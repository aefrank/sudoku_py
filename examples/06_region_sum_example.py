"""Shared Spaces (Blue and Pink) by Fenners
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000MOD
"""

from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, MutableMapping, Sequence, Set
from copy import deepcopy
from dataclasses import dataclass
import itertools as it
import functools as ft
from typing import Any, Iterable, Optional, Self, TypeGuard, cast, overload
from frozendict import frozendict, deepfreeze
from more_itertools import peekable


from ortools.sat.python.cp_model import CpModel, IntVar

from my_utils import MyProblemSetup, MySolutionPrinter, remove_offset
from sudoku_py.constraint import Given, MultiCellConstraint, Renban, WhiteKropki
from sudoku_py.core import Coords, is_Coords, partition, partition_out_types
from sudoku_py.grid import SudokuGrid


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
        # component:Set[Coords]
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
            

def get_wcc(graph:CellGraph) -> list[frozenset[Coords]]:
    """Return weakly connected components (WCCs) of graph.

    For an undirected graph, returns the connected components. For a directed graph, WCC = connected components of underlying undirected graph.

    Adapted from code from https://www.geeksforgeeks.org/dsa/find-weakly-connected-components-in-a-directed-graph/
    """
    GRAPH:CellGraph = CellGraph(graph.edges, directed=False) if graph._directed else graph

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
    component:Set[Coords]
    is_visited:frozendict[Coords, bool] = frozendict((cell, False) for cell in GRAPH.cells)
    for cell in GRAPH.cells:
        if not is_visited[cell]:
            is_visited, component = extract_component(cell, is_visited)
            connected_components.append(component)
    return connected_components



class GraphConstraint(MultiCellConstraint):
    _graph:FrozenCellGraph
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
    name:str
    __INSTANCE_COUNT:int=0
            
    def __init__(self, graph: CellGraph | FrozenCellGraph) -> None:
        super().__init__(graph)
        __class__.__INSTANCE_COUNT += 1 # increment program-wide instance count
        self.name = f"{__class__.__name__}{self.__INSTANCE_COUNT}"

    @staticmethod
    def segment_graph_by_regions(graph: CellGraph | FrozenCellGraph, regions: Sequence[Sequence[Coords]]) -> list[frozenset[Coords]]:
        """Return graph segments divided by region borders.
        """
        def rid(cell:Coords):
            """Get region id of cell"""
            for i, region in enumerate(regions):
                if cell in region:
                    return i
            # cell not found
            raise ValueError(cell) 

        def __graph_segments_sanity_check(segments:list[frozenset[Coords]]) -> None:
                """Prototyping test: Check some properties that should hold"""
                for i, segment in enumerate(segments):
                    # Check that segments are disjoint
                    for s in segments[i+1:]:
                        assert segment.isdisjoint(s)
        
                    # check that all cells in segment are in same region
                    assert len(set(rid(cell) for cell in segment)) == 1

        # Create copy of graph that is safe to mutate
        cg:CellGraph = CellGraph.from_FrozenCellGraph(graph) if isinstance(graph, FrozenCellGraph) else graph.deepcopy()

        # Remove all cross-region edges
        for edge in filter(lambda edge: rid(edge[0])!=rid(edge[1]), cg.edges):
            cg.remove_edge(edge)

        # Find weakly-connected components of graph
        segments:list[frozenset[Coords]] = cg.get_WCC()

        # Check some invariants that should hold
        __graph_segments_sanity_check(segments)

        return segments


    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        segments:list[frozenset[Coords]] = self.segment_graph_by_regions(
              self._graph
            , [[grid.index(cell) for cell in box] for box in grid.boxes()]
            )
        """Region sum lines are segmented by region borders. Digits along each segment must sum to the same value. 
        
        Note that if a region sum line enters the same region twice, each of the two segments counts as separate sums. 
        """
        segment_vars:list[list[IntVar]] = [[grid.cell(*cell) for cell in segment] for segment in segments]
        for vars1, vars2 in it.pairwise(segment_vars):
            model.add(sum(vars1) == sum(vars2))

        





        
type NestedSequence[T] = T | Sequence[NestedSequence[T]]        


def undo_offset[C:NestedSequence[Coords]](data:C, offset:int=1) -> C:
    if not is_Coords(data):
        processed = (undo_offset(item) for item in data)
        try:
            return cast(C, type(data)(processed)) # pyright: ignore[reportCallIssue]
        except TypeError:
            # if type(data) constructor fails, cast from list
            return cast(C, list(processed))
    else:
        r:int
        c:int
        r,c = data
        return cast(C, (r-offset, c-offset))
    

class _Printer(MySolutionPrinter):
    _regionsum_cells:set[Coords]
    _renban_cells:set[Coords]

    def __init__(self, problem: MyProblemSetup):
        super().__init__(problem, problem.correct_solution)
        region_sum, renban = (set(out) for out in partition_out_types(problem.constraints, *[RegionSum, Renban]))
        self._renban_cells = set()
        for r in renban:
            self._renban_cells.update(r.cells)
        self._regionsum_cells = set()
        for rs in region_sum:
            self._regionsum_cells.update(rs.cells)


    def print_target(self, var: IntVar, coords: Coords):
        # prefix:str = "\033["
        format:list[str] = []
        if coords in self._regionsum_cells:
            format += ["1"]
        if coords in self._renban_cells:
            format += ["35"]
        prefix:str = "\033[" + ";".join(format) + "m"
        suffix:str = "\033[0m"
        print(f"{prefix}{self.value(var)}{suffix}", end="  ")


    
def shared_spaced_renban_constraints() -> list[Renban]:
    renban_lines:list[list[Coords]] = [
              [ (1,9), (1,8), (2,8), (3,8) ]
            , [ (2,3), (2,2), (3,2) ]
            , [ (2,4), (3,4), (3,5), (3,6), (4,2), (4,3), (5,3), (6,3) ]
            , [ (4,4), (5,4), (5,5), (5,6) ]
            , [ (4,7), (4,8), (4,9) ]
            , [ (5,8), (6,8), (6,9) ]
            , [ (6,4), (6,5), (6,6) ]
            , [ (7,4), (8,4), (9,4) ]
            , [ (8,5), (8,6), (9,6) ]
            , [ (7,8), (8,8) ]
        ]
    renban_constraints:list[Renban] = [Renban(coords) for coords in undo_offset(renban_lines)]
    return renban_constraints

def shared_spaced_regionsum_constraints() -> list[RegionSum]:
    RS1:list[Coords] = [(6,2), (7,2), (8,2)]
    RS2:list[Coords] = [(6,7), (6,8), (7,8), (8,8), (8,7), (8,6), (7,6)]
    RS3:list[list[Coords]] = [
                [(5,4), (4,4), (4,5), (4,6), (4,7), (4,8), (4,9)]
            , [(4,6), (3,6), (3,5), (3,4), (2,4), (2,3), (2,2), (3,2), (4,2), (4,3), (5,3), (6,3), (6,4), (6,5), (6,6), (5,6)]
            , [(6,4), (7,4), (8,4), (9,4), (9,5)]
        ]
    region_sum_constraints:list[RegionSum] = [RegionSum(CellGraph(arg)) for arg in undo_offset((
                    # [],  # for debugging
                      RS1
                    , RS2
                    , RS3
                    ))]
    return region_sum_constraints

def shared_space_whitekropki_constraints() -> list[WhiteKropki]:
    white_kropki_locations:list[tuple[Coords, Coords]] = [
          ((1,5), (2,5))
        , ((1,6), (2,6))
        , ((1,7), (2,7))
        , ((5,1), (5,2))
        , ((6,1), (6,2))
    ]
    white_kropki_constraints:list[WhiteKropki] = [WhiteKropki(*coords) for coords in undo_offset(white_kropki_locations)]
    return white_kropki_constraints






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

    

    



    problem = MyProblemSetup(
                      one_indexed=True
                    , constraints=shared_space_whitekropki_constraints() + shared_spaced_regionsum_constraints() + shared_spaced_renban_constraints()
                    , correct_solution=SOLUTION
                )
    
    
    problem.apply_constraints()
    problem.solve(solution_printer=_Printer(problem))

if __name__=="__main__":
    main()