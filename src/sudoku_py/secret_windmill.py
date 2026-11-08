"""
Secret Windmill by marty_sears
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000U3J

Normal sudoku rules apply.

If two digits have an X between them, they sum to 10. If not, they don't.

If two digits have a V between them, they sum to 5. If not, they don't.

No two digits on the yellow circle may be consecutive.
"""
import itertools as it
import re
from time import time

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model_helper import IntVar

from sudoku_py.sudoku import SudokuProblem, SudokuSolver, SudokuSolutionPrinter

Coords = tuple[int,int]
CoordsPair = tuple[Coords,Coords]
VarPair = tuple[IntVar,IntVar] 


class WindmillSolver(SudokuSolver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Internals
    def _as_Cell(self, cell:IntVar|int|Coords, col:int|None=None):
        match cell:
            case int():
                assert isinstance(col,int)
                return self.problem.cell(cell, col)
            case tuple():
                return self.problem.cell(*cell)
            case IntVar():
                return cell
            case _:
                print("This should never be reached")

    def _add_V(self, cell1: IntVar, cell2: IntVar):
        self.problem.model.add(cell1 + cell2 == 5)    

    def _add_negative_V(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 + cell2 != 5)  

    def _add_X(self, cell1: IntVar, cell2: IntVar):
        self.problem.model.add(cell1 + cell2 == 10)   

    def _add_negative_X(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 + cell2 != 10)  

    def _add_nonconsecutive(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 - cell2 != 1)
        self.problem.model.add(cell2 - cell1 != 1)
    
    # Interface
    def cell(self, row: int, col: int) -> IntVar:
        return self.problem.cell(row,col)

    def get_all_adjacent_pairs(self):
        return self.problem.get_all_adjacent_pairs()

    def add_V(self, cell1: Coords|IntVar, cell2: Coords|IntVar):
        return self._add_V(self._as_Cell(cell1), self._as_Cell(cell2))

    def add_negative_V(self, cell1: Coords|IntVar, cell2: Coords|IntVar):
        return self._add_negative_V(self._as_Cell(cell1), self._as_Cell(cell2))
        
    def add_X(self, cell1: Coords|IntVar, cell2: Coords|IntVar):
        return self._add_X(self._as_Cell(cell1), self._as_Cell(cell2))

    def add_negative_X(self, cell1: Coords|IntVar, cell2: Coords|IntVar):
        return self._add_negative_X(self._as_Cell(cell1), self._as_Cell(cell2))

    def add_nonconsecutive(self, cell1: Coords|IntVar, cell2: Coords|IntVar):
        return self._add_nonconsecutive(self._as_Cell(cell1), self._as_Cell(cell2))


            
class BorderHighlightSolutionPrinter(SudokuSolutionPrinter):

    def __init__(self, problem:SudokuProblem
                , v_pairs:list[CoordsPair]=[]
                , x_pairs:list[CoordsPair]=[]
                ):
        super().__init__(problem.grid)
        self._problem = problem
        self._V = self._process_pairs(v_pairs)
        self._X = self._process_pairs(x_pairs)

    def _process_pairs(self, pairs:list[CoordsPair]=[]):
        # cast to IntVars
        X = [self._problem._as_canonical_cell_pair(c1,c2) for c1,c2 in pairs]
        # grab leftmost cell of horizontal pairs and topmost cell of vertical pairs
        horiz_pairs = [self._leftmost(c1,c2) for c1,c2 in self._horizontal_only(X)]
        vert_pairs = [self._topmost(c1,c2) for c1,c2 in self._vertical_only(X)]
        return horiz_pairs, vert_pairs

    def _get_all_horizontal_pairs(self):
        return self._problem.get_all_horizontal_pairs()

    def _get_all_vertical_pairs(self):
        return self._problem.get_all_vertical_pairs()

    def _horizontal_only(self, cell_pairs:list[VarPair]) -> list[VarPair]:
        return [cp for cp in cell_pairs if cp in self._get_all_horizontal_pairs()]

    def _vertical_only(self, cell_pairs:list[VarPair]) -> list[VarPair]:
            return [cp for cp in cell_pairs if cp in self._get_all_vertical_pairs()]


    def _leftmost(self, *cells:IntVar) -> IntVar:
        rows = [self._problem._to_coordinates(cell)[0] for cell in cells]
        return cells[rows.index(min(rows))]

    def _topmost(self, *cells:IntVar) -> IntVar:
        cols = [self._problem._to_coordinates(cell)[1] for cell in cells]
        return cells[cols.index(min(cols))]

    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )
        self._solution_count += 1

        for row in self._grid:
            # Add 'v' or 'x' between applicable horizontal pairs
            for cell in row:
                if cell in self._V[0]:
                    end = " v "
                elif cell in self._X[0]:
                    end = " x "
                else:
                    end = "   "
                # Add single underline (v) or double underline (x) between applicable vertical pairs
                if cell in self._V[1]:
                    u1,u2 = "\033[4m", "\033[0m"
                elif cell in self._X[1]:
                    u1,u2 = "\033[21m", "\033[24m"
                else:
                    u1,u2 = "",""
                # print cell with highlights
                print(f"{u1}{self.value(cell)}{u2}", end=end)
            print()
        print()


def secret_windmill():

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

    S = WindmillSolver()

    # no two cells on yellow circle are consecutive
    circle_cells = [(1,8),(1,9),(2,8),(2,9)]
    for a,b in it.combinations(circle_cells,2):
        S.add_nonconsecutive(a,b)

    v_pairs = [
          ((2,2),(2,3))
        , ((2,8),(3,8))
        , ((7,2),(8,2))
        , ((8,7),(8,8))
    ]
    V_constraint_pairs = [S.problem._as_canonical_cell_pair(*pair) for pair in v_pairs]
    # V_constraint_pairs = [(S.cell(*cell1),S.cell(*cell2)) for cell1,cell2 in v_pairs]
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
    X_constraint_pairs = [S.problem._as_canonical_cell_pair(*pair) for pair in x_pairs]


    adjacent_pairs = S.get_all_adjacent_pairs()
    for pair in adjacent_pairs:
        if pair in V_constraint_pairs:
            S.add_V(*pair)
        elif pair in X_constraint_pairs:
            S.add_X(*pair)
        # else:
        #     # This ruleset states that any adjacent cells that DON'T have a V (or X) 
        #     # between them MUST NOT add to 5 (or 10).
        #     S.add_negative_V(*pair)
        #     S.add_negative_X(*pair)

    return S.solve(solution_printer=BorderHighlightSolutionPrinter(S.problem 
                                                    , v_pairs=v_pairs
                                                    , x_pairs=x_pairs
                                                    ))


        
if __name__ == "__main__":
    secret_windmill()



