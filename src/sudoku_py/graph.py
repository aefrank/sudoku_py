from collections import defaultdict
from collections.abc import Iterable, Iterator, Mapping, MutableMapping, Set
from copy import deepcopy
from functools import lru_cache
from itertools import pairwise
from typing import Any, TypeGuard, overload

from frozendict import deepfreeze, frozendict

from sudoku_py.core import Coords, is_Coords


class CellGraph(MutableMapping[Coords, set[Coords]]):
    """Data structure for representing nonlinear cell connections on Sudoku board. 
    
    Each cell C with coordinates (r,c) is represented as self._graph[(r,c)] = the set of cell coordinates pointed to by edges originating from C.
    """
    _graph:defaultdict[Coords, set[Coords]]
    _directed:bool

    #######################################
    # Object Creation

    @overload
    def __init__(self, arg0:Iterable[tuple[Coords, Coords]]=[], directed=False) -> None: ...
    @overload
    def __init__(self, arg0:Iterable[Coords], directed:bool=False) -> None: ...
    @overload
    def __init__(self, arg0:Iterable[Iterable[Coords]], directed:bool=False) -> None: ...
    def __init__(self
        , arg0:Iterable[tuple[Coords,Coords]] | Iterable[Coords] | Iterable[Iterable[Coords]] = []
        , directed:bool=False
        ) -> None:
        
        self._directed = directed
        self._graph = defaultdict(set)

        arglist:list = list(arg0)
        if self.__is_line(arglist):
            # arg0=line
            self.add_consecutive_edges(arglist)
        elif self.__is_edge_iterable(arglist):
            self.add_edges(arglist)
        elif self.__is_line_iterable(arglist):
            for line in arglist:
                self.add_consecutive_edges(line)
        else:
            raise TypeError(arglist)

    def deepcopy(self) -> CellGraph:
        cg = CellGraph()
        cg._graph = defaultdict(set, {deepcopy(parent): set(deepcopy(children)) for parent, children in self.items()})
        cg._directed = self._directed
        return cg

    @classmethod
    def from_FrozenCellGraph(cls, fcg:FrozenCellGraph) -> CellGraph:
        cg = CellGraph()
        cg._graph = defaultdict(set, {deepcopy(parent): set(deepcopy(children)) for parent, children in fcg.items()})
        cg._directed = fcg._directed
        return cg

    #######################################
    # Properties

    @property
    def cells(self) -> set[Coords]:
        return set(self._graph.keys())
    
    @property
    def edges(self) -> set[tuple[Coords, Coords]]:
        out:set[tuple[Coords, Coords]] = set()
        for cell in self.cells:
            out |= self.get_edges_from(cell)
        return out
    
    #######################################
    # Graph Query Methods
    
    def get_edges_from(self, cell:Coords) -> set[tuple[Coords, Coords]]:
        return set((cell, child) for child in self[cell])

    def get_edges_to(self, cell:Coords) -> set[tuple[Coords, Coords]]:
        return set((cell2, cell) for cell2, children in self.items() if cell in children)

    def get_edges(self, cell:Coords) -> set[tuple[Coords, Coords]]:
            return self.get_edges_from(cell) | self.get_edges_to(cell)

    def get_WCC(self) -> list[frozenset[Coords]]:
        """Return weakly connected components (WCCs) of graph.

        For an undirected graph, returns the connected components. For a directed graph, WCC = connected components of underlying undirected graph.

        Adapted from code from https://www.geeksforgeeks.org/dsa/find-weakly-connected-components-in-a-directed-graph/
        """
        GRAPH:CellGraph = CellGraph(self.edges, directed=False) if self._directed else self

        def extract_component(
                cell:Coords
                , visited:Mapping[Coords, bool]
                , component:Set[Coords]=frozenset()
            ) -> tuple[frozendict[Coords, bool], frozenset[Coords]]:
            """Recursively collects all children of cell until all reachable cells are collected.

            Does not mutate inputs.
            """
            visited_prime:frozendict[Coords, bool] = frozendict((c,True) if c==cell else (c,v) for c,v in visited.items())
            component_prime:frozenset[Coords] = frozenset((*component, cell))
            for child in GRAPH[cell]:
                if not visited_prime[child]:
                    visited_prime, component_prime = extract_component(child, visited_prime, component_prime)
            return visited_prime, component_prime

        connected_components:list[frozenset[Coords]] = []
        is_visited:frozendict[Coords, bool] = frozendict((cell, False) for cell in GRAPH.cells)
        for cell in GRAPH.cells:
            if not is_visited[cell]:
                is_visited, component = extract_component(cell, is_visited)
                connected_components.append(component)
        return connected_components
    
     
    #######################################
    # Mutating Methods

    def add_consecutive_edges(self, cells:Iterable[Coords]) -> None:
        """Add edges between all pairs of consecutive cells on a line.
        """
        for c1, c2 in pairwise(cells):                               
            self.add(c1, c2)

    def add_edges(self, edges:Iterable[tuple[Coords, Coords]]) -> None:
        """Add edges (iterable of tuple Coords pairs) to graph.
        """
        for c1, c2 in edges:
            self.add(c1, c2)

    def add(self, cell1:Coords, cell2:Coords) -> None:
        """Add edge between cell1 and cell2.
        """
        self._graph[cell1].add(cell2)
        if not self._directed:
            self._graph[cell2].add(cell1)

    def remove(self, cell:Coords) -> None: 
        """Remove all references to cell from graph.
        """
        self._graph.__delitem__(cell)
        for _, children in self._graph.items():
            if cell in children:
                children.remove(cell)

    def remove_edge(self, edge:tuple[Coords, Coords]) -> None:
        try:
            self[edge[0]].remove(edge[1])
        except KeyError:
            pass
        if not self._directed:
            try:
                self[edge[1]].remove(edge[0])
            except KeyError:
                pass


    #######################################
    # Private/Dunder methods

    def __repr__(self) -> str: # TODO: consider a more compact __repr__
        return f"{self.__class__.__name__}({dict(self._graph)})"

    def __getitem__(self, key: Coords) -> set[Coords]:
        return self._graph[key]
    
    def __setitem__(self, key: Coords, value: set[Coords]) -> None:
        self._graph[key] = value
    
    def __delitem__(self, key: Coords) -> None:
        self.remove(key)

    def __iter__(self) -> Iterator[Coords]:
        return iter(self._graph)
    
    def __len__(self) -> int:
        return len(self._graph)

    @staticmethod
    def __is_edge_iterable(init_arg:Iterable[Any]) -> TypeGuard[Iterable[tuple[Coords, Coords]]]:
        return all(
                isinstance(elem, tuple) 
            and len(elem)==2 
            and is_Coords(elem[0]) 
            and is_Coords(elem[1])
            for elem in init_arg
        )

    @staticmethod
    def __is_line(init_arg:Iterable[Any]) -> TypeGuard[Iterable[Coords]]:
        return all(is_Coords(elem) for elem in init_arg)

    @classmethod
    def __is_line_iterable(cls, init_arg:Iterable[Any]) -> TypeGuard[Iterable[Iterable[Coords]]]:
        return all(cls.__is_line(elem) for elem in init_arg)

    

class FrozenCellGraph(Mapping[Coords, frozenset[Coords]]):
    """Immutable data structure for representing nonlinear cell connections on Sudoku board. 
        
    Each cell C with coordinates (r,c) is represented as self._graph[(r,c)] = the set of cell coordinates pointed to by edges originating from C.
    """
    _data:frozendict[Coords, frozenset[Coords]]
    _directed:bool
    cells:frozenset[Coords]

    ####### INIT ########

    @overload
    def __init__(self, arg:CellGraph) -> None: ...
    @overload
    def __init__(self, arg:Iterable[tuple[Coords, Coords]], directed:bool=False) -> None: ...
    @overload
    def __init__(self, arg:Iterable[Iterable[Coords]], directed:bool=False) -> None: ...

    def __init__(self
            , arg:CellGraph | Iterable[tuple[Coords, Coords]] | Iterable[Iterable[Coords]]
            , directed:bool=False
            ) -> None:
        cg:CellGraph = arg if isinstance(arg, CellGraph) else CellGraph(arg, directed) 
        self._data = deepfreeze(cg._graph)
        self._directed = cg._directed
        self.cells = frozenset(self._data.keys())

    #####################

    def __getitem__(self, key) -> frozenset[Coords]:
        return self._data[key]

    def __iter__(self) -> Iterator[Coords]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    @property
    @lru_cache
    def edges(self) -> frozenset[tuple[Coords, Coords]]:
        out:frozenset[tuple[Coords, Coords]] = frozenset()
        for cell in self.cells:
            out |= self.get_edges_from(cell)
        return frozenset(out)

    @lru_cache
    def get_edges_from(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return frozenset((cell, child) for child in self[cell])

    @lru_cache
    def get_edges_to(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return frozenset((cell2, cell) for cell2, children in self.items() if cell in children)

    @lru_cache
    def get_edges(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return self.get_edges_from(cell) | self.get_edges_to(cell)
        
    def mutable_copy(self) -> CellGraph:
        return CellGraph.from_FrozenCellGraph(self)