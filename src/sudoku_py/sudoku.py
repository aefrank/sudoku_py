
import functools as ft
import itertools as it
from time import time
from typing import Any, Callable

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model_helper import IntVar, CpSolverStatus


class SudokuProblem:
    """
    NOTE: All methods of this class are ZERO-INDEXED!
    """

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3)):
        self.grid_size = size
        self.box_dims = box_dims
        rows_of_boxes = self.grid_size/self.box_dims[0]
        cols_of_boxes = self.grid_size/self.box_dims[1]
        assert all(n.is_integer() for n in (rows_of_boxes, cols_of_boxes))
        self.rows_of_boxes, self.cols_of_boxes = int(rows_of_boxes), int(cols_of_boxes)
        
        self._model_setup()

    def _model_setup(self):
        self.model = cp_model.CpModel()
        self.grid = self._create_grid()
        self.__add_sudoku_constraints()

    def _create_grid(self):
        return [[self.model.new_int_var(1, self.grid_size, f"Cell[{r},{c}]") 
                        for c in range(self.grid_size)] for r in range(self.grid_size)]

    def __add_sudoku_constraints(self):
        for r in range(self.grid_size):
            self.model.add_all_different(self.row(r))
        for c in range(self.grid_size):
            self.model.add_all_different(self.col(c))
        for b in range(self.rows_of_boxes*self.cols_of_boxes):
            self.model.add_all_different(ft.reduce(lambda x,y: x+y, self.box(b)))

    def row(self, row:int) -> list[IntVar]:
        """Return list of the cells in Row <row>.
        """
        return self.grid[row]

    def col(self, col:int) -> list[IntVar]:
        """Return list of the cells in Column <col>.
        """
        return [self.grid[r][col] for r in range(self.grid_size)]

    def box(self, box:int) -> list[list[IntVar]]:
        """Return nested list of the cells in Box <box> in shape <self.box_dims>.
        """
        row = (box // self.cols_of_boxes) * self.box_dims[0]
        col = (box % self.cols_of_boxes) * self.box_dims[1]
        return [[self.grid[row+i][col+j] for j in range(self.box_dims[1])] for i in range(self.box_dims[0])]

    def cell(self, row:int, col:int) -> IntVar:
        return self.grid[row][col]

    def get_all_horizontal_pairs(self) -> list[tuple[IntVar,IntVar]]:
            return [(self.cell(r,c), self.cell(r,c+1)) for r,c in it.product(range(self.grid_size), range(self.grid_size-1))]
    def get_all_vertical_pairs(self) -> list[tuple[IntVar,IntVar]]:
        return [(self.cell(r,c), self.cell(r+1,c)) for r,c in it.product(range(self.grid_size-1), range(self.grid_size))]

    def get_all_adjacent_pairs(self) -> list[tuple[IntVar,IntVar]]:
        return self.get_all_horizontal_pairs() + self.get_all_vertical_pairs()

    def add_given(self, row:int, col:int, val:int):
            self.model.add(self.grid[row][col]==val)
    
    def add_givens(self, givens:list[tuple[int,int,int]]):
        for row,col,val in givens:
            self.model.add(self.grid[row][col]==val)


class OneIndexedSudokuProblem(SudokuProblem):

    def _create_grid(self):
        return [[self.model.new_int_var(1, self.grid_size, f"Cell[{r+1},{c+1}]") 
                        for c in range(self.grid_size)] for r in range(self.grid_size)]

    def _add_sudoku_constraints(self):
        for r in range(self.grid_size):
            self.model.add_all_different(super().row(r))
        for c in range(self.grid_size):
            self.model.add_all_different(super().col(c))
        for b in range(self.rows_of_boxes*self.cols_of_boxes):
            self.model.add_all_different(ft.reduce(lambda x,y: x+y, super().box(b)))
    
    def row(self, row:int) -> list[IntVar]:
        """Return list of the cells in Row <row>.
        """
        return super().row(row-1)

    def col(self, col:int) -> list[IntVar]:
        """Return list of the cells in Column <col>.
        """
        return super().col(col-1)

    def box(self, box:int) -> list[list[IntVar]]:
        """Return nested list of the cells in Box <box> in shape <self.box_dims>.
        """
        return super().box(box-1)

    def cell(self, row:int, col:int) -> IntVar:
        return super().cell(row-1, col-1)

    def add_given(self, row:int, col:int, val:int):
            return super().add_given(row-1, col-1, val)
            
    def add_givens(self, givens:list[tuple[int,int,int]]):
        return super().add_givens([(r-1, c-1, v) for r,c,v in givens])



class SudokuSolver:

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), *, one_indexed:bool=True):
        if one_indexed:
            self.problem = OneIndexedSudokuProblem(size, box_dims)
        else:
            self.problem = SudokuProblem(size, box_dims)

        self.solver = cp_model.CpSolver()
        

    def add_given(self, row:int, col:int, val:int):
            return self.problem.add_given(row, col, val)
            
    def add_givens(self, givens:list[tuple[int,int,int]]):
        return self.problem.add_givens(givens)

        
    def solve(self, solution_printer:cp_model.CpSolverSolutionCallback|None=None, print_stats:bool=True) -> CpSolverStatus:
        status = self.solver.solve(self.problem.model, solution_printer)
        if print_stats:
            print("\nStatistics")
            print(f"  conflicts      : {self.solver.num_conflicts}")
            print(f"  branches       : {self.solver.num_branches}")
            print(f"  wall time      : {self.solver.wall_time} s")
            if isinstance(solution_printer, SudokuSolutionPrinter):
                print(f"  solutions found: {solution_printer.solution_count}")
        return status

    


class SudokuSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, grid: list[list[IntVar]]):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._grid = grid
        self._solution_count = 0
        self._start_time = time()

    @property
    def solution_count(self) -> int:
        return self._solution_count

    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )
        self._solution_count += 1

        for row in self._grid:
            for cell in row:
                print(self.value(cell), end="  ")
            print()
        print()

def example1():
    S = SudokuSolver(6, (2,3), one_indexed=True)
    S.add_givens([
              (1,4,1), (1,6,6)
            , (2,1,6), (2,3,4)
            , (3,1,1), (3,3,2)
            , (4,4,5), (4,6,1)
            , (5,4,6), (5,6,3)
            , (6,1,5), (6,3,6)
        ])
    return S.solve(solution_printer=SudokuSolutionPrinter(S.problem.grid))




def main():

    example1()




if __name__ == '__main__':
    main()