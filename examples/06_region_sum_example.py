"""Shared Spaces (Blue and Pink) by Fenners
https://logic-masters.de/Raetselportal/Raetsel/zeigen.php?id=000MOD
"""

from ortools.sat.python.cp_model import IntVar

from my_utils import MyProblemSetup, MySolutionPrinter, undo_offset
from sudoku_py.constraint import RegionSum, Renban, WhiteKropki
from sudoku_py.core import Coords, partition_out_disjoint_types
from sudoku_py.graph import CellGraph
    

class _Printer(MySolutionPrinter):
    _regionsum_cells:set[Coords]
    _renban_cells:set[Coords]
    _kropki:set[WhiteKropki]

    def __init__(self, problem: MyProblemSetup):
        super().__init__(problem, problem.correct_solution)
        region_sum, renban, self._kropki = (set(out) for out in partition_out_disjoint_types(problem.constraints, *[RegionSum, Renban, WhiteKropki]))
        self._renban_cells = set()
        for r in renban:
            self._renban_cells.update(r.cells)
        self._regionsum_cells = set()
        for rs in region_sum:
            self._regionsum_cells.update(rs.cells)


    def print_target(self, var: IntVar, coords: Coords):
        format:list[str] = []
        end:str = "   "
        white_circle = "\u25CF" # my editor is in dark mode, so filled circle looks white
        if coords in self._regionsum_cells:
            format += ["1"]
        if coords in self._renban_cells:
            format += ["35"]
        if coords == (0,4):
            pass
        for k in self._kropki:
            if k.cells[0]==coords:
                if k.is_horizontal:
                    end = f" {white_circle} "
                else:
                    format += ["4"]
            
        prefix:str = "\033[" + ";".join(format) + "m"
        suffix:str = "\033[0m"
        print(f"{prefix}{self.value(var)}{suffix}", end=end)


    
def shared_spaced_renban_constraints() -> list[Renban]:
    renban_lines:list[list[Coords]] = [
              [ (1,9), (1,8), (2,8), (3,8) ]
            , [ (2,3), (2,2), (3,2) ]
            , [ (2,4), (3,4), (3,5), (3,6), (4,2), (4,3), (5,3), (6,3) ]
            , [ (4,4), (5,4), (5,5), (5,6) ]
            , [ (4,7), (4,8), (4,9) ]
            , [ (5,8), (6,8), (6,9) ]
            , [ (6,4), (6,5), (6,6) ]
            , [ (7,4), (8,4), (9,4) ]
            , [ (8,5), (8,6), (9,6) ]
            , [ (7,8), (8,8) ]
        ]
    renban_constraints:list[Renban] = [Renban(coords) for coords in undo_offset(renban_lines)]
    return renban_constraints

def shared_spaced_regionsum_constraints() -> list[RegionSum]:
    RS1:list[Coords] = [(6,2), (7,2), (8,2)]
    RS2:list[Coords] = [(6,7), (6,8), (7,8), (8,8), (8,7), (8,6), (7,6)]
    RS3:list[list[Coords]] = [
              [(5,4), (4,4), (4,5), (4,6), (4,7), (4,8), (4,9)]
            , [(4,6), (3,6), (3,5), (3,4), (2,4), (2,3), (2,2), (3,2), (4,2), (4,3), (5,3), (6,3), (6,4), (6,5), (6,6), (5,6)]
            , [(6,4), (7,4), (8,4), (9,4), (9,5)]
        ]
    region_sum_constraints:list[RegionSum] = [RegionSum(CellGraph(arg)) for arg in undo_offset((
                    # [],  # for debugging
                      RS1
                    , RS2
                    , RS3
                    ))]
    return region_sum_constraints

def shared_space_whitekropki_constraints() -> list[WhiteKropki]:
    white_kropki_locations:list[tuple[Coords, Coords]] = [
          ((1,5), (2,5))
        , ((1,6), (2,6))
        , ((1,7), (2,7))
        , ((5,1), (5,2))
        , ((6,1), (6,2))
    ]
    white_kropki_constraints:list[WhiteKropki] = [WhiteKropki(*coords) for coords in undo_offset(white_kropki_locations)]
    return white_kropki_constraints






def main():
    SOLUTION:list[list[int]] = [
          [2,3,1,9,6,4,5,8,7]
        , [8,6,7,1,5,3,4,9,2]
        , [4,5,9,2,8,7,1,6,3]
        , [9,4,3,8,2,1,6,7,5]
        , [1,2,5,7,9,6,8,3,4]
        , [7,8,6,3,4,5,9,2,1]
        , [6,7,8,5,1,2,3,4,9]
        , [3,1,4,6,7,9,2,5,8]
        , [5,9,2,4,3,8,7,1,6]
    ]

    kropki_constraints = shared_space_whitekropki_constraints()
    constraints = kropki_constraints + shared_spaced_regionsum_constraints() + shared_spaced_renban_constraints()

    problem = MyProblemSetup(
                      one_indexed=True
                    , constraints=constraints
                    , correct_solution=SOLUTION
                )
    
    
    problem.apply_constraints()
    problem.solve(solution_printer=_Printer(problem))

if __name__=="__main__":
    main()