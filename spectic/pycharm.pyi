"""PyCharm-specific stubs for better IDE integration.

This module provides type hints for PyCharm-specific features.
"""
from typing import Any, Callable, Dict, Generic, List, Optional, Protocol, Type, TypeVar, Union

T = TypeVar("T")
U = TypeVar("U")

# PyCharm uses this to recognize property accessors
class _PropertyLike(Protocol[T]):
    def __get__(self, instance: Any, owner: Optional[Type[Any]] = ...) -> T: ...
    def __set__(self, instance: Any, value: T) -> None: ...

class SpecClass(Generic[T]):
    """Base class for spec classes in PyCharm type checking."""
    
    def __new__(cls, **kwargs: Any) -> T: ...
    def __init__(self, **kwargs: Any) -> None: ...
    
# PyCharm plugin uses these attributes to understand classes
def __pycharm_attrs__(cls: Type[T]) -> Dict[str, Type[Any]]:
    """Return a dictionary of attributes for PyCharm."""
    return getattr(cls, "__annotations__", {})

def __pycharm_params__(cls: Type[T]) -> List[str]:
    """Return a list of parameters for PyCharm."""
    return list(getattr(cls, "__annotations__", {}).keys())

# Helper for PyCharm type analysis 
def is_spec_class(cls: Type[Any]) -> bool:
    """Check if a class is a spec class."""
    return hasattr(cls, "__spec_rules__")