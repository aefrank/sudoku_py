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

from sudoku_py.sudoku import OneIndexedSudokuProblem, SudokuProblem, SudokuSolver, SudokuSolutionPrinter, CellVar

Coords = tuple[int,int]
CoordsPair = tuple[Coords,Coords]
VarPair = tuple[IntVar,IntVar] 


class XVSudokuProblem(OneIndexedSudokuProblem):

    # INTERNAL
    def __init__(self, size: int = 9, box_dims: tuple[int, int] = (3, 3)):
        super().__init__(size, box_dims)
        self.__V_borders:tuple[set[tuple[int,int]],set[tuple[int,int]]] = (set(),set())
        self.__X_borders:tuple[set[tuple[int,int]],set[tuple[int,int]]] = (set(),set())


    def __add_V_constraint(self, cell1:CellVar, cell2:CellVar):
        self.model.add(cell1 + cell2 == 5)

    def __add_negative_V_constraint(self, cell1:CellVar, cell2:CellVar):
        self.model.add(cell1 + cell2 != 5)

    def __add_X_constraint(self, cell1:CellVar, cell2:CellVar):
        self.model.add(cell1 + cell2 == 10)

    def __add_negative_X_constraint(self, cell1:CellVar, cell2:CellVar):
        self.model.add(cell1 + cell2 != 10)


    def __is_horizontal_adjacent_pair(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        return (cell1[0]-cell2[0])==0 and (cell1[1]-cell2[1])!=0

    def __is_vertical_adjacent_pair(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        return (cell1[0]-cell2[0])!=0 and (cell1[1]-cell2[1])==0
    
        
    def __add_V_border(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        if self.__is_horizontal_adjacent_pair(cell1, cell2):
            self.__V_borders[0].add(sorted([cell1,cell2])[0])
        elif self.__is_vertical_adjacent_pair(cell1, cell2):
            self.__V_borders[1].add(sorted([cell1,cell2])[0])    

    def __add_X_border(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        if self.__is_horizontal_adjacent_pair(cell1, cell2):
            self.__X_borders[0].add(sorted([cell1,cell2])[0])
        elif self.__is_vertical_adjacent_pair(cell1, cell2):
            self.__X_borders[1].add(sorted([cell1,cell2])[0])    
    
    # INTERFACE

    @property
    def V_borders(self):
        return self.__V_borders

    @property
    def X_borders(self):
        return self.__X_borders
    
    
    def add_V(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        cell1,cell2 = sorted((cell1,cell2))
        self.__add_V_border(cell1,cell2)
        return self.__add_V_constraint(self.cell(*cell1),self.cell(*cell2))
    
    def add_negative_V(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        cell1,cell2 = sorted((cell1,cell2))
        return self.__add_negative_V_constraint(self.cell(*cell1),self.cell(*cell2))
    
    def add_X(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        cell1,cell2 = sorted((cell1,cell2))
        self.__add_X_border(cell1,cell2)
        return self.__add_X_constraint(self.cell(*cell1),self.cell(*cell2))
    
    def add_negative_X(self, cell1:tuple[int,int], cell2:tuple[int,int]):
        cell1,cell2 = sorted((cell1,cell2))
        return self.__add_negative_X_constraint(self.cell(*cell1),self.cell(*cell2))

    def infer_all_negative_XV_constraints(self):
        '''Enforce that any adjacent pair that does not have either an X or V constraint
        must instead have a negative X and V constraint.
        '''
        adjacent_pairs = self.get_all_adjacent_pairs()
        for pair in adjacent_pairs:
            if pair not in self.__V_borders and pair not in self.__X_borders:
                self.add_negative_V(*pair)
                self.add_negative_X(*pair)


class WindmillSolver(SudokuSolver):

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), **kwargs):
        super().__init__(size, box_dims, **kwargs)
        self.problem = XVSudokuProblem(size, box_dims)

    def __add_nonconsecutive(self, cell1:IntVar, cell2:IntVar):
        self.problem.model.add(cell1 - cell2 != 1)
        self.problem.model.add(cell2 - cell1 != 1)
    
    # Interface
    def cell(self, row: int, col: int) -> IntVar:
        return self.problem.cell(row,col)

    def get_all_adjacent_pairs(self) -> list[tuple[tuple[int,int],tuple[int,int]]]:
        return self.problem.get_all_adjacent_pairs()

    def add_V(self, cell1: Coords, cell2: Coords):
        return self.problem.add_V(cell1, cell2)

    def add_negative_V(self, cell1: Coords, cell2: Coords):
        return self.problem.add_negative_V(cell1, cell2)
        
    def add_X(self, cell1: Coords, cell2: Coords):
            return self.problem.add_X(cell1, cell2)
    
    def add_negative_X(self, cell1: Coords, cell2: Coords):
        return self.problem.add_negative_X(cell1, cell2)

    def add_nonconsecutive(self, cell1: Coords, cell2: Coords):
        return self.__add_nonconsecutive(self.problem.cell(*cell1), self.problem.cell(*cell2))



    def add_XV_and_infer_negative_XV(self
                           , V_pairs:list[tuple[tuple[int,int], tuple[int,int]]]
                           , X_pairs:list[tuple[tuple[int,int], tuple[int,int]]]
                           ):
        V_pairs = [self.problem.as_canonical_coords_pair(pair) for pair in V_pairs]
        X_pairs = [self.problem.as_canonical_coords_pair(pair) for pair in X_pairs]
        adjacent_pairs = self.get_all_adjacent_pairs()
        for pair in adjacent_pairs:
            if pair in V_pairs:
                self.add_V(*pair)
            elif pair in X_pairs:
                self.add_X(*pair)
            else:
                # This ruleset states that any adjacent cells that DON'T have a V (or X) 
                # between them MUST NOT add to 5 (or 10).
                self.add_negative_V(*pair)
                self.add_negative_X(*pair)
    
    def add_XV_constraints(self
                           , V_pairs:list[tuple[tuple[int,int], tuple[int,int]]]
                           , X_pairs:list[tuple[tuple[int,int], tuple[int,int]]]
                           , infer_negative_constraints:bool=True):
        if infer_negative_constraints:
            return self.add_XV_and_infer_negative_XV(V_pairs, X_pairs)
        
        for pair in V_pairs:
            self.add_V(*self.problem.as_canonical_coords_pair(pair))
        for pair in X_pairs:
            self.add_X(*self.problem.as_canonical_coords_pair(pair))

    def add_circle_constraints(self, circle_cells:list[tuple[int,int]]):
        # no two cells on yellow circle are consecutive
        for a,b in it.combinations(circle_cells,2):
            self.add_nonconsecutive(a,b)


class XVSudokuSolutionPrinter(cp_model.CpSolverSolutionCallback):

    def __init__(self, problem:XVSudokuProblem, correct_solution:list[list[int]]|None=None):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.problem = problem
        self.V = self.problem.V_borders
        self.X = self.problem.X_borders
        self._solution_count = 0
        self._start_time = time()
        self.__correct_solution = correct_solution
        
        
    @property
    def solution_count(self) -> int:
        return self._solution_count

    def check_cell(self, i, j, val):
        assert self.__correct_solution is not None
        return self.__correct_solution[i][j] == val
    
    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )
        self._solution_count += 1

        if self.__correct_solution:
            correct = True
        for i, row in enumerate(self.problem.grid):
            # Add 'v' or 'x' between applicable horizontal pairs
            for j, cell in enumerate(row):
                coords = (i+1,j+1) # one-indexed
                if coords in self.V[0]:
                    end = " v "
                elif coords in self.X[0]:
                    end = " x "
                else:
                    end = "   "
                # Add single underline (v) or double underline (x) between applicable vertical pairs
                if coords in self.V[1]:
                    u1,u2 = "\033[4m", "\033[0m"
                elif coords in self.X[1]:
                    u1,u2 = "\033[21m", "\033[24m"
                else:
                    u1,u2 = "",""
                # print cell with highlights
                val = self.value(cell)
                print(f"{u1}{val}{u2}", end=end)
                if self.__correct_solution:
                    correct = correct and self.check_cell(i,j,val)

            print()
        if self.__correct_solution and correct:
            print("SOLUTION CORRECT!")
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

    solver = WindmillSolver()

#     # no two cells on yellow circle are consecutive
    circle_cells = [(1,8),(1,9),(2,8),(2,9)]
    solver.add_circle_constraints(circle_cells)

    v_pairs = [
          ((2,2),(2,3))
        , ((2,8),(3,8))
        , ((7,2),(8,2))
        , ((8,7),(8,8))
    ]
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
    
    solver.add_XV_constraints(v_pairs, x_pairs, True)
    solver.solver.parameters.enumerate_all_solutions = True
    return solver.solve(solution_printer=XVSudokuSolutionPrinter(solver.problem
            ,  correct_solution=SOLUTION
    #                                                 # , v_pairs=v_pairs
    #                                                 # , x_pairs=x_pairs
                                                    ))
 

        
if __name__ == "__main__":
    secret_windmill()



