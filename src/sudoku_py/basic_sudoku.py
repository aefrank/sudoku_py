import functools as ft
from time import time

from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback
from ortools.sat.python.cp_model_helper import IntVar, CpSolverStatus

from sudoku_py.sudoku import Given, Coords, SudokuProblem


class SudokuSolutionPrinter(CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, grid: list[list[IntVar]]):
        CpSolverSolutionCallback.__init__(self)
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




def example1() -> tuple[CpSolver, CpSolverStatus]:
    problem = SudokuProblem(6, (2,3))
    givens: list[tuple[Coords, int]] = [
              ((1,4),1), ((1,6),6)
            , ((2,1),6), ((2,3),4)
            , ((3,1),1), ((3,3),2)
            , ((4,4),5), ((4,6),1)
            , ((5,4),6), ((5,6),3)
            , ((6,1),5), ((6,3),6)
        ]
    givens = [((r-1,c-1),v) for (r,c),v in givens]
    given_constraints:list[Given] = [Given(cell, val) for cell, val in givens]
    problem.add_constraints(*given_constraints)
    problem.apply_constraints()

    solver = CpSolver()
    solution_printer = SudokuSolutionPrinter(problem.grid.items)
    status = solver.solve(problem.model, solution_callback=solution_printer)
    print("\nStatistics")
    print(f"  conflicts      : {solver.num_conflicts}")
    print(f"  branches       : {solver.num_branches}")
    print(f"  wall time      : {solver.wall_time} s")
    if hasattr(solution_printer, "solution_count"):
        print(f"  solutions found: {solution_printer.solution_count}") # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
    return solver, status


def main():
    example1()




if __name__ == '__main__':
    main()