
from ortools.sat.python.cp_model import CpSolver

from my_utils import MyProblemSetup, concatenate_constraint_lists
from sudoku_py.core import Coords
from sudoku_py.constraint import VBorder, XBorder, WhiteKropki, BlackKropki

import itertools as it



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



    v_list:list[tuple[Coords, Coords]] = [  
          ((3,6), (3,7))
        , ((3,7), (4,7))
        , ((5,1), (5,2))
    ]

    x_list:list[tuple[Coords, Coords]] = [  
          ((4,4), (5,4))
        , ((4,9), (5,9))
        , ((6,3), (7,3))
        , ((7,3), (7,4))
        , ((8,8), (8,9))
    ]
    black_kropki_list:list[tuple[Coords, Coords]] = [  
          ((3,3), (3,4))
        , ((3,3), (4,3))
        , ((7,6), (7,7))
        , ((6,7), (7,7))
        , ((9,8), (9,9))
    ]
    white_kropki_list:list[tuple[Coords, Coords]] = [ 
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

    unoffset = lambda cell: (cell[0]-1, cell[1]-1)
    v_constraints:list[VBorder] = [VBorder(*(unoffset(cell) for cell in pair)) for pair in v_list]
    x_constraints:list[XBorder] = [XBorder(*(unoffset(cell) for cell in pair)) for pair in x_list]
    white_kropki_constraints:list[WhiteKropki] = [WhiteKropki(*(unoffset(cell) for cell in pair)) for pair in white_kropki_list]
    black_kropki_constraints:list[BlackKropki] = [BlackKropki(*(unoffset(cell) for cell in pair)) for pair in black_kropki_list]

    
    problem = MyProblemSetup(
          one_indexed=True
        , constraints=concatenate_constraint_lists([v_constraints, x_constraints, white_kropki_constraints, black_kropki_constraints])
        , correct_solution=SOLUTION
    )

    problem.solve(CpSolver())

if __name__=="__main__":
    square_dotted_ring()


    
