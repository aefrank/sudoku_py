"""
Secret Windmill by marty_sears
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000U3J

Normal sudoku rules apply.

If two digits have an X between them, they sum to 10. If not, they don't.

If two digits have a V between them, they sum to 5. If not, they don't.

No two digits on the yellow circle may be consecutive.
"""
import itertools as it

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model_helper import IntVar

from sudoku_py.sudoku import SudokuSolver


class SudokuSolverPlus(SudokuSolver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    
    def get_all_adjacent_pairs(self) -> list[tuple[IntVar,IntVar]]:
        horizontal_pairs = [(self.grid[r][c], self.grid[r][c+1]) for r,c in it.product(range(self.N), range(self.N-1))]
        vertical_pairs = [(self.grid[r][c], self.grid[r+1][c]) for r,c in it.product(range(self.N-1), range(self.N))]
        return horizontal_pairs + vertical_pairs

    def add_V(self, cell1: tuple[int,int], cell2: tuple[int,int]):
        self.model.add(self.cell(*cell1)+self.cell(*cell2)==5)

    def add_negative_V(self, cell1: tuple[int,int], cell2: tuple[int,int]):
        self.model.add(self.cell(*cell1)+self.cell(*cell2)!=5)
        
    def add_X(self, cell1: tuple[int,int], cell2: tuple[int,int]):
            self.model.add(self.cell(*cell1)+self.cell(*cell2)==10)

    def add_negative_X(self, cell1: tuple[int,int], cell2: tuple[int,int]):
        self.model.add(self.cell(*cell1)+self.cell(*cell2)!=10)

    def add_nonconsecutive(self, cell1: tuple[int,int], cell2: tuple[int,int]):
            self.model.add(self.cell(*cell1)-self.cell(*cell2)!=1)
            self.model.add(self.cell(*cell2)-self.cell(*cell1)!=1)



S = SudokuSolverPlus()
print(S.get_all_adjacent_pairs())
print(len(S.get_all_adjacent_pairs()))

def secret_windmill(self):
    S = SudokuSolverPlus()

    # no two cells on yellow circle ((1,8),(1,9),(2,9),(2,8)) cannot be consecutive
    circle_cells = [(1,8),(1,9),(2,8),(2,9)]
    for a,b in it.combinations(circle_cells,2):
        S.add_nonconsecutive(a,b)

    adjacent_pairs = S.get_all_adjacent_pairs()

    # V constraints (cells must add to 5)
    V_constraint_pairs = [((2,2),(2,3)), ((2,8),(3,8)), ((7,2),(8,2)), ((8,7),(8,8))]
    for pair in adjacent_pairs:
        if pair in V_constraint_pairs:
            S.add_V(*pair)
        else:
            S.add_negative_V(*pair)


    # X constraints
    S.add_X((2,3), (3,3))
    S.add_X((3,3), (3,4))
    S.add_X((3,4), (4,4))
    S.add_X((4,4), (4,5))

    S.add_X((3,8), (3,7))
    S.add_X((3,7), (4,7))
    S.add_X((4,7), (4,6))
    S.add_X((4,6), (5,6))

    S.add_X((5,4), (6,4))
    S.add_X((6,4), (6,3))
    S.add_X((6,3), (7,3))
    S.add_X((7,3), (7,2))

    S.add_X((6,5), (6,6))
    S.add_X((6,6), (7,6))
    S.add_X((7,6), (7,7))
    S.add_X((7,7), (8,7))



        



