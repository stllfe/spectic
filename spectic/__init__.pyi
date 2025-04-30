"""Type stubs for spectic library - mimicking msgspec's approach"""

import enum
from typing import (
    Any,
    Callable, 
    ClassVar,
    Dict, 
    Final,
    Iterable, 
    List, 
    Literal,
    Mapping, 
    Optional, 
    Tuple, 
    Type, 
    TypeVar, 
    Union,
    overload,
)

try:
    from typing import dataclass_transform  # Python 3.11+
except ImportError:
    from typing_extensions import dataclass_transform  # Python 3.8+

from . import types

T = TypeVar("T")

# Sentinel value for default
class UnknownType(enum.Enum):
    UNKNOWN = "..."

Unknown = UnknownType.UNKNOWN

# --- Rule class ---
class Rule:
    def __init__(
        self, 
        expr: Callable[[Any], Any],
        bind: Optional[str] = None,
        message: Optional[str] = None
    ) -> None: ...
    
    expr: Callable[[Any], Any]
    bind: Optional[str]
    message: Optional[str]
    filename: Optional[str]
    lineno: Optional[int]
    source: str
    
    def __call__(self, inst: Any) -> bool: ...

# --- Field class ---
class Field:
    def __init__(
        self,
        default: Any = ...,
        constraints: Optional[Dict[str, Any]] = None,
        rule: Optional[Callable[[Any], bool]] = None,
        coerce: bool = False,
        **kwargs: Any
    ) -> None: ...
    
    default: Any
    constraints: Dict[str, Any]
    field_kwargs: Dict[str, Any]
    rule: Optional[Callable[[Any], bool]]
    coerce: bool

# --- Struct base class ---
@dataclass_transform(field_specifiers=(Field, field))
class Struct:
    """Base class for all spec-decorated classes."""
    __spec_rules__: ClassVar[List[Rule]]
    __method_rules__: ClassVar[List[Callable]]
    __annotations__: ClassVar[Dict[str, Any]]
    __coerce_fields__: ClassVar[set[str]]
    
    def __init__(self, **kwargs: Any) -> None: ...
    def __post_init__(self) -> None: ...
    def __iter__(self) -> Iterable[str]: ...
    def __getitem__(self, key: str) -> Any: ...

# --- Field function ---
@overload
def field(
    default: T = ...,
    rule: Optional[Callable[[T], bool]] = None,
    message: Optional[str] = None,
    *,
    default_factory: Optional[Callable[[], T]] = None,
    coerce: bool = False,
    name: Optional[str] = None,
    gt: Optional[Union[int, float]] = None,
    ge: Optional[Union[int, float]] = None,
    lt: Optional[Union[int, float]] = None,
    le: Optional[Union[int, float]] = None,
    multiple_of: Optional[Union[int, float]] = None,
    pattern: Optional[str] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    tz: Optional[bool] = None,
    description: Optional[str] = None,
) -> T: ...

# --- Rule function ---
@overload
def rule(expr: Callable[[Any], bool], message: Optional[str] = None) -> Rule: ...

@overload
def rule(expr: None = None, message: Optional[str] = None) -> Callable[[Callable[[Any], bool]], Callable[[Any], bool]]: ...

# --- Spec decorator ---
@dataclass_transform(field_specifiers=(Field, field))
def spec(cls: Type[T]) -> Type[Struct]: ...

# --- Check function ---
@overload
def check(func: Callable[..., T]) -> Callable[..., T]: ...

@overload
def check(*, coerce: bool = True) -> Callable[[Callable[..., T]], Callable[..., T]]: ...

# --- Annotation function ---
def annotate_spec(cls: Type[T]) -> Type[T]: ...

# --- Conversion functions ---
def asdict(obj: Any) -> Dict[str, Any]: ...
def asjson(obj: Any, *, indent: Optional[int] = None) -> bytes: ...
def asyaml(obj: Any, *, indent: int = 2) -> str: ...
def fromdict(data: Dict[str, Any], cls: Type[T]) -> T: ...
def fromjson(json_str: Union[str, bytes], cls: Type[T]) -> T: ...
def fromyaml(yaml_str: str, cls: Type[T]) -> T: ...