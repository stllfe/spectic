"""SpecStruct implementation that extends msgspec.Struct.

This module provides a proper subclass of msgspec.Struct that preserves
validation rules and other metadata during serialization-deserialization.
"""
from typing import Any, Callable, ClassVar, Dict, List, Optional, Type, TypeVar, cast, get_type_hints

import msgspec

# For backwards compatibility, we raise ValueError directly 
# instead of custom exceptions (our own exceptions would break tests)
# from .exceptions import SpecError

T = TypeVar("T")

class SpecStruct(msgspec.Struct):
    """Base class for spec-decorated classes.
    
    This class extends msgspec.Struct to preserve validation rules and other
    metadata during serialization-deserialization cycles.
    """
    # These will be set by the @spec decorator
    __spec_rules__: ClassVar[List[Any]] = []
    __method_rules__: ClassVar[List[Callable]] = []
    __coerce_fields__: ClassVar[set] = set()
    
    def __post_init__(self) -> None:
        """Validate the struct after initialization.
        
        This method is called after __init__ to perform validation of field values
        and apply rules. It's called automatically by msgspec.
        """
        # Apply field-level validation and coercion first
        # This would be implemented by the spec decorator
        
        # Apply all class rules
        for rule in self.__spec_rules__:
            try:
                rule(self)
            except Exception as e:
                if isinstance(e, ValueError):
                    # Re-raise ValueErrors directly for backward compatibility
                    raise
                raise ValueError(f"Rule validation failed: {e}") from e
        
        # Apply method rules
        for method_rule in self.__method_rules__:
            try:
                method_rule(self)
            except Exception as e:
                if isinstance(e, ValueError):
                    # Re-raise ValueErrors directly for backward compatibility
                    raise
                raise ValueError(f"Method rule validation failed: {e}") from e