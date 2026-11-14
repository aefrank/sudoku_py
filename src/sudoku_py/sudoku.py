########################### IMPORTS #############################

from abc import ABC, abstractmethod
from collections.abc import Generator
from copy import deepcopy
from dataclasses import dataclass, field
import functools as ft
from itertools import product
from time import time
from typing import Any, Generic, TypeVar

from ortools.sat.python.cp_model import CpModel, IntVar

from sudoku_py.common import AdjacentCellPair, Coords, is_adjacent, sort_cells, verify_adjacency


####################################################################
########################## VARIABLE GRID ###########################
####################################################################

T = TypeVar("T")

class BaseSudokuGrid(Generic[T]):
    """Base data structure for CP Model variable storage and handling.

    Stores data in a NxN grid represented by N nested N-length lists.
    
    Contains data querying methods and some basic predicates such as
    whether two cells are in the same 'sudoku box'.
    """
    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3)):
        self.size = size
        self.box_dims = box_dims
        rows_of_boxes, cols_of_boxes = [self.size/dim for dim in self.box_dims]
        assert all(n.is_integer() for n in (rows_of_boxes, cols_of_boxes))
        self.rows_of_boxes, self.cols_of_boxes = int(rows_of_boxes), int(cols_of_boxes)
        self.items:list[list[T]] = []

    def populate_grid(self, L:list[list[T]]):
        assert (len(L) == self.size)
        for sublist in L:
            assert len(sublist) == self.size
        self.items = L

    @classmethod
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> BaseSudokuGrid[T]:
        sudoku_grid = cls(len(L), box_dims)
        sudoku_grid.populate_grid(L)
        return sudoku_grid

    def row(self, r:int) -> list[T]:
        return self.items[r]

    def col(self, c:int) -> list[T]:
        return [self.items[r][c] for r in range(self.size)]

    def box(self, b:int) -> list[list[T]]:
        row = (b // self.cols_of_boxes) * self.box_dims[0]
        col = (b % self.cols_of_boxes) * self.box_dims[1]
        return [[self.items[row+i][col+j] for j in range(self.box_dims[1])] for i in range(self.box_dims[0])]

    def cell(self, row:int, col:int) -> T:
        return self.items[row][col]

    def index(self, val:T) -> tuple[int,int]:
        for r, row in enumerate(self.items):
            try:
                return r, row.index(val)
            except ValueError:
                continue
        # if you get to the end, cell wasn't anywhere in grid
        raise ValueError(val)

    def rows(self) -> list[list[T]]:
        return self.items

    def cols(self) -> list[list[T]]:
        return [self.col(i) for i in range(self.size)]

    def boxes(self) -> list[list[list[T]]]:
        return [self.box(i) for i in range(self.rows_of_boxes*self.cols_of_boxes)]

    def cells(self) -> list[T]:
        return ft.reduce(lambda x,y: x+y, self.rows())

    def get_row(self, item:T) -> int:
        return self.index(item)[0]

    def get_col(self, item:T) -> int:
        return self.index(item)[1]

    def get_box(self, item:T) -> int:
        for i,box in enumerate(self.boxes()):
            if item in ft.reduce(lambda x,y: x+y, box):
                return i
        # if we get to here, item does not exist in grid
        raise ValueError(item)

    def same_row(self, cell1:T, cell2:T) -> bool:
            return self.get_row(cell1) == self.get_row(cell2)
    
    def same_col(self, cell1:T, cell2:T) -> bool:
        return self.get_col(cell1) == self.get_col(cell2)

    def same_box(self, cell1:T, cell2:T) -> bool:
        return self.get_box(cell1) == self.get_box(cell2)

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> Generator[list[T], Any, Any]:
        for item in self.items:
            yield item



class SudokuGrid(BaseSudokuGrid[T]):
    """Extended data structure for CP Model variable storage and handling.
    
        Stores data in a NxN grid represented by N nested N-length lists.
        
        Contains basic data querying methods and predicates, and adds
        methods to generate derived queries such as getting all pairs
        of adjacent cells.
    """

    @classmethod
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> SudokuGrid[T]: 
        sudoku_grid = cls(len(L), box_dims)
        sudoku_grid.populate_grid(L)
        return sudoku_grid

    def get_all_horizontal_pairs(self) -> list[tuple[T,T]]:
        return [(self.cell(r,c), self.cell(r,c+1)) for r,c in product(range(self.size), range(self.size-1))]
    
    def get_all_vertical_pairs(self) -> list[tuple[T,T]]:
        return [(self.cell(r,c), self.cell(r+1,c)) for r,c in product(range(self.size-1), range(self.size))]
    
    def get_all_adjacent_pairs(self) -> list[tuple[T,T]]:
        return self.get_all_horizontal_pairs() + self.get_all_vertical_pairs()

    def is_horizontal_neighbor(self, cell1:T, cell2:T) -> bool:
        return self.same_row(cell1,cell2) and (abs(self.get_col(cell1)-self.get_col(cell2))==1)

    def is_vertical_neighbor(self, cell1:T, cell2:T) -> bool:
        return self.same_col(cell1,cell2) and (abs(self.get_row(cell1)-self.get_row(cell2))==1)


####################################################################
########################### CONSTRAINTS ############################
####################################################################

################   ABSTRACT CONSTRAINT CLASSES   ###################

class Constraint(ABC):
    """Defines abstract skeleton for Sudoku constraints.

    In particular defines the ```apply``` method signature,
    which should be implemented by all concrete subclasses.

    Also supplies static method to apply multiple constraints
    to the same model and variables.
    """
    @abstractmethod
    def apply(self, model:CpModel, grid:SudokuGrid) -> None: ...

    @staticmethod
    def apply_constraints(model:CpModel, grid:SudokuGrid, *constraints:Constraint) -> None:
        for constraint in constraints:
            constraint.apply(model, grid)

@ft.total_ordering
class MultiCellConstraint(Constraint):
    """Defines abstract interface for Sudoku constraints that relate
    multiple cells.

    Enforces a canonical (sorted) order for storing collections of cells
    so they can be easily checked without worrying about permutations.
    """
    _cells:tuple[Coords, ...]

    def __init__(self, *cells:Coords):
        self._cells = sort_cells(*cells)

    @property
    def cells(self) -> tuple[Coords, ...]:
        return self._cells

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
    """Defines abstract interface for Sudoku constraints that act 
    on a single cell.
    """
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
    """Defines abstract interface for Sudoku constraints that relate
    exactly two cells.

    Enables the assumption that len(TwoCellConstraint.cells)==2,
    which is useful for type checking and adjacency requirements.
    """
    _cells:tuple[Coords, Coords] = field(init=False, repr=False)

    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = sort_cells(cell1, cell2)

    @property
    def cells(self) -> tuple[Coords,Coords]:
        return sort_cells(*self._cells)

    @cells.setter
    def cells(self, pair:tuple[Coords,Coords]):
        self._cells = sort_cells(*pair)


class BorderConstraint(TwoCellConstraint):
    """Defines abstract interface for Sudoku constraints located
    on the border between two adjacent cells.

    Enforces that the two cells in self._cells are adjacent, and
    allows querying of whether the border separates the cells
    horizontally or vertically.
    """
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
    """Implements the standard 'Sudoku' non-repeating constraints.

    Enforces AllDifferent CpModel constraint on grid rows, columns, and boxes.

    Singleton class with no internal data.
    """
    @staticmethod
    def apply(model: CpModel, grid: SudokuGrid) -> None:
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
    """Represents a given cell value known to be true.
    """
    value: int

    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        model.add(grid.cell(*self.cell)==self.value)

class Nonconsecutive(TwoCellConstraint):
    """Enforces that the values of two cells are nonconsecutive.
    """
    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = sort_cells(cell1, cell2)

    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 - cell2 != 1)
        model.add(cell2 - cell1 != 1)

class XBorder(BorderConstraint):
    """Enforces that the sum of two *adjacent* cells is 10.
    """
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 10)

class VBorder(BorderConstraint):
    """Enforces that the sum of two *adjacent* cells is 5.
    """
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 5)

class NegativeXBorder(TwoCellConstraint):
    """Enforces that the sum of two cells *IS NOT* 10.
    """
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 10)

class NegativeVBorder(TwoCellConstraint):
    """Enforces that the sum of two cells *IS NOT* 5.
    """
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 5)




############################################################
###################### SUDOKU PROBLEM ######################
############################################################

class SudokuProblem:
    """Main class coordinating model, data, and constraint objects for
    a given Sudoku problem.
    """
    model: CpModel
    grid: SudokuGrid
    _constraints:list[Constraint]

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True):
        self.model = CpModel()
        self.grid = self.create_grid(size, box_dims, one_indexed_cell_names)
        self._constraints = [SudokuConstraint]

    def create_grid(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True) -> SudokuGrid[IntVar]:
        os = 1 if one_indexed_cell_names else 0
        grid = [[self.model.new_int_var(1, size, f"Cell[{r+os},{c+os}]") 
                for c in range(size)] 
                for r in range(size)]
        return SudokuGrid.from_list(grid, box_dims)

    @property
    def constraints(self) -> list[Constraint]:
        return self._constraints

    def add_constraint(self, constraint:Constraint):
        self._constraints.append(constraint)

    def add_constraints(self, *constraints:Constraint):
        for constraint in constraints:
            if constraint not in self._constraints:
                self._constraints.append(constraint)

    def apply_constraints(self):
        Constraint.apply_constraints(self.model, self.grid, *self._constraints)

    
        


    



