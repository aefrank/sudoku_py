from time import time
from typing import Optional, overload
import functools as ft
import itertools as it

from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback, CpSolverStatus, IntVar

from sudoku_py.core import Coords, sort_cells
from sudoku_py.problem import SudokuProblem


class MySolutionPrinter(CpSolverSolutionCallback):
    
    def __init__(self
                 , problem: SudokuProblem
                 , correct_solution:list[list[int]]|None=None
                ):
        CpSolverSolutionCallback.__init__(self)
        self.model = problem.model
        self.grid = problem.grid
        self.__correct_solution = correct_solution
        
        self._solution_count = 0
        self._start_time = time()

    @property
    def solution_count(self) -> int:
        return self._solution_count

    def check_cell(self, i, j, val) -> bool:
        """Checks cell's value against correct solution.
        """
        assert self.__correct_solution is not None
        return self.__correct_solution[i][j] == val

    def print_cell(self, cell:IntVar):
        print(self.value(cell), end="  ")

    def print_caption(self):
        current_time = time()
        print(
            f"Solution {self._solution_count}, "
            f"time = {current_time - self._start_time} s"
        )

    def print_solution(self):
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
        self.print_caption()
        if self.__correct_solution and correct:
            print("SOLUTION CORRECT!")
        print()

    def on_solution_callback(self):
        """Prints grid and stats to terminal for each found solution.
        """
        self._solution_count += 1
        self.print_solution()

        




class MyProblemSetup(SudokuProblem):
    one_indexed:bool
    correct_solution:Optional[list[list[int]]]
    solution_printer:Optional[CpSolverSolutionCallback]
    constraints_applied:bool = False

    def __init__( self
                , *
                , one_indexed:bool
                , constraint_data: dict[type, list[tuple[Coords,...]]] = {}
                , sudoku_size:int=9
                , sudoku_box_dims:tuple[int,int]=(3,3)
                , correct_solution:Optional[list[list[int]]]=None
                , solution_printer:Optional[CpSolverSolutionCallback]=None
                ) -> None:
        self.one_indexed = one_indexed
        self.correct_solution = correct_solution
        self.solution_printer = solution_printer 

        constraint_data = {
            constructor : MyProblemSetup.sort_and_offset(*all_pairs, one_indexed=self.one_indexed)
            for constructor, all_pairs in constraint_data.items()
        }
        super().__init__(
              size=sudoku_size
            , box_dims=sudoku_box_dims
            , constraints=ft.reduce(lambda x,y: x+y, [[Constructor(*cell_group) for cell_group in all_constrained_cells] for Constructor, all_constrained_cells in constraint_data.items()])
            , one_indexed_cell_names=self.one_indexed
        )

    @overload
    @staticmethod
    def sort_and_offset(coords:tuple[Coords,...], *, one_indexed:bool) -> tuple[Coords, ...]: ...
    @overload
    @staticmethod
    def sort_and_offset(*coord_group_lists:tuple[Coords, ...]      , one_indexed:bool) -> list[tuple[Coords, ...]]: ...
    @staticmethod
    def sort_and_offset(coords:tuple[Coords, ...], *more_coords:tuple[Coords, ...], one_indexed:bool) -> tuple[Coords, ...]|list[tuple[Coords, ...]]:
        offset:int = 1 if one_indexed else 0
        if len(more_coords)==0:
            return sort_cells(*[(r-offset, c-offset) for (r,c) in coords])
        else:
            return [ 
                sort_cells( *[(r-offset, c-offset) for (r,c) in coords_group]) 
                for coords_group in it.chain([coords], more_coords)
            ]

    def solve(self, solver:CpSolver, *, enumerate_all_solutions:bool=True, print=True) -> tuple[CpSolverStatus, CpSolver]:
        self.apply_constraints()
        solution_printer:Optional[CpSolverSolutionCallback] = None
        if print:
            if self.solution_printer is not None:
                solution_printer = self.solution_printer
            else:
                solution_printer = MySolutionPrinter(self, self.correct_solution)
        solver.parameters.enumerate_all_solutions = enumerate_all_solutions
        return solver.solve(self.model, solution_callback=solution_printer), solver

    def apply_constraints(self):
        if not self.constraints_applied:
            super().apply_constraints()

