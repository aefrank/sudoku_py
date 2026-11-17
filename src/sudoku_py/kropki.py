
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import itertools as it
import functools as ft
from time import time
from typing import Optional, overload

from ortools.sat.python.cp_model import CpModel, CpSolver, CpSolverSolutionCallback, CpSolverStatus, IntVar

from sudoku_py.common import AdjacentCellPair, Coords, sort_cells, verify_adjacency
from sudoku_py.sudoku import BorderConstraint, Consecutive, Constraint, SudokuGrid, SudokuProblem, VBorder, XBorder

class WhiteKropki(BorderConstraint, Consecutive):
    pass

class BlackKropki(BorderConstraint):
    def apply(self, model: CpModel, grid: SudokuGrid[IntVar]) -> None:
        cell1, cell2 = grid.cell(*self.cells[0]), grid.cell(*self.cells[1])
        # boolean switch handles "(cell1 == 2*cell2) OR (cell2 == 2*cell1)"
        cell2_is_twice_cell1:IntVar = model.new_bool_var(name=f"{cell2.name}==2 * `{cell1.name}`")
        model.add(cell2 == 2 * cell1).only_enforce_if(cell2_is_twice_cell1)
        model.add(cell1 == 2 * cell2).only_enforce_if(~cell2_is_twice_cell1)



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



def square_dotted_ring():
    '''
    https://sudokupad.app/jnyo2wg0iq
    '''
    SOLUTION = [
          [7,8,4,3,9,1,2,6,5]
        , [6,5,1,2,8,7,9,3,4]
        , [9,2,3,6,5,4,1,7,8]
        , [5,9,6,1,2,3,4,8,7]
        , [4,1,7,9,6,8,5,2,3]
        , [2,3,8,7,4,5,6,9,1]
        , [1,4,2,8,7,6,3,5,9]
        , [3,7,9,5,1,2,8,4,6]
        , [8,6,5,4,3,9,7,1,2]
    ]

    constraint_data:dict[type, list[tuple[Coords, Coords]]] = {
        WhiteKropki : [ 
              ((1,1), (1,2))
            , ((1,6), (1,7))
            , ((1,9), (2,9))
            , ((2,1), (2,2))
            , ((3,4), (3,5))
            , ((3,5), (3,6))
            , ((3,8), (4,8))
            , ((3,9), (4,9))
            , ((4,1), (5,1))
            , ((4,3), (5,3))
            , ((5,3), (6,3))
            , ((4,7), (5,7))
            , ((5,7), (6,7))
            , ((6,1), (7,1))
            , ((6,2), (7,2))
            , ((7,4), (7,5))
            , ((7,5), (7,6))
            , ((8,2), (9,2))
            , ((8,4), (9,4))
            ]
        , BlackKropki : [  
              ((3,3), (3,4))
            , ((3,3), (4,3))
            , ((7,6), (7,7))
            , ((6,7), (7,7))
            , ((9,8), (9,9))
            ]
        , XBorder : [  
              ((4,4), (5,4))
            , ((4,9), (5,9))
            , ((6,3), (7,3))
            , ((7,3), (7,4))
            , ((8,8), (8,9))
            ]
        , VBorder : [  
              ((3,6), (3,7))
            , ((3,7), (4,7))
            , ((5,1), (5,2))
        ]
    }


    problem = MyProblemSetup(
          one_indexed=True
        , constraint_data=constraint_data
        , correct_solution=SOLUTION
    )

    problem.solve(CpSolver())

if __name__=="__main__":
    square_dotted_ring()


    
