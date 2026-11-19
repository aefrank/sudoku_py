"""
Pickleball - by FullDeckMissing
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000LK8
Rules: Kropki and German Whispers
"""


from my_utils import MyProblemSetup, MySolutionPrinter, concatenate_constraint_lists, partition_horizontal_vertical, remove_offset
from sudoku_py.constraint import BlackKropki, Constraint, GermanWhisperLine, WhiteKropki
from sudoku_py.core import Coords, partition, partition_out_types
from sudoku_py.problem import SudokuProblem


class PickleballSolutionPrinter(MySolutionPrinter):

    def __init__(self, problem: SudokuProblem, correct_solution: list[list[int]] | None = None):
        (white_kropki, black_kropki) = partition_out_types(problem.constraints, WhiteKropki, BlackKropki)
        self._white_kropki_print_targets: tuple[set[Coords], set[Coords]] = partition_horizontal_vertical(white_kropki) 
        self._black_kropki_print_targets: tuple[set[Coords], set[Coords]] = partition_horizontal_vertical(black_kropki)  
        super().__init__(problem, correct_solution)

    def print_target(self, cell:Coords, *, invert_kropki_markings=False):
        """Prints cell value with Kropki annotation to terminal in current 
        location.
        """
        filled_circle = "\u25CF"
        empty_circle = "\u25CB"
        kropki_targets = (self._black_kropki_print_targets, self._white_kropki_print_targets) if invert_kropki_markings else (self._white_kropki_print_targets, self._black_kropki_print_targets)
        # HORIZONTAL ANNOTATIONS
        if cell in kropki_targets[0][0]:
            end =  f" {empty_circle} "
        elif cell in kropki_targets[1][0]:
            end =  f" {filled_circle} "
        else:
            end = "   "
        # VERTICAL ANNOTATIONS:
        # Add single underline (white) or double underline (black) between applicable vertical pairs
        if cell in kropki_targets[0][1]:
            u1,u2 = "\033[4m", "\033[0m"
        elif cell in kropki_targets[1][1]:
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
              (5,1), (4,2), (3,3)
            , (2,4), (1,5), (2,6)
            , (3,7), (4,8), (5,9)
            , (6,8), (7,7), (8,6)
            , (9,5)
        )
        , (
              (3,4), (3,5), (3,6)
            , (4,7), (5,7), (6,7)
            , (7,6), (7,5), (7,4)
            , (6,3), (5,3), (4,3)
            , (3,4) # closed loop: repeat first cell
        )
        , (
              (4,5), (5,6), (6,5)
            , (5,4), (4,5) # closed loop: repeat first cell
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
        , [GermanWhisperLine(remove_offset(cells, 1)) for cells in german_whispers_lines]
        ))

    problem = MyProblemSetup(
              one_indexed=True
            , constraints=constraint_list
            , correct_solution=SOLUTION
        )
    
    problem.solve(solution_printer=PickleballSolutionPrinter(problem, SOLUTION))


if __name__=="__main__":
    pickleball()