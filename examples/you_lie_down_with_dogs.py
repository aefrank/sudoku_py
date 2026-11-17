"""
you lie down with dogs - by aqjhs
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000UTI

Doppelgänger Sudoku:

    Fill each cell of the main 9x9 grid such that every row, column and 3x3 box contains a 0 and eight different digits from 1-9.
    No two rows, no two columns and no two boxes may be missing the same digit.
    For each 0 in the grid, the digits missing in its row, column and region must be three different digits.

Doppel-Dög loop:

    Draw an orthogonal non-branching closed loop that doesn't cross or touch itself, not even diagonally.
    The loop "starts" at the cell marked with the dog and is considered to be oriented in the direction indicated by the arrow (i.e. r5c1 and r5c2 are on the loop).
    A cell on the loop with a digit D will have a value equal to the digit in the cell D steps away along the loop in the orientation given by the arrow.
    Cells not on the loop will have a value equal to the digit in them.

    Adjacent digits (not values) along the loop must have a difference of at least 5.
    Cells marked with a circle are not part of the loop and have a digit that equal to the count of the, up to 8, neighboring loop cells.
    Cells joined by a ball have the same value.
    Full Quad-Rank:

    All the 2x2 areas of the grid, when their values are read in western reading order, make a total of 64 four-digit numbers.
    Clues in the center of a 2x2 area show its rank among those 64 numbers, where the lowest is 1 and the highest is 64.
    One or more equal numbers are considered to be at rank N when there are N-1 numbers of strictly lower rank. (For example, we say there are three numbers in rank 20 when there are 19 numbers of lower rank and the next rank will be 23, i.e. the ranks could go ⋯, 19, 20, 20, 20, 23, ⋯)


"""

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model_helper import IntVar

N: int = 9 # 9x9 sudoku
model = cp_model.CpModel()
grid: list[list[IntVar]] = [[
    model.new_int_var(0, N, # 0 is allowed
    f"Cell[{r},{c}]") 
    for c in range(N)] 
    for r in range(N)
]