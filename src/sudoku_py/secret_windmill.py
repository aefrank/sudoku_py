"""
Secret Windmill by marty_sears
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000U3J

Normal sudoku rules apply.

If two digits have an X between them, they sum to 10. If not, they don't.

If two digits have a V between them, they sum to 5. If not, they don't.

No two digits on the yellow circle may be consecutive.
"""
from collections.abc import Sequence
from itertools import combinations
from time import time

from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback

from sudoku_py.constraints import Constraint, Coords, NegativeVBorder, NegativeXBorder, Nonconsecutive, SudokuConstraint, VBorder, XBorder, sort_cells
from sudoku_py.sudoku import SudokuProblem

############################################################
################### EXAMPLE PROBLEM ########################
############################################################



class XVSolutionPrinter(CpSolverSolutionCallback):

    def __init__(self
                 , problem: SudokuProblem
                #  , v_constraints:list[VBorder]=[]
                #  , x_constraints:list[XBorder]=[]
                 , correct_solution:list[list[int]]|None=None
                ):
        CpSolverSolutionCallback.__init__(self)
        self.model = problem.model
        self.grid = problem.grid
        self.v_borders, self.x_borders = self.get_xv(*problem.constraints)
        self.__correct_solution = correct_solution
        
        self._solution_count = 0
        self._start_time = time()


    def get_xv(self, *constraints:Constraint) -> tuple[tuple[set[XBorder], set[XBorder]], tuple[set[VBorder], set[VBorder]]]:
        x_constraints:tuple[set[XBorder], set[XBorder]] = (set(), set())
        v_constraints:tuple[set[VBorder], set[VBorder]] = (set(), set())
        for constraint in constraints:
            if isinstance(constraint, XBorder):
                if constraint.is_horizontal:
                    x_constraints[0].add(constraint)
                else:
                    x_constraints[1].add(constraint)
            elif isinstance(constraint, VBorder):
                if constraint.is_horizontal:
                    v_constraints[0].add(constraint)
                else:
                    v_constraints[1].add(constraint)
        return x_constraints, v_constraints

        
    @property
    def solution_count(self) -> int:
        return self._solution_count

    def check_cell(self, i, j, val) -> bool:
        assert self.__correct_solution is not None
        return self.__correct_solution[i][j] == val

    def print_cell(self, cell:Coords):
        # HORIZONTAL ANNOTATIONS
        if cell in self.v_borders[0]:
            end = " v "
        elif cell in self.x_borders[0]:
            end = " x "
        else:
            end = "   "
        # VERTICAL ANNOTATIONS:
        # Add single underline (v) or double underline (x) between applicable vertical pairs
        if cell in self.v_borders[1]:
            u1,u2 = "\033[4m", "\033[0m"
        elif cell in self.x_borders[1]:
            u1,u2 = "\033[21m", "\033[24m"
        else:
            u1,u2 = "",""
        # print cell with highlights
        val = self.value(self.grid.cell(*cell))
        print(f"{u1}{val}{u2}{end}", end="")

    
    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )
        self._solution_count += 1

        # solution is correct until a mismatch found
        if self.__correct_solution:
            correct = True
        
        for i, row in enumerate(self.grid):
            # Add 'v' or 'x' between applicable horizontal pairs
            for j, cell in enumerate(row):
                self.print_cell(cell)
                if self.__correct_solution:
                    correct = correct and self.check_cell(i, j, self.value(cell))

            print()
        if self.__correct_solution and correct:
            print("SOLUTION CORRECT!")
        print()



def SecretWindmill(v_pairs:list[tuple[Coords, Coords]]
                   , x_pairs:list[tuple[Coords, Coords]]
                   , nonconsecutive_pairs:list[tuple[Coords, Coords]]
                   , *
                   , one_indexed:bool):

    def sort_and_offset(*pairs:tuple[Coords,Coords]):
        offset:int = 1 if one_indexed else 0
        return [sort_cells( (r1-offset, c1-offset)
                          , (r2-offset, c2-offset)  ) 
                for (r1,c1), (r2,c2) in pairs]

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
    
    v_pairs = sort_and_offset(*v_pairs)
    x_pairs = sort_and_offset(*x_pairs)
    nonconsecutive_pairs = sort_and_offset(*nonconsecutive_pairs)
    
    problem = SudokuProblem()

    sudoku_constraint = SudokuConstraint

    v_constraints:list[VBorder] = [VBorder(*pair) for pair in v_pairs]
    x_constraints:list[XBorder] = [XBorder(*pair) for pair in x_pairs]
    
    xv_pairs:list[tuple[Coords,Coords]] = v_pairs + x_pairs
    negative_v_constraints:list[NegativeVBorder] = []
    negative_x_constraints:list[NegativeXBorder] = []
    for (cell1, cell2) in problem.grid.get_all_adjacent_pairs():
        pair:tuple[Coords,Coords] = (problem.grid.index(cell1), problem.grid.index(cell2))
        if pair not in xv_pairs:
            negative_v_constraints.append(NegativeVBorder(*pair))
            negative_x_constraints.append(NegativeXBorder(*pair))

    nonconsecutive_constraints:list[Nonconsecutive] = [Nonconsecutive(*pair) for pair in nonconsecutive_pairs]

    constraints_list:Sequence[Constraint] = [sudoku_constraint] + v_constraints + x_constraints + negative_v_constraints + negative_x_constraints + nonconsecutive_constraints
    Constraint.apply_constraints(problem.model, problem.grid, *constraints_list)

    solver = CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.solve(problem.model
                 , solution_callback=XVSolutionPrinter( problem
                                                      , correct_solution=SOLUTION
                                                      )
    )



def main():
    nonconsecutive_pairs = list(combinations( [ (1,8)
                                              , (1,9)
                                              , (2,8)
                                              , (2,9)
                                            ]
                                            , 2)
    )
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
    SecretWindmill(v_pairs=v_pairs, x_pairs=x_pairs, nonconsecutive_pairs=nonconsecutive_pairs, one_indexed=True)
    
if __name__=="__main__":
    main()