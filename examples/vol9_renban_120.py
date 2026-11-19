"""
Vol.11 Renban #120 by Adrian Klausen
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000TZ0
"""

from functools import reduce
from typing import Any, Iterable

from ortools.sat.python.cp_model import CpModel, CpSolver, IntVar

from my_utils import MyProblemSetup, MySolutionPrinter, concatenate_constraint_lists, remove_offset
from sudoku_py.constraint import Constraint, Given, MultiCellConstraint
from sudoku_py.core import Coords, partition, partition_out_types
from sudoku_py.grid import SudokuGrid
from sudoku_py.problem import SudokuProblem

class Renban(MultiCellConstraint):
    name:str
    __INSTANCE_COUNT:int=0
    _cells:frozenset[Coords]

    @property
    def cells(self) -> frozenset[Coords]:
        return self._cells

    def __init__(self, cells: Iterable[Coords]):
        self._cells = frozenset(cells)
        __class__.__INSTANCE_COUNT += 1 # increment program-wide instance count
        self.name = f"{__class__.__name__}{self.__INSTANCE_COUNT}"

    def apply(self, model: CpModel, grid: SudokuGrid) -> None:
        """Add constraints to model so that cells on the line form a consecutive set.

        This is done by enforcing that all cells on the line are different, and that the maximum and minimum values on the line differ by exactly `len(self.cells)-1`.
        """
        # values must form consecutive set
        cell_vars:set[IntVar] = set(grid.cell(*coords) for coords in self.cells)
        # no repeat values
        model.add_all_different(cell_vars)
        value_bounds:tuple[int,int] = (
              min(cell.domain.min() for cell in cell_vars)
            , max(cell.domain.max() for cell in cell_vars)
        )
        # Define new variables to represent smallest and largest value on renban
        min_cell = model.new_int_var(*value_bounds, f"min({self.name})")
        model.add_min_equality(min_cell, cell_vars)
        model.add_max_equality(min_cell+len(cell_vars)-1, cell_vars)

    @property
    def _identifying_attributes(self) -> tuple[frozenset[Coords]]:
        return super()._identifying_attributes
    
    



def problem_setup():
    SOLUTION = [ 
          [5,7,8,3,2,1,9,6,4]
        , [1,6,4,7,9,8,3,2,5]
        , [2,3,9,6,5,4,7,1,8]
        , [4,1,7,8,3,6,5,9,2]
        , [8,5,2,1,4,9,6,3,7]
        , [6,9,3,5,7,2,4,8,1]
        , [7,2,6,4,8,3,1,5,9]
        , [9,4,1,2,6,5,8,7,3]
        , [3,8,5,9,1,7,2,4,6]
    ]

    givens:list[tuple[Coords, int]] = [
          ((1,2), 7)
        , ((1,5), 2)
        , ((1,8), 6)
        , ((2,1), 1)
        , ((2,9), 5)
        , ((5,1), 8)
        , ((5,9), 7)
        , ((8,1), 9)
        , ((8,9), 3)
        , ((9,2), 8)
        , ((9,5), 1)
        , ((9,8), 4)
    ]	

    renban_lines:list[list[Coords]] = [
          [(1,1), (2,2), (2,3), (3,2)]
        , [(1,9), (2,7), (2,8), (3,8)]
        , [(3,3), (3,4), (4,3), (4,4)]
        , [(3,5), (4,5), (5,3), (5,4), (5,5), (5,6), (5,7), (6,5), (7,5)]
        , [(3,6), (3,7), (4,6), (4,7)]
        , [(4,1), (5,2), (6,1)]
        , [(4,9), (5,8), (6,9)]
        , [(6,3), (6,4), (7,3), (7,4)]
        , [(6,6), (6,7), (7,6), (7,7)]
        , [(7,2), (8,2), (8,3), (9,1)]
        , [(7,8), (8,7), (8,8), (9,9)]
    ]


    constraint_list:list[Constraint] = concatenate_constraint_lists((
          [Given(remove_offset(cell, 1), value) for cell, value in givens]
        , [Renban(remove_offset(line, 1)) for line in renban_lines]
        ))

    return MyProblemSetup(
          one_indexed=True
        , constraints=constraint_list
        , correct_solution=SOLUTION
    )


class _Printer(MySolutionPrinter):
    _givens_cells:set[Coords]
    _renban_cells:set[Coords]
    def __init__(self, problem: MyProblemSetup):
        super().__init__(problem, problem.correct_solution)
        givens, renban = (set(out) for out in partition_out_types(problem.constraints, *[Given, Renban]))
        self._given_cells = set(g.cell for g in givens)
        self._renban_cells = set()
        for r in renban:
            self._renban_cells.update(r.cells)


    def print_target(self, var: IntVar, coords: Coords):
        # prefix:str = "\033["
        format:list[str] = []
        if coords in self._given_cells:
            format += ["1"]
        if coords in self._renban_cells:
            format += ["35"]
        prefix:str = "\033[" + ";".join(format) + "m"
        suffix:str = "\033[0m"
        print(f"{prefix}{self.value(var)}{suffix}", end="  ")


if __name__=="__main__":
    problem = problem_setup()
    
    solution_printer = _Printer(problem)
    problem.apply_constraints()
    problem.solve(CpSolver(), solution_printer=solution_printer)

