
from collections.abc import Generator
import functools as ft
from time import time
from typing import Any, Generic, TypeVar

from ortools.sat.python.cp_model import CpModel, CpSolver, CpSolverSolutionCallback
from ortools.sat.python.cp_model_helper import IntVar, CpSolverStatus

CellVar = IntVar
T = TypeVar("T")

class SudokuGrid(Generic[T]):
    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3)):
        self.size = size
        self.box_dims = box_dims
        rows_of_boxes, cols_of_boxes = [self.size/dim for dim in self.box_dims]
        assert all(n.is_integer() for n in (rows_of_boxes, cols_of_boxes))
        self.rows_of_boxes, self.cols_of_boxes = int(rows_of_boxes), int(cols_of_boxes)
        self.items:list[list[T]] = []

    def populate_grid(self, L:list[list[T]]):
        assert (len(L) == self.size)
        for sublist in L:
            assert len(sublist) == self.size
        self.items = L

    @classmethod
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> SudokuGrid[T]:
        sudoku_grid = cls(len(L), box_dims)
        sudoku_grid.populate_grid(L)
        return sudoku_grid

    def row(self, r:int) -> list[T]:
        return self.items[r]

    def col(self, c:int) -> list[T]:
        return [self.items[r][c] for r in range(self.size)]

    def box(self, b:int) -> list[list[T]]:
        row = (b // self.cols_of_boxes) * self.box_dims[0]
        col = (b % self.cols_of_boxes) * self.box_dims[1]
        return [[self.items[row+i][col+j] for j in range(self.box_dims[1])] for i in range(self.box_dims[0])]

    def cell(self, row:int, col:int) -> T:
        return self.items[row][col]

    def index(self, val:T) -> tuple[int,int]:
        for r, row in enumerate(self.items):
            try:
                return r, row.index(val)
            except ValueError:
                continue
        # if you get to the end, cell wasn't anywhere in grid
        raise ValueError(val)

    def rows(self) -> list[list[T]]:
        return self.items

    def cols(self) -> list[list[T]]:
        return [self.__col(i) for i in range(self.size)]

    def boxes(self) -> list[list[list[T]]]:
        return [self.__box(i) for i in range(self.rows_of_boxes*self.cols_of_boxes)]

    def cells(self) -> list[T]:
        return ft.reduce(lambda x,y: x+y, self.__rows())

    def get_row(self, item:T) -> int:
        return self.__index(item)[0]

    def get_col(self, item:T) -> int:
        return self.__index(item)[1]

    def get_box(self, item:T) -> int:
        for i,box in enumerate(self.boxes()):
            if item in ft.reduce(lambda x,y: x+y, box):
                return i
        # if we get to here, item does not exist in grid
        raise ValueError(item)

    def same_row(self, cell1:T, cell2:T) -> bool:
            return self.__get_row(cell1) == self.__get_row(cell2)
    
    def same_col(self, cell1:T, cell2:T) -> bool:
        return self.__get_col(cell1) == self.__get_col(cell2)

    def same_box(self, cell1:T, cell2:T) -> bool:
        return self.__get_box(cell1) == self.__get_box(cell2)

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> Generator[list[T], Any, Any]:
        for item in self.items:
            yield item

    # avoid name-mangling
    __row = row
    __col = col
    __box = box
    __cell = cell
    __rows = rows
    __cols = cols
    __boxes = boxes
    __cells = cells
    __index = index
    __get_row = get_row
    __get_col = get_col
    __get_box = get_box
    __populate_grid = populate_grid


class SudokuGridPlus(SudokuGrid[T]):

    @classmethod
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> SudokuGridPlus[T]: 
        sudoku_grid = cls(len(L), box_dims)
        sudoku_grid.populate_grid(L)
        return sudoku_grid

    def get_all_horizontal_pairs(self) -> list[tuple[T,T]]:
        return [(self.cell(r,c), self.cell(r,c+1)) for r,c in it.product(range(self.size), range(self.size-1))]
    
    def get_all_vertical_pairs(self) -> list[tuple[T,T]]:
        return [(self.cell(r,c), self.cell(r+1,c)) for r,c in it.product(range(self.size-1), range(self.size))]
    
    def get_all_adjacent_pairs(self) -> list[tuple[T,T]]:
        return self.get_all_horizontal_pairs() + self.get_all_vertical_pairs()

    def is_horizontal_neighbor(self, cell1:T, cell2:T) -> bool:
        return self.same_row(cell1,cell2) and (abs(self.get_col(cell1)-self.get_col(cell2))==1)

    def is_vertical_neighbor(self, cell1:T, cell2:T) -> bool:
        return self.same_col(cell1,cell2) and (abs(self.get_row(cell1)-self.get_row(cell2))==1)

    

class SudokuModel(CpModel):
    """
    NOTE: All methods of this class are ZERO-INDEXED!
    """

    def __init__(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True):
        super().__init__()
        self.grid = self.create_grid(size, box_dims, one_indexed_cell_names)
        self.add_sudoku_constraints()


    def create_grid(self, size:int=9, box_dims:tuple[int,int]=(3,3), one_indexed_cell_names:bool=True) -> SudokuGridPlus[CellVar]:
        os = 1 if one_indexed_cell_names else 0
        grid = [[self.new_int_var(1, size, f"Cell[{r+os},{c+os}]") 
                for c in range(size)] 
                for r in range(size)]
        return SudokuGridPlus.from_list(grid, box_dims)

    def add_sudoku_constraints(self):
        for row in self.grid.rows():
            self.add_all_different(row)
        for col in self.grid.cols():
            self.add_all_different(col)
        for box in self.grid.boxes():
            box_cells = ft.reduce(lambda x,y: x+y, box)
            self.add_all_different(box_cells)

    def sort_cells(self, cell1:CellVar, cell2:CellVar) -> tuple[CellVar,CellVar]:
        pair = sorted((self.grid.index(cell1),self.grid.index(cell2)))
        return (self.grid.cell(*pair[0]), self.grid.cell(*pair[1]))

    def add_given(self, cell:CellVar, val:int):
        self.add(cell == val)
                
    def add_givens(self, givens:list[tuple[CellVar,int]]):
        for cell, val in givens:
            self.add(cell == val)

    def add_nonconsecutive(self, cell1:IntVar, cell2:IntVar):
        self.add(cell1 - cell2 != 1)
        self.add(cell2 - cell1 != 1)

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
    model = SudokuModel(6, (2,3))
    givens = [
              ((1,4),1), ((1,6),6)
            , ((2,1),6), ((2,3),4)
            , ((3,1),1), ((3,3),2)
            , ((4,4),5), ((4,6),1)
            , ((5,4),6), ((5,6),3)
            , ((6,1),5), ((6,3),6)
        ]
    given_cells = [(model.grid.cell(r-1,c-1),v) for (r,c),v in givens]
    model.add_givens(given_cells)

    solver = CpSolver()
    solution_printer = SudokuSolutionPrinter(model.grid.items)
    status = solver.solve(model, solution_callback=solution_printer)
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


