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

from ortools.sat.python.cp_model import CpSolver, CpSolverSolutionCallback
from ortools.sat.python.cp_model_helper import IntVar

from sudoku_py.sudoku import SudokuModel, SudokuSolutionPrinter, CellVar

Coords = tuple[int,int]
CoordsPair = tuple[Coords,Coords]
VarPair = tuple[IntVar,IntVar] 


class XVSudokuModel(SudokuModel):

    # INTERNAL
    def __init__(self, size: int = 9, box_dims: tuple[int, int] = (3, 3)):
        super().__init__(size, box_dims)
        self.V_borders:tuple[set[CellVar],set[CellVar]] = (set(),set())
        self.X_borders:tuple[set[CellVar],set[CellVar]] = (set(),set())


    def add_V_border(self, cell1:CellVar, cell2:CellVar):
        if self.grid.is_horizontal_neighbor(cell1, cell2):
            self.V_borders[0].add(self.sort_cells(cell1,cell2)[0])
        elif self.grid.is_vertical_neighbor(cell1, cell2):
            self.V_borders[1].add(self.sort_cells(cell1,cell2)[0])    

    def add_X_border(self, cell1:CellVar, cell2:CellVar):
        if self.grid.is_horizontal_neighbor(cell1, cell2):
            self.X_borders[0].add(self.sort_cells(cell1,cell2)[0])
        elif self.grid.is_vertical_neighbor(cell1, cell2):
            self.X_borders[1].add(self.sort_cells(cell1,cell2)[0])     
    
    # INTERFACE

    
    def add_V(self, cell1:CellVar, cell2:CellVar):
        self.add_V_border(cell1,cell2)
        self.add(cell1 + cell2 == 5)
    
    def add_negative_V(self, cell1:CellVar, cell2:CellVar):
        self.add(cell1 + cell2 != 5)
    
    def add_X(self, cell1:CellVar, cell2:CellVar):
        self.add_X_border(cell1,cell2)
        self.add(cell1 + cell2 == 10)
        
    def add_negative_X(self, cell1:CellVar, cell2:CellVar):
        self.add(cell1 + cell2 != 10)

    def infer_all_negative_XV_constraints(self):
        '''Enforce that any adjacent pair that does not have either an X or V constraint
        must instead have a negative X and V constraint.
        '''
        adjacent_pairs = self.grid.get_all_adjacent_pairs()
        for cell1, cell2 in adjacent_pairs:
            if cell1 not in self.V_borders and cell1 not in self.X_borders:
                self.add_negative_V(cell1, cell2)
                self.add_negative_X(cell1, cell2)

    


class WindmillModel(XVSudokuModel):

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), **kwargs):
        super().__init__(size, box_dims, **kwargs)

    def add_XV_and_infer_negative_XV(self
                           , V_pairs:list[tuple[CellVar,CellVar]]
                           , X_pairs:list[tuple[CellVar,CellVar]]
                           ):
        V_pairs = [self.sort_cells(*pair) for pair in V_pairs]
        X_pairs = [self.sort_cells(*pair) for pair in X_pairs]
        adjacent_pairs = self.grid.get_all_adjacent_pairs()
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
                           , V_pairs:list[tuple[CellVar,CellVar]]
                           , X_pairs:list[tuple[CellVar,CellVar]]
                           , infer_negative_constraints:bool=True):
        if infer_negative_constraints:
            return self.add_XV_and_infer_negative_XV(V_pairs, X_pairs)
        for pair in V_pairs:
            self.add_V(*pair)
        for pair in X_pairs:
            self.add_X(*pair)

    def add_circle_constraints(self, circle_cells:list[CellVar]):
        # no two cells on yellow circle are consecutive
        for cell1, cell2 in it.combinations(circle_cells,2):
            self.add_nonconsecutive(cell1, cell2)


class XVSudokuSolutionPrinter(CpSolverSolutionCallback):

    def __init__(self, model:XVSudokuModel, correct_solution:list[list[int]]|None=None):
        CpSolverSolutionCallback.__init__(self)
        self.model = model
        self.V = self.model.V_borders
        self.X = self.model.X_borders
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

        # solution is correct until a mismatch found
        if self.__correct_solution:
            correct = True
        
        for i, row in enumerate(self.model.grid):
            # Add 'v' or 'x' between applicable horizontal pairs
            for j, cell in enumerate(row):
                # HORIZONTAL ANNOTATIONS
                if cell in self.V[0]:
                    end = " v "
                elif cell in self.X[0]:
                    end = " x "
                else:
                    end = "   "
                # VERTICAL ANNOTATIONS:
                # Add single underline (v) or double underline (x) between applicable vertical pairs
                if cell in self.V[1]:
                    u1,u2 = "\033[4m", "\033[0m"
                elif cell in self.X[1]:
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
        

def to_cell_var(model:SudokuModel, coords:tuple[int,int], one_indexed=True) -> CellVar:
    return model.grid.cell(*[i-int(one_indexed) for i in coords])

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

    model = WindmillModel()
    solver = CpSolver()

#     # no two cells on yellow circle are consecutive
    circle_cells = [(1,8),(1,9),(2,8),(2,9)]
    circle_cell_vars = [to_cell_var(model, coords) for coords in circle_cells]
    model.add_circle_constraints(circle_cell_vars)

    v_pairs = [
          ((2,2),(2,3))
        , ((2,8),(3,8))
        , ((7,2),(8,2))
        , ((8,7),(8,8))
    ]
    v_var_pairs = [(to_cell_var(model, coords1), to_cell_var(model, coords2)) for coords1, coords2 in v_pairs]
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
    x_var_pairs = [(to_cell_var(model, coords1), to_cell_var(model, coords2)) for coords1, coords2 in x_pairs]
    model.add_XV_constraints(v_var_pairs, x_var_pairs, True)
    solver.parameters.enumerate_all_solutions = True
    status = solver.solve(model, 
            solution_callback=XVSudokuSolutionPrinter(model,            correct_solution=SOLUTION)
    )
    return solver, status

        
if __name__ == "__main__":
    secret_windmill()



