
from ortools.sat.python.cp_model import CpModel, IntVar

from sudoku_py.constraint import Constraint, SudokuConstraint
from sudoku_py.grid import SudokuGrid


class SudokuProblem:
    """Main class coordinating model, data, and constraint objects for
    a given Sudoku problem.
    """
    model: CpModel
    grid: SudokuGrid
    _constraints:list[Constraint] # TODO: refactor to set

    def __init__(self
                 , size:int=9
                 , box_dims:tuple[int,int]=(3,3)
                 , constraints:list[Constraint]=[]
                 , one_indexed_cell_names:bool=True
                ):
        self.model = CpModel()
        self.grid = self.create_grid(size, box_dims, one_indexed_cell_names)
        if not SudokuConstraint in constraints:
            self._constraints = [SudokuConstraint] + [c for c in constraints]
        else:
            self._constraints = [c for c in constraints]

    def create_grid(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True) -> SudokuGrid[IntVar]:
        os = 1 if one_indexed_cell_names else 0
        grid = [[self.model.new_int_var(1, size, f"Cell[{r+os},{c+os}]") 
                for c in range(size)] 
                for r in range(size)]
        return SudokuGrid.from_list(grid, box_dims)

    @property
    def constraints(self) -> list[Constraint]:
        return self._constraints

    def add_constraint(self, constraint:Constraint):
        self._constraints.append(constraint)

    def add_constraints(self, *constraints:Constraint):
        for constraint in constraints:
            if constraint not in self._constraints:
                self._constraints.append(constraint)

    def apply_constraints(self):
        Constraint.apply_constraints(self.model, self.grid, *self._constraints)

    
        


    



