
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from copy import deepcopy
from dataclasses import dataclass, field
import functools as ft
from itertools import filterfalse, product, tee
from time import time
from typing import Any, Generic, Iterable, NewType, Optional, TypeIs, TypeVar, overload

from ortools.sat.python.cp_model import CpModel
from ortools.sat.python.cp_model_helper import IntVar



############        CELL COORDINATES   ########################

T = TypeVar("T")
CellVar = IntVar

type Coords = tuple[int,int]
def is_Coords(x:Any) -> TypeIs[Coords]:
    if isinstance(x, tuple):
        if len(x)==2 and isinstance(x[0],int) and isinstance(x[1],int):
            return True
    return False


############        CELL ADJACENCY      ########################
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
############## VARIABLE STORAGE: SUDOKUGRID ################
############################################################

class BaseSudokuGrid(Generic[T]):
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
        return [self.__col(i) for i in range(self.size)]

    def boxes(self) -> list[list[list[T]]]:
        return [self.__box(i) for i in range(self.rows_of_boxes*self.cols_of_boxes)]

    def cells(self) -> list[T]:
        return ft.reduce(lambda x,y: x+y, self.__rows())

    def get_row(self, item:T) -> int:
        return self.__index(item)[0]

    def get_col(self, item:T) -> int:
        return self.__index(item)[1]

    def get_box(self, item:T) -> int:
        for i,box in enumerate(self.boxes()):
            if item in ft.reduce(lambda x,y: x+y, box):
                return i
        # if we get to here, item does not exist in grid
        raise ValueError(item)

    def same_row(self, cell1:T, cell2:T) -> bool:
            return self.__get_row(cell1) == self.__get_row(cell2)
    
    def same_col(self, cell1:T, cell2:T) -> bool:
        return self.__get_col(cell1) == self.__get_col(cell2)

    def same_box(self, cell1:T, cell2:T) -> bool:
        return self.__get_box(cell1) == self.__get_box(cell2)

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> Generator[list[T], Any, Any]:
        for item in self.items:
            yield item

    # avoid name-mangling
    __row = row
    __col = col
    __box = box
    __cell = cell
    __rows = rows
    __cols = cols
    __boxes = boxes
    __cells = cells
    __index = index
    __get_row = get_row
    __get_col = get_col
    __get_box = get_box
    __populate_grid = populate_grid


class SudokuGrid(BaseSudokuGrid[T]):

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

############################################################
####################### CONSTRAINTS ########################
############################################################



############        ABSTRACT CONSTRAINTS   ########################
class Constraint(ABC):
    @abstractmethod
    def apply(self, model:CpModel, grid:SudokuGrid) -> None: ...

    @staticmethod
    def apply_constraints(model:CpModel, grid:SudokuGrid, *constraints:Constraint) -> None:
        for constraint in constraints:
            constraint.apply(model, grid)

@ft.total_ordering
class MultiCellConstraint(Constraint):
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
    value: int

    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        model.add(grid.cell(*self.cell)==self.value)

class Nonconsecutive(TwoCellConstraint):
    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = sort_cells(cell1, cell2)

    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 - cell2 != 1)
        model.add(cell2 - cell1 != 1)

class XBorder(BorderConstraint):
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 10)

class VBorder(BorderConstraint):
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 5)

class NegativeXBorder(BorderConstraint):
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 10)

class NegativeVBorder(BorderConstraint):
    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 5)




############################################################
###################### SUDOKU PROBLEM ######################
############################################################

class SudokuProblem:
    model: CpModel
    grid: SudokuGrid
    _constraints:list[Constraint]

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True):
        self.model = CpModel()
        self.grid = self.create_grid(size, box_dims, one_indexed_cell_names)
        self._constraints = [SudokuConstraint]

    def create_grid(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True) -> SudokuGrid[CellVar]:
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

    
        


    



