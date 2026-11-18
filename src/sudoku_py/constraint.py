
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from types import NotImplementedType
from typing import TypeGuard, TypeVar
import functools as ft
from ortools.sat.python.cp_model import CpModel, IntVar

from sudoku_py.core import AdjacentCellPair, Coords, sort_cells, verify_adjacency
from sudoku_py.grid import SudokuGrid

T = TypeVar("T")

###########################################################
################## ABSTRACT CONSTRAINTS ###################
###########################################################

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

    @staticmethod
    def handle_mismatched_compare(response_on_mismatch:bool|Exception|NotImplementedType):        
        def decorator[T](func:Callable[[T,T],bool]):
            def type_match(x:object) -> TypeGuard[T]:
                return type(x) is T

            @ft.wraps(func)
            def wrapper(self:T, other:object) -> bool:
                if type_match(other):
                    return func(self, other)
                if isinstance(response_on_mismatch, Exception):
                    raise response_on_mismatch
                return response_on_mismatch
            return wrapper
        return decorator

    @handle_mismatched_compare(False)
    def __eq__(self, other:Constraint) -> bool:
        return other is self

    @handle_mismatched_compare(NotImplemented)
    def __lt__(self, other:Constraint):
        return NotImplemented


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

    @Constraint.handle_mismatched_compare(False)
    def __eq__(self, other: MultiCellConstraint) -> bool:
        return (self.cells==other.cells) 
            
    @Constraint.handle_mismatched_compare(NotImplemented)
    def __lt__(self, other: MultiCellConstraint) -> bool: 
        return self.cells < other.cells 

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

    def _same_type__eq__(self: T, other: T) -> bool:
        return (self.cell==other.cell) # pyright: ignore[reportAttributeAccessIssue]
    
    def _same_type__lt__(self: T, other: T) -> bool:
            return (self.cell==other.cell) # pyright: ignore[reportAttributeAccessIssue]


class TwoCellConstraint(MultiCellConstraint):
    """Defines abstract interface for Sudoku constraints that relate
    exactly two cells.

    Enables the assumption that len(TwoCellConstraint.cells)==2,
    which is useful for type checking and adjacency requirements.
    """
    _cells:tuple[Coords, Coords] = field(init=False, repr=False)

    def __init__(self, cell1:Coords, cell2:Coords):
        self.cells = (cell1, cell2)

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



###########################################################
################## CONCRETE CONSTRAINTS ###################
###########################################################

class SudokuConstraintType(Constraint):
    """Implements the standard 'Sudoku' non-repeating constraints.

    Enforces AllDifferent CpModel constraint on grid rows, columns, and boxes.

    Singleton class with no internal data.
    """
    @staticmethod
    def apply(model: CpModel, grid: SudokuGrid[IntVar]) -> None:
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

    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        model.add(grid.cell(*self.cell)==self.value)

class Consecutive(TwoCellConstraint):
    """Enforces that the values of two cells are consecutive.
    """

    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        # need new variable to represent difference of cells
        max_diff = max(
            abs(cell1.domain.max()-cell2.domain.min()), 
            abs(cell2.domain.max()-cell1.domain.min())
        )
        # diff:IntVar = model.new_int_var(-max_diff, max_diff, name=f"{cell2.name}-{cell1.name}")
        # model.add(cell2 - cell1 == diff)
        model.add_abs_equality(1, cell2-cell1)

class Nonconsecutive(TwoCellConstraint):
    """Enforces that the values of two cells are nonconsecutive.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 - cell2 != 1)
        model.add(cell2 - cell1 != 1)

class XBorder(BorderConstraint):
    """Enforces that the sum of two *adjacent* cells is 10.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 10)

class VBorder(BorderConstraint):
    """Enforces that the sum of two *adjacent* cells is 5.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 == 5)

class NegativeXBorder(TwoCellConstraint):
    """Enforces that the sum of two cells *IS NOT* 10.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 10)

class NegativeVBorder(TwoCellConstraint):
    """Enforces that the sum of two cells *IS NOT* 5.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 + cell2 != 5)

class WhiteKropki(BorderConstraint, Consecutive):
    """Enforces that two adjacent cells are consecutive.
    """
    pass

class BlackKropki(BorderConstraint):
    """Enforces that two adjacent cells have a 2:1 ratio.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        # boolean switch handles "(cell1 == 2*cell2) OR (cell2 == 2*cell1)"
        cell2_is_twice_cell1:IntVar = model.new_bool_var(name=f"{cell2.name}==2 * `{cell1.name}`")
        model.add(cell2 == 2 * cell1).only_enforce_if(cell2_is_twice_cell1)
        model.add(cell1 == 2 * cell2).only_enforce_if(~cell2_is_twice_cell1)