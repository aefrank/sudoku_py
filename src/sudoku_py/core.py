
from collections.abc import Callable, Iterable, Sequence
from itertools import filterfalse, tee
from typing import Any, NewType, Optional, TypeIs, TypeVar, Union, overload
import functools as ft

from more_itertools import peekable

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


############        MANIPULATING ITERABLES   ########################

@overload
def sort_cells(cell1:Coords, cell2:Coords, /) -> tuple[Coords, Coords]: ...
@overload
def sort_cells(*cells:Coords) -> tuple[Coords, ...]: ...
def sort_cells(*cells:Coords) -> tuple[Coords, ...]:
    """Sorts iterable of Coords low-to-high by row then column.
    """
    ordered = sorted(cells)
    if isinstance(cells, tuple):
        return (ordered[0], ordered[1])
    else:
        return tuple(ordered)

def partition(iterable:Iterable[T], predicate:Callable[[T],bool]) -> tuple[filter[T], filterfalse[T]]:
    """Splits an iterable into two: one containing the elements for which predicate is True, one containing those for which it is False.
    """
    t1, t2 = tee(iterable)
    return filter(predicate, t1), filterfalse(predicate, t2)

def disjoint_partition[T](values:Iterable[T], predicate:Callable[[T], bool], *more_predicates:Callable[[T], bool], include_leftovers:bool=False) -> list[list[T]]:
    """Splits an iterable into the values for which each mutually-exclusive predicate returns true.

    If include_leftovers=True, appends list of remaining values for which no predicate returned true at the end of the list.
    """
    true_list, false_list = (list(x) for x in partition(values, predicate))
    
    if not false_list or not more_predicates:
        if include_leftovers:
            return [true_list] + [false_list]
        else:
            return [true_list]
        
    return [true_list] + disjoint_partition(false_list, *more_predicates, include_leftovers=include_leftovers)

def partition_out_type[T](values:Iterable[Any], target_type:type[T]) -> tuple[list[T], list[Any]]:
    """Splits an iterable into one list of all its elements of type T, and another list of all its elements not of type T. 
    """
    Ts, not_Ts = partition(values, lambda x: isinstance(x, target_type))
    return list(Ts), list(not_Ts)

def partition_out_disjoint_types[T](values:Iterable[Any], target_type:type[T], *more_target_types:type) -> list[filter[T]|Any]:
    """Splits an iterable into separate lists containing all elements of each of the mutually exclusive target types.

    Elements that are of none of the target types are not returned.
    """
    T_list, not_T_list = partition_out_type(values, target_type)
    if not not_T_list or not more_target_types:
        return [T_list]
    else:
         return [T_list] + partition_out_disjoint_types(not_T_list, *more_target_types)
