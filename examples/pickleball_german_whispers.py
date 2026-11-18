"""
Pickleball - by FullDeckMissing
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000LK8
Rules: Kropki and German Whispers
"""


from collections.abc import Iterable
from dataclasses import dataclass, field
import functools as ft
import itertools as it
from typing import Any

from ortools.sat.python.cp_model import CpModel, CpSolver, IntVar

from my_utils import MyProblemSetup, MySolutionPrinter, concatenate_constraint_lists, remove_offset
from sudoku_py.constraint import BlackKropki, BorderConstraint, Constraint, MultiCellConstraint, TwoCellConstraint, WhiteKropki
from sudoku_py.core import Coords, partition
from sudoku_py.grid import SudokuGrid
from sudoku_py.problem import SudokuProblem

# @ft.total_ordering
# @dataclass
# class GermanWhisperPair(TwoCellConstraint):
#     minimum_difference:int=5

#     def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
#         cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
#         # boolean switch handles "(cell1 == 2*cell2) OR (cell2 == 2*cell1)"
#         cell1_gt_cell2:IntVar = model.new_bool_var(name=f"{cell1.name} > {cell2.name}")
#         model.add(cell1-cell2 >= self.minimum_difference).only_enforce_if(cell1_gt_cell2)
#         model.add(cell2-cell1 >= self.minimum_difference).only_enforce_if(~cell1_gt_cell2)

#     @Constraint.handle_mismatched_compare(False)
#     def __eq__(self, other: GermanWhisperPair) -> bool:
#         return super().__eq__(self, other) and self.minimum_difference==other.minimum_difference

#     @Constraint.handle_mismatched_compare(False)
#     def __lt__(self, other: GermanWhisperPair) -> bool:
#         # use minimum_difference as a tie-breaker
#         out = super().__lt__(self, other)
#         if not out: # could be ==
#             return self.minimum_difference < other.minimum_difference
#         return out

@ft.total_ordering
@dataclass
class WhisperLine(MultiCellConstraint):
    """Defines a sequence of cells where consecutive cells must differ by at least some minimum difference.

    Most common variants are German Whispers (minimum difference=5) and Dutch Whispers (minimum difference=4).
    """
    minimum_difference:int

    def __init__(self, cells:tuple[Coords,...], minimum_difference:int=5):
        self._cells = cells # DO NOT SORT
        self.minimum_difference = minimum_difference

    @property
    def cells(self) -> tuple[Coords,...]:
        return self._cells # DO NOT SORT

    @property
    def pairwise(self) -> Iterable[tuple[Coords, Coords]]:
        return it.pairwise(self.cells)

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


@ft.total_ordering
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
        for c1, c2 in self.pairwise:
            cell1, cell2 = grid.cell(*c1), grid.cell(*c2)
            model.add(cell1-cell2 >= self.minimum_difference).only_enforce_if(start_high)
            model.add(cell2-cell1 >= self.minimum_difference).only_enforce_if(~start_high)

    


    



class GermanWhisperGraph(MultiCellConstraint): # TODO
    """For non-linear German Whisper formations.
    
    i.e. where at least one cell connects to at least 3 other cells
    """
    def __init__(self, *cells: Coords):
        raise NotImplementedError



class PickleballSolutionPrinter(MySolutionPrinter):

    @staticmethod
    def partition_horizontal_vertical(border_constraints:Iterable[BorderConstraint]):
        horizontal, vertical = partition(border_constraints, lambda x: x.is_horizontal) # pyright: ignore[reportAttributeAccessIssue]
        return (
              set(sorted(cons.cells)[0] for cons in horizontal)
            , set(sorted(cons.cells)[0] for cons in vertical)
            )


    def __init__(self, problem: SudokuProblem, correct_solution: list[list[int]] | None = None):
        white_kropki, not_white_kropki = partition(problem.constraints, lambda x: isinstance(x, WhiteKropki))
        black_kropki, _ = partition(not_white_kropki, lambda x: isinstance(x, BlackKropki))
        self._white_kropki_print_targets: tuple[set[Coords], set[Coords]] = self.partition_horizontal_vertical(white_kropki) # pyright: ignore[reportArgumentType]
        self._black_kropki_print_targets: tuple[set[Coords], set[Coords]] = self.partition_horizontal_vertical(black_kropki) # pyright: ignore[reportArgumentType]
        super().__init__(problem, correct_solution)

    def print_target(self, cell:Coords, *, invert_kropki_colors=False):
        """Prints cell value with Kropki annotation to terminal in current 
        location.
        """
        filled_circle = "\u25CF"
        empty_circle = "\u25CB"
        # HORIZONTAL ANNOTATIONS
        if cell in self._white_kropki_print_targets[0]:
            end =  f" {empty_circle} "
        elif cell in self._black_kropki_print_targets[0]:
            end =  f" {filled_circle} "
        else:
            end = "   "
        # VERTICAL ANNOTATIONS:
        # Add single underline (white) or double underline (black) between applicable vertical pairs
        if cell in self._white_kropki_print_targets[1]:
            u1,u2 = "\033[4m", "\033[0m"
        elif cell in self._black_kropki_print_targets[1]:
            u1,u2 = "\033[21m", "\033[24m"
        else:
            u1,u2 = "",""
        # print cell with highlights
        val = self.value(self.grid.cell(*cell))
        print(f"{u1}{val}{u2}{end}", end="")




def pickleball():
    SOLUTION:list[list[int]] = [
          [8,1,6,4,3,5,9,2,7]
        , [7,2,3,9,6,8,5,4,1]
        , [9,5,4,2,7,1,3,6,8]
        , [1,9,7,5,2,3,6,8,4]
        , [4,6,2,8,9,7,1,5,3]
        , [5,3,8,6,1,4,7,9,2]
        , [6,7,9,1,8,2,4,3,5]
        , [2,4,1,3,5,9,8,7,6]
        , [3,8,5,7,4,6,2,1,9]
    ]

    black_kropki_pairs:list[tuple[Coords,Coords]] = [
          ((1,5), (2,5))
        , ((3,3), (3,4))
        , ((3,7), (4,7))
        , ((7,6), (7,7))
    ]

    white_kropki_pairs:list[tuple[Coords,Coords]] = [
          ((4,5), (4,6))
        , ((6,3), (7,3))
    ]

    german_whispers_lines:list[tuple[Coords,...]] = [
        (
            (2,1), (1,2)
        )
        , (
            (5,1), (4,2), (3,3), (2,4), (1,5), (2,6), (3,7), (4,8), (5,9), (6,8), (7,7), (8,6), (9,5)
        )
        , (
              (3,4), (3,5), (3,6), (4,7), (5,7), (6,7), (7,6), (7,5), (7,4), (6,3), (5,3), (4,3)
            , (3,4) # closed loop
        )
        , (
              (4,5), (5,6), (6,5), (5,4)
            , (4,5) # closed loop
        ) 
        , (
            (6,2), (7,3), (8,4)
        )
        , (
            (7,2), (8,1), (9,2), (8,3)
        )
        , (
            (8,9), (9,8)
        )
    ]

    constraint_list:list[Constraint] = concatenate_constraint_lists((
          [BlackKropki(*remove_offset(cells, 1)) for cells in black_kropki_pairs]
        , [WhiteKropki(*remove_offset(cells, 1)) for cells in white_kropki_pairs]
        # , [GermanWhisperLine(remove_offset(cells, 1)) for cells in german_whispers_lines]
        ))

    problem = MyProblemSetup(
              one_indexed=True
            , constraints=constraint_list
            , correct_solution=SOLUTION
        )
    
    problem.solve(solution_printer=PickleballSolutionPrinter(problem, SOLUTION))


if __name__=="__main__":
    pickleball()