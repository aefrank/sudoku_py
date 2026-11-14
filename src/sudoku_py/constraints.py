from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from itertools import combinations, filterfalse, tee
from time import time
from typing import Any, Iterable, NewType, Optional, TypeIs, TypeVar, overload

from multipledispatch import dispatch
import functools as ft
from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback

from sudoku_py.sudoku import SudokuGrid, SudokuModel

""" 
HOUSEKEEPING
"""

############        CELL COORDINATES   ########################

type Coords = tuple[int,int]
def is_Coords(x:Any) -> TypeIs[Coords]:
    if isinstance(x, tuple):
        if len(x)==2 and isinstance(x[0],int) and isinstance(x[1],int):
            return True
    return False



############        ADJACENCY   ########################

AdjacentCellPair = NewType("AdjacentCellPair", tuple[Coords, Coords])
@overload
def is_adjacent(cell1:Coords, cell2:Coords, /) -> bool: ...
@overload 
def is_adjacent(cell_pair:tuple[Coords,Coords], /) -> TypeIs[AdjacentCellPair]: ...
def is_adjacent(arg0:Coords|tuple[Coords,Coords], arg1:Optional[Coords]=None) -> bool:
    if is_Coords(arg0):
        if not is_Coords(arg1):
            raise ValueError(arg1)
        dr, dc = abs(arg0[0]-arg1[0]), abs(arg0[1]-arg1[1])
        return dr+dc==1 
    else:
        if is_Coords(arg0[0]) and is_Coords(arg0[1]):
            return is_adjacent(arg0[0], arg0[1])
        else:
            raise ValueError(arg0, arg1)

def verify_adjacency(pair:tuple[Coords,Coords]) -> AdjacentCellPair:
    if is_adjacent(pair):
        return pair
    else:
        raise ValueError(pair)




############        MANIPULATING CELL ITERABLES   ########################

@overload
def sort_cells(cell1:Coords, cell2:Coords, /) -> tuple[Coords, Coords]: ...
@overload
def sort_cells(*cells:Coords) -> tuple[Coords, ...]: ...
def sort_cells(*cells:Coords) -> tuple[Coords, ...]:
    ordered = sorted(cells)
    if isinstance(cells,tuple):
        return (ordered[0], ordered[1])
    else:
        return tuple(ordered)

T = TypeVar('T')
def partition(iterable:Iterable[T], pred:Callable[[T],bool]) -> tuple[filter[T], filterfalse[T]]:
    """Splits an iterable into two: one matching pred, one not matching pred."""
    t1, t2 = tee(iterable)
    return filter(pred, t1), filterfalse(pred, t2)






############################################################
############ ABSTRACT CONSTRAINT CLASSES ###################
############################################################

class Constraint(ABC):
    @abstractmethod
    def apply(self, model:SudokuModel, grid:SudokuGrid) -> None: ...

    @staticmethod
    def apply_constraints(model:SudokuModel, grid:SudokuGrid, *constraints:Constraint) -> None:
        for constraint in constraints:
            constraint.apply(model, grid)

@ft.total_ordering
class MultiCellConstraint(Constraint):
    _cells:tuple[Coords, ...]

    def __init__(self, *cells:Coords):
        self.cells = cells

    @property
    def cells(self) -> tuple[Coords, ...]:
        return sort_cells(*self._cells)

    @cells.setter
    def cells(self, cells:Iterable[Coords]):
        self._cells = sort_cells(*cells)

    def __lt__(self, other:object) -> bool: 
        if type(other) is not type(self):
            raise NotImplemented
        return self.cells < other.cells

    def __eq__(self, other:object) -> bool:
        if type(other) is not type(self):
            raise NotImplemented
        return self.cells == other.cells

    def __repr__(self) -> str:
        kws = [f"{key}={value!r}" if key != "_cells" else f"cells={self.cells!r}" for key, value in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(kws))

@dataclass
@ft.total_ordering
class SingleCellConstraint(Constraint):
    cell:Coords

    def __lt__(self, other:object) -> bool: 
        if type(other) is not type(self):
            raise NotImplemented
        return self.cell < other.cell

    def __eq__(self, other:object) -> bool:
        if type(other) is not type(self):
            raise NotImplemented
        return self.cell == other.cell


class TwoCellConstraint(MultiCellConstraint):
    _cells:tuple[Coords, Coords] = field(init=False, repr=False)

    @abstractmethod
    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = sort_cells(cell1, cell2)

    @property
    def cells(self) -> tuple[Coords,Coords]:
        return sort_cells(*self._cells)

    @cells.setter
    def cells(self, pair:tuple[Coords,Coords]):
        self._cells = sort_cells(*pair)


class BorderConstraint(TwoCellConstraint):
    _cells:AdjacentCellPair
    def __init__(self, cell1:Coords, cell2:Coords):
        assert is_adjacent(cell1, cell2)
        cells = sort_cells(cell1, cell2)
        if is_adjacent(cells):
            self.cells = cells

    @property
    def cells(self) -> AdjacentCellPair:
        return verify_adjacency(sort_cells(*self._cells))

    @cells.setter
    def cells(self, adjacent_cell_pair:AdjacentCellPair):
        self._cells = verify_adjacency(sort_cells(*adjacent_cell_pair))

    @property
    def is_horizontal(self) -> bool:
        cell1, cell2 = self.cells
        dr, dc = cell2[0]-cell1[0], cell2[1]-cell1[1]
        return dr==0 and abs(dc)==1





############################################################
############ CONCRETE CONSTRAINT CLASSES ###################
############################################################

class SudokuConstraintType(Constraint):
    @staticmethod
    def apply(model: SudokuModel, grid: SudokuGrid) -> None:
        for row in grid.rows():
            model.add_all_different(row)
        for col in grid.cols():
            model.add_all_different(col)
        for box in grid.boxes():
            box_cells = ft.reduce(lambda x,y: x+y, box)
            model.add_all_different(box_cells)

    instance = None
    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

SudokuConstraint = SudokuConstraintType()

@dataclass
class Given(SingleCellConstraint):
    value: int

    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        model.add(grid.cell(*self.cell)==self.value)

class Nonconsecutive(TwoCellConstraint):
    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = sort_cells(cell1, cell2)

    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 - cell2 != 1)
        model.add(cell2 - cell1 != 1)

class XBorder(BorderConstraint):
    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 10)

class VBorder(BorderConstraint):
    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 5)

class NegativeXBorder(BorderConstraint):
    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 10)

class NegativeVBorder(BorderConstraint):
    def apply(self, model: SudokuModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 5)



############################################################
################### EXAMPLE PROBLEM ########################
############################################################

class XVSolutionPrinter(CpSolverSolutionCallback):

    def __init__(self
                 , model:SudokuModel
                 , v_constraints:list[VBorder]=[]
                 , x_constraints:list[XBorder]=[]
                 , correct_solution:list[list[int]]|None=None
                ):
        CpSolverSolutionCallback.__init__(self)
        self.model = model
        self._solution_count = 0
        self._start_time = time()
        self.__correct_solution = correct_solution
        is_horizontal = lambda border_constraint: border_constraint.is_horizontal
        v_horiz, v_vert = partition(v_constraints, is_horizontal)
        self.v_borders = ([constraint.cells[0] for constraint in v_horiz], [constraint.cells[0] for constraint in v_vert])
        x_horiz, x_vert = partition(x_constraints, is_horizontal)
        self.x_borders = ([constraint.cells[0] for constraint in x_horiz], [constraint.cells[0] for constraint in x_vert])
        
    @property
    def solution_count(self) -> int:
        return self._solution_count

    def check_cell(self, i, j, val):
        assert self.__correct_solution is not None
        return self.__correct_solution[i][j] == val
    
    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )
        self._solution_count += 1

        # solution is correct until a mismatch found
        if self.__correct_solution:
            correct = True
        
        for i, row in enumerate(self.model.grid):
            # Add 'v' or 'x' between applicable horizontal pairs
            for j, cell in enumerate(row):
                # HORIZONTAL ANNOTATIONS
                if (i,j) in self.v_borders[0]:
                    end = " v "
                elif (i,j) in self.x_borders[0]:
                    end = " x "
                else:
                    end = "   "
                # VERTICAL ANNOTATIONS:
                # Add single underline (v) or double underline (x) between applicable vertical pairs
                if (i,j) in self.v_borders[1]:
                    u1,u2 = "\033[4m", "\033[0m"
                elif (i,j) in self.x_borders[1]:
                    u1,u2 = "\033[21m", "\033[24m"
                else:
                    u1,u2 = "",""
                # print cell with highlights
                val = self.value(cell)
                print(f"{u1}{val}{u2}", end=end)
                if self.__correct_solution:
                    correct = correct and self.check_cell(i,j,val)

            print()
        if self.__correct_solution and correct:
            print("SOLUTION CORRECT!")
        print()



def SecretWindmill(v_pairs:list[tuple[Coords, Coords]]
                   , x_pairs:list[tuple[Coords, Coords]]
                   , nonconsecutive_pairs:list[tuple[Coords, Coords]]
                   , *
                   , one_indexed:bool):

    def sort_and_offset(*pairs:tuple[Coords,Coords]):
        offset:int = 1 if one_indexed else 0
        return [sort_cells( (r1-offset, c1-offset)
                          , (r2-offset, c2-offset)  ) 
                for (r1,c1), (r2,c2) in pairs]

    SOLUTION = [
              [1, 5, 4, 2, 6, 7, 9, 8, 3]
            , [6, 2, 3, 4, 8, 9, 7, 1, 5]
            , [8, 9, 7, 3, 1, 5, 6, 4, 2]
            , [9, 8, 5, 7, 3, 6, 4, 2, 1]
            , [7, 6, 2, 1, 5, 4, 3, 9, 8]
            , [4, 3, 1, 9, 2, 8, 5, 7, 6]
            , [3, 1, 9, 5, 4, 2, 8, 6, 7]
            , [5, 4, 8, 6, 7, 1, 2, 3, 9]
            , [2, 7, 6, 8, 9, 3, 1, 5, 4]
        ]
    
    v_pairs = sort_and_offset(*v_pairs)
    x_pairs = sort_and_offset(*x_pairs)
    nonconsecutive_pairs = sort_and_offset(*nonconsecutive_pairs)
    
    model = SudokuModel()

    sudoku_constraint = SudokuConstraint

    v_constraints:list[VBorder] = [VBorder(*pair) for pair in v_pairs]
    x_constraints:list[XBorder] = [XBorder(*pair) for pair in x_pairs]
    
    xv_pairs:list[tuple[Coords,Coords]] = v_pairs + x_pairs
    negative_v_constraints:list[NegativeVBorder] = []
    negative_x_constraints:list[NegativeXBorder] = []
    for (cell1, cell2) in model.grid.get_all_adjacent_pairs():
        pair:tuple[Coords,Coords] = (model.grid.index(cell1), model.grid.index(cell2))
        if pair not in xv_pairs:
            negative_v_constraints.append(NegativeVBorder(*pair))
            negative_x_constraints.append(NegativeXBorder(*pair))

    nonconsecutive_constraints:list[Nonconsecutive] = [Nonconsecutive(*pair) for pair in nonconsecutive_pairs]

    constraints_list:Sequence[Constraint] = [sudoku_constraint] + v_constraints + x_constraints + negative_v_constraints + negative_x_constraints + nonconsecutive_constraints
    Constraint.apply_constraints(model, model.grid, *constraints_list)

    solver = CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.solve(model
                 , solution_callback=XVSolutionPrinter( model
                                                      , v_constraints=v_constraints
                                                      , x_constraints=x_constraints
                                                      , correct_solution=SOLUTION
                                                      )
    )



def main():
    nonconsecutive_pairs = list(combinations( [ (1,8)
                                              , (1,9)
                                              , (2,8)
                                              , (2,9)
                                            ]
                                            , 2)
    )
    v_pairs = [
              ((2,2),(2,3))
            , ((2,8),(3,8))
            , ((7,2),(8,2))
            , ((8,7),(8,8))
        ]
    x_pairs = [ 
              ((2,3), (3,3)) # vertical
            , ((3,3), (3,4)) # horizontal
            , ((3,4), (4,4)) # vertical
            , ((4,4), (4,5)) # horizontal
    
            , ((3,8), (3,7)) # horizontal
            , ((3,7), (4,7)) # vertical
            , ((4,7), (4,6)) # horizontal
            , ((4,6), (5,6)) # vertical
    
            , ((5,4), (6,4)) # vertical
            , ((6,4), (6,3)) # horizontal
            , ((6,3), (7,3)) # vertical
            , ((7,3), (7,2)) # horizontal
    
            , ((6,5), (6,6)) # horizontal
            , ((6,6), (7,6)) # vertical
            , ((7,6), (7,7)) # horizontal
            , ((7,7), (8,7)) # vertical
        ]
    SecretWindmill(v_pairs=v_pairs, x_pairs=x_pairs, nonconsecutive_pairs=nonconsecutive_pairs, one_indexed=True)
    
if __name__=="__main__":
    main()