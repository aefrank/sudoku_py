"""Shared Spaces (Blue and Pink) by Fenners
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000MOD
"""

from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from dataclasses import dataclass
import itertools as it
import functools as ft
from typing import Any, Iterable, Optional, Self, TypeGuard, overload
from frozendict import frozendict, deepfreeze
from more_itertools import peekable


from ortools.sat.python.cp_model import CpModel

from my_utils import MyProblemSetup, remove_offset
from sudoku_py.constraint import MultiCellConstraint
from sudoku_py.core import Coords, is_Coords, partition
from sudoku_py.grid import SudokuGrid


class CellGraph(MutableMapping[Coords, set[Coords]]):
    """Data structure for representing nonlinear cell connections on Sudoku board. 
    
    Each cell C with coordinates (r,c) is represented as self._graph[(r,c)] = the set of cell coordinates pointed to by edges originating from C.
    """
    _graph:defaultdict[Coords, set[Coords]]
    _directed:bool

    
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


    def add_consecutive_edges(self, cells:Iterable[Coords]) -> None:
        """Add edges between all pairs of consecutive cells on a line.
        """
        for c1, c2 in it.pairwise(cells):
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

    @property
    def cells(self) -> set[Coords]:
        return set(self._graph.keys())

    @property
    def edges(self) -> set[tuple[Coords, Coords]]:
        out:set[tuple[Coords, Coords]] = set()
        for cell in self.cells:
            out |= self.get_edges_from(cell)
        return out

    def get_edges_from(self, cell:Coords) -> set[tuple[Coords, Coords]]:
        return set((cell, child) for child in self[cell])

    def get_edges_to(self, cell:Coords) -> set[tuple[Coords, Coords]]:
        return set((cell2, cell) for cell2, children in self.items() if cell in children)

    def get_edges(self, cell:Coords) -> set[tuple[Coords, Coords]]:
        return self.get_edges_from(cell) | self.get_edges_to(cell)

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

    @classmethod
    def from_FrozenCellGraph(cls, fcg:FrozenCellGraph) -> CellGraph:
        cg = CellGraph()
        cg._graph = defaultdict(set, {parent: set(children) for parent, children in fcg.items()})
        cg._directed = fcg._directed
        return cg


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
    @ft.lru_cache
    def edges(self) -> frozenset[tuple[Coords, Coords]]:
        out:frozenset[tuple[Coords, Coords]] = frozenset()
        for cell in self.cells:
            out |= self.get_edges_from(cell)
        return frozenset(out)

    @ft.lru_cache
    def get_edges_from(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return frozenset((cell, child) for child in self[cell])

    @ft.lru_cache
    def get_edges_to(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return frozenset((cell2, cell) for cell2, children in self.items() if cell in children)

    @ft.lru_cache
    def get_edges(self, cell:Coords) -> frozenset[tuple[Coords, Coords]]:
        return self.get_edges_from(cell) | self.get_edges_to(cell)
        
    def mutable_copy(self) -> CellGraph:
        return CellGraph.from_FrozenCellGraph(self)
            



# based on code from https://www.geeksforgeeks.org/dsa/find-weakly-connected-components-in-a-directed-graph/
class WeaklyConnectedComponents:
    def __init__(self, graph: CellGraph):
        self.graph = graph
    
    
    #  Finds all the connected components
   # of the given undirected graph
    def connected_components(self, undirected_graph:CellGraph) -> list[set[Coords]]:
        assert not undirected_graph._directed
        N:int = len(undirected_graph)

        connected_components:list[set[Coords]] = []
        is_visited:dict[Coords, bool] = {cell:False for cell in undirected_graph.cells}

        for cell in undirected_graph.cells:
            if not is_visited[cell]:
                component:set[Coords] = set()
                self.find_connected_component(cell, is_visited, component, undirected_graph)
                connected_components.append(component)

        return connected_components
 
    # Finds a connected component
    # starting from source using DFS
    def find_connected_component(self, src:Coords, is_visited:dict[Coords, bool], component:set[Coords], undirected_graph:CellGraph):
        assert not undirected_graph._directed

        is_visited[src] = True
        component.add(src)

        for child in undirected_graph[src]:
            if not is_visited[child]:
                self.find_connected_component(child, is_visited, component, undirected_graph)
  
    def weakly_connected_components(self):
       #Step 1: Construct the
        # underlying undirected graph
        undirected_graph = CellGraph(self.graph.edges, directed=False) if self.graph._directed else self.graph
        return self.connected_components(undirected_graph)



        

class GraphConstraint(MultiCellConstraint):
    _graph:FrozenCellGraph

    # @classmethod
    # def from_edges(cls, edges:Iterable[tuple[Coords, Coords]], directed:bool=False) -> Self:
    #     return cls(CellGraph(edges, directed))

    # @classmethod
    # def from_lines(cls, lines:Iterable[Iterable[Coords]], directed:bool=False) -> Self:
    #     return cls(CellGraph(lines, directed))

    # @classmethod
    # def from_line(cls, line:Iterable[Coords], directed:bool=False) -> Self:
    #     return cls(CellGraph([line], directed))

    def __init__(self, graph: CellGraph | FrozenCellGraph) -> None:
        if not isinstance(graph, FrozenCellGraph):
            self._graph = FrozenCellGraph(graph)
        else:
            self._graph = graph
        self.cells = self._graph.cells

    @property
    def _identifying_attributes(self) -> tuple[frozendict[Coords, frozenset[Coords]]]:
        return (self._graph._data,)



def disjoint_partition[T](values:Iterable[T], predicate:Callable[[T], bool], *more_predicates:Callable[[T], bool]) -> list[filter[T] | it.filterfalse[T]]:
    # Declare some types for type checking
    yes:filter[T]
    no:it.filterfalse[T]
    peekable_no:peekable[T]
    peekable_tail:peekable[Callable[[T], bool]]
    # main:
    yes, no = partition(values, predicate)
    peekable_no, peekable_tail = peekable(no), peekable(more_predicates)
    if not peekable_no or not peekable_tail:
        return [yes]
    else:
         return [yes] + disjoint_partition(no, *more_predicates)


class RegionSum(GraphConstraint):
    def __init__(self, graph: CellGraph | FrozenCellGraph) -> None:
        super().__init__(graph)

    @staticmethod
    def segment_graph_by_regions(fcg:FrozenCellGraph, regions:list[Iterable[Coords]]):
        def region_idx(cell:Coords):
            for i, region in enumerate(regions):
                if cell in region:
                    return i
            # cell not found
            raise ValueError(cell) 

        cg:CellGraph = CellGraph.from_FrozenCellGraph(fcg)

        # # region_predicates:list[Callable[[Coords], bool]] = [lambda cell: (cell in region) for region in regions]
        # # cells_per_region:list[filter[Coords]|it.filterfalse[Coords]] = disjoint_partition(cg.cells, *region_predicates)
        
        # region_edges_predicates:list[Callable[[tuple[Coords,Coords]], bool]] = [
        #     lambda edge: ((edge[0] in region) and (edge[1] in region)) 
        #     for region in regions
        # ]
        # edges_in_region: list[filter[tuple[Coords, Coords]] | it.filterfalse[tuple[Coords,Coords]]] = disjoint_partition(cg.edges, *region_edges_predicates)
        # N = len(regions)
        # assert len(edges_in_region) == N+1
        # # edges_in_region[N] should hold all cross-region edges
        # for edge in edges_in_region[N]:

        cross_region_edges = filter(
            lambda edge: region_idx(edge[0]) != region_idx(edge[1])
            , cg.edges
        )
        for edge in cross_region_edges:
            cg.remove_edge(edge)

        segments:list[set[Coords]] = WeaklyConnectedComponents(cg).weakly_connected_components()

        for i, segment in enumerate(segments):
            # Check that segments are disjoint
            for s in segments[i+1:]:
                assert segment.isdisjoint(s)

            # check that all cells in segment are in same region
            assert len(set(region_idx(cell) for cell in segment)) == 1

        return segments


    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        raise NotImplementedError





        
        
        


    

    


def main():
    SOLUTION:list[list[int]] = [
        [2,3,1,9,6,4,5,8,7]
        , [8,6,7,1,5,3,4,9,2]
        , [4,5,9,2,8,7,1,6,3]
        , [9,4,3,8,2,1,6,7,5]
        , [1,2,5,7,9,6,8,3,4]
        , [7,8,6,3,4,5,9,2,1]
        , [6,7,8,5,1,2,3,4,9]
        , [3,1,4,6,7,9,2,5,8]
        , [5,9,2,4,3,8,7,1,6]
    ]

    region_sum_lines = [
        [ 
            (6,2), (7,2), (8,2) 
        ]
        , [ 
            (6,7), (6,8), (7,8), (8,8), (8,7), (8,6), (7,6) 
        ]
        , [
            [ 
                (5,4), (4,4), (4,5), (4,6), (4,7), (4,8), (4,9) 
            ]
            , [ 
                (4,6), (3,6), (3,5), (3,4), (2,4), (2,3), (2,2), (3,2), (4,2), (4,3), (5,3), (6,3), (6,4), (6,5), (6,6), (5,6) 
            ]
            , [ 
                (6,4), (7,4), (8,4), (9,4), (9,5) 
            ]
        ]
    ]
    region_sum_lines[0] = [(r-1, c-1) for (r,c) in region_sum_lines[0]]
    region_sum_lines[1] = [(r-1, c-1) for (r,c) in region_sum_lines[1]]

    region_sum_lines[2] = [[(r-1, c-1) for (r,c) in line] for line in region_sum_lines[2]]



    region_sum_constraints = [RegionSum(arg) for arg in region_sum_lines]
    problem = MyProblemSetup(
                      one_indexed=True
                    , constraints=[c for c in region_sum_constraints]
                    , correct_solution=SOLUTION
                )
    
    
    boxes_of_vars = [list(it.chain(*box)) for box in problem.grid.boxes()]
    regions:list[list[Coords]] = [[problem.grid.index(cell) for cell in box] for box in boxes_of_vars]
    RS = region_sum_constraints[2]
    RegionSum.segment_graph_by_regions(RS._graph, [region for region in regions])
    print()

if __name__=="__main__":
    main()