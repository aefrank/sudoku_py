
from collections.abc import Callable, Iterable
from itertools import filterfalse, tee
from typing import Any, NewType, Optional, TypeIs, TypeVar, overload
import functools as ft

T = TypeVar('T')



############        CELL COORDINATES   ########################

type Coords = tuple[int,int]
def is_Coords(x:Any) -> TypeIs[Coords]:
    """Type check that x is of type Coords.
    """
    if isinstance(x, tuple):
        if len(x)==2 and isinstance(x[0],int) and isinstance(x[1],int):
            return True
    return False


############        CELL ADJACENCY      ########################

AdjacentCellPair = NewType("AdjacentCellPair", tuple[Coords, Coords])
@overload
def is_adjacent(cell1:Coords, cell2:Coords, /) -> bool: ...
@overload 
def is_adjacent(cell_pair:tuple[Coords,Coords], /) -> TypeIs[AdjacentCellPair]: ...
def is_adjacent(arg0:Coords|tuple[Coords,Coords], arg1:Optional[Coords]=None) -> bool:
    """Predicate reporting if two coordinates are adjacent.
    """
    if is_Coords(arg0):
        if not is_Coords(arg1):
            raise ValueError(arg1)
        dr, dc = abs(arg0[0]-arg1[0]), abs(arg0[1]-arg1[1])
        return dr+dc==1 
    else:
        if is_Coords(arg0[0]) and is_Coords(arg0[1]):
            return is_adjacent(arg0[0], arg0[1])
        else:
            raise ValueError(arg0, arg1)

def verify_adjacency(pair:tuple[Coords,Coords]) -> AdjacentCellPair:
    """"Casts pair of adjacent cell coordinates to type AdjacentCellPair, or
    raises TypeError if they are not adjacent."""
    if is_adjacent(pair):
        return pair
    else:
        raise TypeError(pair)


############        MANIPULATING CELL ITERABLES   ########################

@overload
def sort_cells(cell1:Coords, cell2:Coords, /) -> tuple[Coords, Coords]: ...
@overload
def sort_cells(*cells:Coords) -> tuple[Coords, ...]: ...
def sort_cells(*cells:Coords) -> tuple[Coords, ...]:
    """Sorts iterable of Coords low-to-high by row then column.
    """
    ordered = sorted(cells)
    if isinstance(cells,tuple):
        return (ordered[0], ordered[1])
    else:
        return tuple(ordered)

def partition(iterable:Iterable[T], pred:Callable[[T],bool]) -> tuple[filter[T], filterfalse[T]]:
    """Splits an iterable into two: one matching pred, one not matching pred.
    """
    t1, t2 = tee(iterable)
    return filter(pred, t1), filterfalse(pred, t2)