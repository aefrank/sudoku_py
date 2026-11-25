from collections.abc import Callable, Iterable, Sequence
from time import time
from typing import Any, Optional, overload
import functools as ft
import itertools as it

from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback, CpSolverStatus, IntVar

from sudoku_py.constraint import BorderConstraint, Constraint
from sudoku_py.core import Coords, partition, sort_cells, is_Coords
from sudoku_py.problem import SudokuProblem

def concatenate_constraint_lists(iterable_of_lists:Iterable[Iterable[Constraint]]) -> list[Constraint]:
    return [elem for elem in it.chain(*iterable_of_lists)]

@overload
def remove_offset(coords:Coords, offset=1) -> Coords: ...
@overload
def remove_offset(coords:Iterable[Coords], offset=1) -> list[Coords]: ...
def remove_offset(coords:Coords|Iterable[Coords], offset=1) -> Coords|list[Coords]:
    """Subtract `offset` from each coordinate of each Coords.
    """
    if is_Coords(coords):
            return (coords[0]-offset, coords[1]-offset)
    else:
        return [(x-offset, y-offset) for x,y in coords]

        
@overload
def sort_and_offset(coords:Iterable[Coords], *, one_indexed:bool) -> tuple[Coords, ...]: ...
@overload
def sort_and_offset(*coord_group_lists:Iterable[Coords], one_indexed:bool) -> list[tuple[Coords, ...]]: ...
def sort_and_offset(coords:Iterable[Coords], *more_coords:Iterable[Coords], one_indexed:bool) -> tuple[Coords, ...]|list[tuple[Coords, ...]]:
    offset:int = 1 if one_indexed else 0
    if len(more_coords)==0:
        return sort_cells(*[(r-offset, c-offset) for (r,c) in coords])
    else:
        return [ 
            sort_cells( *[(r-offset, c-offset) for (r,c) in coords_group]) 
            for coords_group in it.chain([coords], more_coords)
        ]


def partition_horizontal_vertical(border_constraints:Iterable[BorderConstraint]):
        horizontal, vertical = partition(border_constraints, lambda x: x.is_horizontal) # pyright: ignore[reportAttributeAccessIssue]
        return (
                set(sorted(cons.cells)[0] for cons in horizontal)
            , set(sorted(cons.cells)[0] for cons in vertical)
            )



class MyProblemSetup(SudokuProblem):
    one_indexed:bool
    correct_solution:Optional[list[list[int]]]
    solution_printer:Optional[CpSolverSolutionCallback]
    constraints_applied:bool = False

    def __init__( self
                , *
                , one_indexed:bool
                , constraints: Sequence[Constraint]
                , sudoku_size:int=9
                , sudoku_box_dims:tuple[int,int]=(3,3)
                , correct_solution:Optional[list[list[int]]]=None
                ) -> None:
        self.one_indexed = one_indexed
        self.correct_solution = correct_solution
        super().__init__(
              size=sudoku_size
            , box_dims=sudoku_box_dims
            , constraints=constraints
            , one_indexed_cell_names=self.one_indexed
        )

    def solve(self, solver:CpSolver=CpSolver(), *, solution_printer:Optional[CpSolverSolutionCallback]=None, enumerate_all_solutions:bool=True, print=True) -> tuple[CpSolverStatus, CpSolver]:
        self.apply_constraints()
        if print and solution_printer is None:
                solution_printer = MySolutionPrinter(self, self.correct_solution)
        solver.parameters.enumerate_all_solutions = enumerate_all_solutions
        return solver.solve(self.model, solution_callback=solution_printer), solver

    def apply_constraints(self):
        if not self.constraints_applied:
            super().apply_constraints()

    



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

    def print_from_coords(self, coords:Coords):
        self.print_from_var(self.grid.cell(*coords))

    def print_from_var(self, var:IntVar):
        print(self.value(var), end="  ")

    def print_target(self, var:IntVar, coords:Coords):
        return self.print_from_var(var)

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
            for j, cell in enumerate(row):
                self.print_target(cell, (i,j))
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



