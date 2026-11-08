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

    # Internals
    def __as_Cell(self, cell:IntVar|int|tuple[int,int], col:int|None=None):
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

    def __add_V(self, cell1: IntVar, cell2: IntVar):
        self.problem.model.add(cell1 + cell2 == 5)    

    def __add_negative_V(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 + cell2 != 5)  

    def __add_X(self, cell1: IntVar, cell2: IntVar):
        self.problem.model.add(cell1 + cell2 == 10)   

    def __add_negative_X(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 + cell2 != 10)  

    def __add_nonconsecutive(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 - cell2 != 1)
        self.problem.model.add(cell2 - cell1 != 1)
    
    # Interface
    def cell(self, row: int, col: int) -> IntVar:
        return self.problem.cell(row,col)

    def get_all_adjacent_pairs(self):
        return self.problem.get_all_adjacent_pairs()

    def add_V(self, cell1: tuple[int,int]|IntVar, cell2: tuple[int,int]|IntVar):
        return self.__add_V(self.__as_Cell(cell1), self.__as_Cell(cell2))

    def add_negative_V(self, cell1: tuple[int,int]|IntVar, cell2: tuple[int,int]|IntVar):
        return self.__add_negative_V(self.__as_Cell(cell1), self.__as_Cell(cell2))
        
    def add_X(self, cell1: tuple[int,int]|IntVar, cell2: tuple[int,int]|IntVar):
        return self.__add_X(self.__as_Cell(cell1), self.__as_Cell(cell2))

    def add_negative_X(self, cell1: tuple[int,int]|IntVar, cell2: tuple[int,int]|IntVar):
        return self.__add_negative_X(self.__as_Cell(cell1), self.__as_Cell(cell2))

    def add_nonconsecutive(self, cell1: tuple[int,int]|IntVar, cell2: tuple[int,int]|IntVar):
        return self.__add_nonconsecutive(self.__as_Cell(cell1), self.__as_Cell(cell2))

    
            



def secret_windmill():
    S = SudokuSolverPlus()

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
    V_constraint_pairs = [(S.cell(*cell1),S.cell(*cell2)) for cell1,cell2 in v_pairs]
    x_pairs = [ 
          ((2,3), (3,3))
        , ((3,3), (3,4))
        , ((3,4), (4,4))
        , ((4,4), (4,5))

        , ((3,8), (3,7))
        , ((3,7), (4,7))
        , ((4,7), (4,6))
        , ((4,6), (5,6))

        , ((5,4), (6,4))
        , ((6,4), (6,3))
        , ((6,3), (7,3))
        , ((7,3), (7,2))

        , ((6,5), (6,6))
        , ((6,6), (7,6))
        , ((7,6), (7,7))
        , ((7,7), (8,7))
    ]
    X_constraint_pairs = [(S.cell(*cell1),S.cell(*cell2)) for cell1,cell2 in x_pairs]


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

    return S.solve()


        
if __name__ == "__main__":
    secret_windmill()



