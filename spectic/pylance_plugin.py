"""Pylance/Pyright plugin for spectic.

For IDE use only - helps with code completion and type checking.
"""
from typing import Any, Dict, List, Optional, Type, TypeVar, cast

T = TypeVar("T")
U = TypeVar("U")

# For Pylance type checker
def plugin_hook(spec_class: Type[T]) -> Type[T]:
    """Hook function for the Pylance language server."""
    return spec_class

class PylanceField:
    """Field for Pylance type analysis."""
    
    def __init__(self, type_annotation: Any, **kwargs: Any) -> None:
        self.type = type_annotation
        self.name = kwargs.get("name", None)
        self.default = kwargs.get("default", ...)
        
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.type
        
    def __get__(self, obj: Any, objtype: Optional[Type[Any]] = None) -> Any:
        if obj is None:
            return self
        # This would be the actual value at runtime
        return self.type

def analyze_spec_class(cls: Type[T]) -> Dict[str, Any]:
    """Analyze a spec class to provide information to the Pylance plugin."""
    annotations = getattr(cls, "__annotations__", {})
    fields = {}
    
    for name, type_hint in annotations.items():
        fields[name] = PylanceField(type_hint)
        
    return {
        "fields": fields,
        "class": cls,
    }