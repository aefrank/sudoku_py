
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import reduce, total_ordering, wraps
from itertools import pairwise
from types import NotImplementedType
from typing import Iterable, TypeGuard, TypeVar

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
            def type_match(x:object, self:T) -> TypeGuard[T]:
                return type(x) is type(self)

            @wraps(func)
            def wrapper(self:T, other:object) -> bool:
                if type_match(other, self):
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


@total_ordering
class MultiCellConstraint(Constraint):
    """Defines abstract interface for Sudoku constraints that relate
    multiple cells.

    Enforces a canonical (sorted) order for storing collections of cells
    so they can be easily checked without worrying about permutations.
    """
    _cells:tuple[Coords, ...]

    def __init__(self, cells:Iterable[Coords]):
        self._cells = tuple(cells)

    @property
    def cells(self) -> tuple[Coords, ...]:
        return sort_cells(*self._cells)

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
@total_ordering
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


class LineConstraint(MultiCellConstraint):
    """Defines a constraint on a linear sequence of cells. 
    """

    def __init__(self, cells:tuple[Coords,...]):
        self._cells = cells # DO NOT SORT

    @property
    def cells(self) -> tuple[Coords,...]:
        """Return cells constrained by this line in order.
        """
        return self._cells # DO NOT SORT

    @property
    def pairwise(self) -> Iterable[tuple[Coords, Coords]]:
        """Returns adjacent pairs of cells along line.
        """
        return pairwise(self.cells)


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
            box_cells = reduce(lambda x,y: x+y, box)
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

    def __hash__(self) -> int: # TODO: implement hash in ABCs as hash((type(self), *self.hashable_attributes))
        return hash((type(self), self.cell, self.value))


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
        model.add_abs_equality(1, cell2-cell1)

class Nonconsecutive(TwoCellConstraint):
    """Enforces that the values of two cells are nonconsecutive.
    """
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        model.add(cell1 - cell2 != 1)
        model.add(cell2 - cell1 != 1)

###############################################################################
#############               BORDER CONSTRAINTS          #######################
###############################################################################

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
        cell2_is_twice_cell1:IntVar = model.new_bool_var(name=f"{cell2.name}==2 * {cell1.name}")
        model.add(cell2 == 2 * cell1).only_enforce_if(cell2_is_twice_cell1)
        model.add(cell1 == 2 * cell2).only_enforce_if(~cell2_is_twice_cell1)




###############################################################################
############# ##              LINE CONSTRAINTS          #######################
###############################################################################

@total_ordering
@dataclass
class WhisperLine(LineConstraint):
    """Defines a sequence of cells where consecutive cells must differ by at least some minimum difference.

    Most common variants are German Whispers (minimum difference=5) and Dutch Whispers (minimum difference=4).
    """
    minimum_difference:int

    def __init__(self, cells:tuple[Coords,...], minimum_difference:int=5):
        self._cells = cells # DO NOT SORT
        self.minimum_difference = minimum_difference


    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        for c1, c2 in self.pairwise:
            cell1, cell2 = grid.cell(*c1), grid.cell(*c2)
            # boolean switch handles enforcing the magnitude of the difference is at least minimum_difference 
            cell1_gt_cell2:IntVar = model.new_bool_var(name=f"{cell1.name} > {cell2.name}")
            model.add(cell1-cell2 >= self.minimum_difference).only_enforce_if(cell1_gt_cell2)
            model.add(cell2-cell1 >= self.minimum_difference).only_enforce_if(~cell1_gt_cell2)

    @Constraint.handle_mismatched_compare(False)
    def __eq__(self, other: WhisperLine) -> bool:
        return super().__eq__(self, other) and self.minimum_difference==other.minimum_difference

    @Constraint.handle_mismatched_compare(False)
    def __lt__(self, other: WhisperLine) -> bool:
        out = super().__lt__(self, other)
        # use minimum_difference as a tie-breaker if needed
        if not out:
            return self.minimum_difference < other.minimum_difference
        return out


@total_ordering
@dataclass(init=False)
class GermanWhisperLine(WhisperLine):
    """Defines a sequence of cells where consecutive cells are connected by a German Whisper constraint.

    ASssumes minimum difference is defined to partition cells along line into alternating high and low digits.
    For example, for a traditional 9x9 sudoku where cells have values 1-9, minimum_difference=5. This makes
    consecutive cells on a German Whisper line alternate between values in {1,2,3,4} and those in {6,7,8,9}.

    If this assumption does not hold, use the parent class `WhisperLine` instead.
    """
    minimum_difference:int=5
    name:str
    __INSTANCE_COUNT:int=field(default=0, repr=False, compare=False, hash=False)


    def __init__(self, cells: Iterable[Coords], minimum_difference: int = 5):
        super().__init__(tuple(cells), minimum_difference)
        __class__.__INSTANCE_COUNT += 1 # increment program-wide instance count
        self.name = f"{__class__.__name__}{self.__INSTANCE_COUNT}"

    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        # single boolean switch handles if line goes low-high-low-high or high-low-high-low
        start_high:IntVar = model.new_bool_var(name=f"{self.name}: {grid.cell(*self.cells[0]).name} is high-valued")
        high = True
        for c1,c2 in self.pairwise:
            cell1, cell2 = grid.cell(*c1), grid.cell(*c2)
            if high:
                model.add(cell1-cell2 >= self.minimum_difference).only_enforce_if(start_high)
                model.add(cell2-cell1 >= self.minimum_difference).only_enforce_if(~start_high)
            else:
                model.add(cell1-cell2 >= self.minimum_difference).only_enforce_if(~start_high)
                model.add(cell2-cell1 >= self.minimum_difference).only_enforce_if(start_high)
            high = not high


class GermanWhisperGraph(MultiCellConstraint): # TODO
    """For non-linear German Whisper formations.
    
    i.e. where at least one cell connects to at least 3 other cells
    """
    def __init__(self, *cells: Coords):
        raise NotImplementedError