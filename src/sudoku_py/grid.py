from collections.abc import Generator
from typing import Any, Generic, TypeVar
import functools as ft
import itertools as it


T = TypeVar("T")

class BaseSudokuGrid(Generic[T]):
    """Base data structure for CP Model variable storage and handling.

    Stores data in a NxN grid represented by N nested N-length lists.
    
    Contains data querying methods and some basic predicates such as
    whether two cells are in the same 'sudoku box'.
    """
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
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> BaseSudokuGrid[T]:
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
        return [self.col(i) for i in range(self.size)]

    def boxes(self) -> list[list[list[T]]]:
        return [self.box(i) for i in range(self.rows_of_boxes*self.cols_of_boxes)]

    def cells(self) -> list[T]:
        return ft.reduce(lambda x,y: x+y, self.rows())

    def get_row(self, item:T) -> int:
        return self.index(item)[0]

    def get_col(self, item:T) -> int:
        return self.index(item)[1]

    def get_box(self, item:T) -> int:
        for i,box in enumerate(self.boxes()):
            if item in ft.reduce(lambda x,y: x+y, box):
                return i
        # if we get to here, item does not exist in grid
        raise ValueError(item)

    def same_row(self, cell1:T, cell2:T) -> bool:
            return self.get_row(cell1) == self.get_row(cell2)
    
    def same_col(self, cell1:T, cell2:T) -> bool:
        return self.get_col(cell1) == self.get_col(cell2)

    def same_box(self, cell1:T, cell2:T) -> bool:
        return self.get_box(cell1) == self.get_box(cell2)

    def __len__(self) -> int:
        return self.size

    def __iter__(self) -> Generator[list[T], Any, Any]:
        for item in self.items:
            yield item



class SudokuGrid(BaseSudokuGrid[T]):
    """Extended data structure for CP Model variable storage and handling.
    
        Stores data in a NxN grid represented by N nested N-length lists.
        
        Contains basic data querying methods and predicates, and adds
        methods to generate derived queries such as getting all pairs
        of adjacent cells.
    """

    @classmethod
    def from_list(cls, L:list[list[T]], box_dims:tuple[int,int]=(3,3)) -> SudokuGrid[T]: 
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
