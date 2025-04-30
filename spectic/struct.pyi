"""Type stubs for struct module."""
from typing import Any, Callable, ClassVar, Dict, Iterable, List, Optional, Tuple, Type, TypeVar, Union

import msgspec

T = TypeVar("T")

class SpecStruct(msgspec.Struct):
    """Base class for spec-decorated classes.
    
    This class extends msgspec.Struct to preserve validation rules and other
    metadata during serialization-deserialization cycles.
    """
    __spec_rules__: ClassVar[List[Any]]
    __method_rules__: ClassVar[List[Callable]]
    __coerce_fields__: ClassVar[set[str]]
    
    def __post_init__(self) -> None: ...
    def __init__(self, **kwargs: Any) -> None: ...
    def __iter__(self) -> Iterable[str]: ...
    def __getitem__(self, key: str) -> Any: ...