
import functools as ft
import itertools as it
from time import time

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model_helper import IntVar


class SudokuSolver:

    @staticmethod
    def make_offset_handler(offset_args:list[int]): # note: offset_args = [0] implies first argument after 'self'
            def offset_handler(func):
                def wrapper(self, *arg, one_indexed:bool|None=None, **kw):
                    if one_indexed is None:
                        one_indexed = self.one_indexed
                    if one_indexed:
                        arglist = [a-1 if i in offset_args else a for i,a in enumerate(arg)]
                        return func(self, *arglist, **kw)
                    else:
                        return func(self, *arg, **kw)
                return wrapper
            return offset_handler

    def __init__(self, grid_size:int=9, box_size:int|tuple[int,int]=(3,3), one_indexed_labels:bool=True):
        self.N = grid_size
        self.size = (grid_size, grid_size)
        match box_size:
            case int():
                self.box_size = (box_size, box_size)
            case tuple():
                self.box_size = box_size
            case _:
                print("Unknown type for argument 'box_size'.")
        num_boxes = self.N**2/(self.box_size[0]*self.box_size[1])
        rows_of_boxes = self.size[0]/self.box_size[0]
        cols_of_boxes = self.size[1]/self.box_size[1]
        assert all(n.is_integer() for n in (num_boxes, rows_of_boxes, cols_of_boxes))
        self.num_boxes, self.rows_of_boxes, self.cols_of_boxes = (int(n) for n in (num_boxes, rows_of_boxes, cols_of_boxes))

        self.one_indexed = one_indexed_labels
        
        self.model: cp_model.CpModel = cp_model.CpModel()
        self.grid = self._create_grid()
        self._add_sudoku_constraints()


    def _create_grid(self):
        return [[self.model.new_int_var(1, self.N, 
                    f"Cell[{r+int(self.one_indexed)},{c+int(self.one_indexed)}]") for c in range(self.N)] for r in range(self.N)]


    @make_offset_handler([0])
    def row(self, r:int) -> list[IntVar]:
        return self.grid[r]

    @make_offset_handler([0])
    def col(self, c:int) -> list[IntVar]:
        return [self.grid[r][c] for r in range(self.N)]

    @make_offset_handler([0,1])
    def cell(self, r:int, c:int) -> IntVar:
        return self.grid[r][c]

    @make_offset_handler([0,1])
    def box(self, br:int, bc:int=-2, flatten=False) -> list[IntVar]|list[list[IntVar]]:
        # print(br,bc,self.num_boxes,self.rows_of_boxes, self.cols_of_boxes)
        if bc < 0:
            bc = br % self.cols_of_boxes
            br = br // self.cols_of_boxes
        B = [ [self.grid[br*self.box_size[0]+i][bc*self.box_size[1]+j] for j in range(self.box_size[1])] 
            for i in range(self.box_size[0]) ]
        return ft.reduce(lambda x,y: x+y, B) if flatten else B


    ########## GENERAL SUDOKU CONSTRAINTS ##############
    def _add_sudoku_constraints(self):
        # no row repeats
        for r in range(self.N):
            self.model.add_all_different(self.grid[r])
        # no column repeats
        for c in range(self.N):
            self.model.add_all_different(self.grid[r][c] for r in range(self.N))

        # no repeats in boxes
        for r in range(0,self.N,self.box_size[0]):
            for c in range(0,self.N,self.box_size[1]):
                self.model.add_all_different(
                    self.grid[r+i][c+j] 
                    for i,j in 
                    it.product(range(self.box_size[0]), range(self.box_size[1]))
                )


    @make_offset_handler([0,1])
    def _add_given_cell(self, r:int, c:int, val:int):
        self.model.add(self.grid[r][c] == val)

    def add_given_cells(self, *givens:tuple[int,int,int], one_indexed=None):
        for given in givens:
            self._add_given_cell(*given, one_indexed=one_indexed) # pyright: ignore[reportCallIssue]



def check_indexing(S:SudokuSolver):
    # for i in range(S.N):
    #     print(i, S.col(i, one_indexed=False)) # pyright: ignore[reportCallIssue]

    for i in range(S.num_boxes):
        for br in S.box(i, one_indexed=False): # pyright: ignore[reportCallIssue]
            print(br)
        print()


class SudokuSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, grid: list[list[cp_model.IntVar]]):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__grid = grid
        self.__solution_count = 0
        self.__start_time = time()

    @property
    def solution_count(self) -> int:
        return self.__solution_count

    def on_solution_callback(self):
        current_time = time()
        print(
            f"Solution {self.__solution_count}, "
            f"time = {current_time - self.__start_time} s"
        )
        self.__solution_count += 1

        for row in self.__grid:
            for cell in row:
                print(self.value(cell), end="  ")
            print()
        print()

def example1():
    S = SudokuSolver(6, (2,3), one_indexed_labels=True)
    S.add_given_cells(
            (1,4,1), (1,6,6),
            (2,1,6), (2,3,4),
            (3,1,1), (3,3,2),
            (4,4,5), (4,6,1),
            (5,4,6), (5,6,3),
            (6,1,5), (6,3,6)
        )
    return S




def main():

    S = example1()
    
    solver = cp_model.CpSolver()
    solution_printer = SudokuSolutionPrinter(S.grid)
    solver.parameters.enumerate_all_solutions = True
    solver.solve(S.model, solution_printer)

    # Statistics.
    print("\nStatistics")
    print(f"  conflicts      : {solver.num_conflicts}")
    print(f"  branches       : {solver.num_branches}")
    print(f"  wall time      : {solver.wall_time} s")
    print(f"  solutions found: {solution_printer.solution_count}")




if __name__ == '__main__':
    main()