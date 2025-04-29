import inspect
import functools
from types import EllipsisType
from typing import Annotated, Any, Callable, TypeVar, get_type_hints, get_origin, get_args, cast

import msgspec


__version__ = "0.1.0"


from ._hooks import default_deserializer, default_serializer
from .utils import unwrap_annotation


# utility functions for type handling
def get_base_type(annotation: Any) -> Any:
    """Get the base type from any annotation, handling Annotated types properly."""
    if get_origin(annotation) is Annotated:
        # use unwrap_annotation from utils to properly handle any type of annotation
        base_type, _, _ = unwrap_annotation(annotation)
        return base_type
    return annotation


# type vars for better hints
T = TypeVar("T")


# Utility functions for data conversion
def fromdict(cls: type[T], data: dict[str, Any]) -> T:
    """Convert a dictionary to an instance of the specified class."""
    return msgspec.convert(data, cls, dec_hook=default_deserializer)


def asdict(obj: Any) -> dict[str, Any]:
    """Convert an object to a dictionary."""
    return msgspec.to_builtins(obj)


def asjson(obj: Any, *, indent: int | None = None) -> bytes:
    """Convert an object to JSON bytes."""
    # First encode the object to JSON bytes
    json_bytes = msgspec.json.encode(obj, enc_hook=default_serializer)
    
    # If indent is specified, use format to make it pretty
    if indent is not None:
        return msgspec.json.format(json_bytes, indent=indent)
    
    # Otherwise just return the compact JSON
    return json_bytes


def fromjson(cls: type[T], json_str: str | bytes) -> T:
    """Convert a JSON string to an instance of the specified class."""
    return msgspec.json.decode(json_str, type=cls, dec_hook=default_deserializer)


def asyaml(obj: Any, *, indent: int = 2) -> str:
    """Convert an object to a YAML string."""
    try:
        import yaml
        return yaml.dump(asdict(obj), indent=indent, sort_keys=False)
    except ImportError:
        raise ImportError("pyyaml is required for YAML support")


def fromyaml(cls: type[T], yaml_str: str) -> T:
    """Convert a YAML string to an instance of the specified class."""
    try:
        import yaml
        data = yaml.safe_load(yaml_str)
        return fromdict(cls, data)
    except ImportError:
        raise ImportError("pyyaml is required for YAML support")


# -----------------------------------------------------------------------------
# fields


class Field:
  def __init__(
      self, 
      default: Any = ..., 
      constraints: dict[str, Any] | None = None, 
      rule: Callable[[Any], Any] | None = None, 
      coerce: bool = False, 
      **kwargs
  ) -> None:
    # constraints: dict (gt, ge, lt, le, min_length, max_length, pattern, etc)
    self.default = default
    self.constraints = constraints or {}
    self.field_kwargs = kwargs
    self.rule = rule
    self.coerce = coerce


Unknown = EllipsisType


def field(
  default: T | Unknown = ...,
  rule: Callable[[T], bool | None] | None = None,
  message: str | None = None,
  *,
  default_factory: Callable[[], T] | None = None,
  coerce: bool = False,
  name: str | None = None,
  gt: int | float | None = None,
  ge: int | float | None = None,
  lt: int | float | None = None,
  le: int | float | None = None,
  multiple_of: int | float | None = None,
  pattern: str | None = None,
  min_length: int | None = None,
  max_length: int | None = None,
  tz: bool | None = None,
  description: str | None = None,
) -> Field:
  # Save constraints and defer conversion to Annotated
  constraints = {}
  if gt is not None:
    constraints["gt"] = gt
  if ge is not None:
    constraints["ge"] = ge
  if lt is not None:
    constraints["lt"] = lt
  if le is not None:
    constraints["le"] = le
  if min_length is not None:
    constraints["min_length"] = min_length
  if max_length is not None:
    constraints["max_length"] = max_length
  if pattern is not None:
    constraints["pattern"] = pattern
  if description is not None:
    constraints["description"] = description
  if multiple_of is not None:
    constraints["multiple_of"] = multiple_of
  if tz is not None:
    constraints["tz"] = tz

  # if rule has a message, wrap it in a Rule object
  if rule is not None and message is not None:
    rule_obj = Rule(rule, message=message)
  else:
    rule_obj = rule
    
  return Field(
    default,
    constraints, 
    rule_obj, 
    coerce=coerce, 
    name=name, 
    default_factory=default_factory
  )


# -----------------------------------------------------------------------------
# rules


class Rule:
  def __init__(self, expr, bind=None, message=None):
    self.expr = expr
    self.bind = bind
    self.message = message

  def __call__(self, inst):
    inst = inst if not self.bind else getattr(inst, self.bind)
    ok = self.expr(inst)

    if ok is None or ok:
      return True

    raise ValueError(self.message or f"Rule failed: {self.expr}")


# -----------------------------------------------------------------------------
# rule collector for use in class body

_RULE_MARKER = "_marked_rule"


def rule(expr=None, message: str | None = None):
  """Define a validation rule for a spec class.
  
  Can be used in three ways:
  1. As a decorator: @rule
  2. As a decorator with message: @rule(message="error message")
  3. Directly in class body: rule(lambda self: self.x > 0, "x must be positive")
  """
  # if rule is used as a decorator with no arguments
  if callable(expr) and not isinstance(expr, type):
    if inspect.ismethod(expr):
      setattr(expr, _RULE_MARKER, True)
      return expr
    
    # it's a function/lambda, directly create a Rule
    return Rule(expr, message=message)
    
  # if rule is called directly (rule(...))
  # or if it's used as a decorator with arguments
  if expr is None:
    # used as @rule() decorator with optional message
    def decorator(func):
      if inspect.ismethod(func):
        setattr(func, _RULE_MARKER, True)
        return func
      return Rule(func, message=message)
    return decorator
  
  # direct rule definition in class body
  try:
    frame = inspect.currentframe().f_back
    if frame and frame.f_locals is not None:
      local_vars = frame.f_locals
      local_vars.setdefault("__spec_rules__", []).append(Rule(expr, message=message))
  except Exception:
    # Fallback in case of any frame access issues
    pass
    
  return expr


# -----------------------------------------------------------------------------
# typecheck

def check(func):
  """Decorator that validates function arguments based on type annotations.
  
  This decorator performs runtime type checking and conversion for function 
  arguments based on their type annotations. It attempts to convert values
  to the expected type when possible.
  
  Args:
      func: The function to decorate
      
  Returns:
      A wrapped function with argument validation
  
  Example:
      @check
      def calculate_area(width: PositiveInt, height: PositiveInt) -> float:
          return width * height
          
      # This will work - strings are converted to ints
      calculate_area("10", "20")
  """
  @functools.wraps(func)
  def wrapper(*args, **kwargs):
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    annotations = func.__annotations__
    
    for name, value in bound.arguments.items():
      if name in annotations and name != 'return':
        expected_type = annotations[name]
        base_type = get_base_type(expected_type)
        
        # Dictionary isn't automatically converted to custom classes
        if isinstance(value, dict) and inspect.isclass(base_type) and not issubclass(base_type, dict):
            raise TypeError(f"Cannot convert dictionary to {base_type.__name__}")
        
        # Let msgspec handle the validation and conversion
        converted = msgspec.convert(value, expected_type, dec_hook=default_deserializer)
        bound.arguments[name] = converted
    
    return func(*bound.args, **bound.kwargs)
  
  return wrapper


# -----------------------------------------------------------------------------
# main spec magic

T = TypeVar("T")


def spec(cls: type[T]) -> type[T]:
  """Class decorator that transforms a regular class into a validated specification.
  
  The decorated class becomes a msgspec.Struct with validation, coercion and rule checking.
  """
  # For type checkers, create a class template
  spec_class_template = {}
  
  # Extract rules - get the rules defined in class namespace
  namespace = cls.__dict__.copy()
  spec_rules = namespace.get("__spec_rules__", [])
  
  # Also add directly defined rules
  for key, value in list(namespace.items()):
    if key.startswith("__rule_") and isinstance(value, Rule):
      spec_rules.append(value)
  
  # find @rule methods
  method_rules = []
  for name, mem in inspect.getmembers(cls):
    if getattr(mem, _RULE_MARKER, False):
      method_rules.append(mem)

  # type hints
  hints = get_type_hints(cls, include_extras=True)
  attrs = {}  # {name: (type, default/field)}
  msgspec_fields = {}
  coerce_fields = set()  # track fields that should be coerced

  # collect field info
  for key, T in hints.items():
    default = getattr(cls, key, Ellipsis)
    info = None
    if isinstance(default, Field):
      rule = default.rule
      info = default
      default = info.default
      if info.constraints:
        T = Annotated[T, msgspec.Meta(**info.constraints)]
      if rule:
        spec_rules.append(Rule(rule, bind=key))
      if info.coerce:
        coerce_fields.add(key)
    if default is not Ellipsis:
      msgspec_fields[key] = msgspec.field(default=default, **(info.field_kwargs if info else {}))
    else:
      msgspec_fields[key] = msgspec.field()
    attrs[key] = (T, default)
    
    # Add field to class template for static type checking
    spec_class_template[key] = T

  def __post_init__(self) -> None:
    # validate and coerce fields as needed
    for key, T in self.__annotations__.items():
      raw = getattr(self, key)
      should_coerce = key in coerce_fields
      
      # get the base type using our utility function
      base_type = get_base_type(T)
      
      # skip conversion if type matches and coercion not forced
      if isinstance(raw, base_type) and not should_coerce:
        continue
      
      # always try to convert, which will also validate
      try:
        # handle string to number conversion manually if coercion requested
        if should_coerce and isinstance(raw, str):
          if base_type is int:
            try:
              value = int(raw)
              setattr(self, key, value)
              continue
            except (ValueError, TypeError):
                pass  # Fall back to msgspec conversion
          elif base_type is float:
            try:
              value = float(raw)
              setattr(self, key, value)
              continue
            except (ValueError, TypeError):
                pass  # Fall back to msgspec conversion
        
        # standard conversion through msgspec
        value = msgspec.convert(raw, T, dec_hook=default_deserializer)
        if value is not raw:  # only set if value actually changed
          setattr(self, key, value)
      except msgspec.ValidationError as e:
        raise msgspec.ValidationError(str(e) + f" - at `$.{key}`")  # noqa: mimic original exceptions
    
    # rules checks
    for r in self.__rules__:
      try:
        r(self)
      except Exception as e:
        # Make sure the rule validation error is propagated
        if isinstance(e, ValueError):
          raise
        else:
          # Convert other exceptions to ValueError with message
          raise ValueError(f"Rule validation failed: {e}")
          
    for rm in self.__method_rules__:
      try:
        rm(self)
      except Exception as e:
        # Make sure the method rule validation error is propagated
        if isinstance(e, ValueError):
          raise
        else:
          # Convert other exceptions to ValueError with message
          raise ValueError(f"Method rule validation failed: {e}")
    
    # run user's __post_init__ once everything is validated
    if __user_post_init__ := getattr(cls, "__post_init__", None):
      __user_post_init__(self)

  # build new Struct class dynamically
  bases = (msgspec.Struct,)

  __dict__ = {
    "__module__": cls.__module__,
    "__doc__": cls.__doc__,
    "__rules__": spec_rules,
    "__method_rules__": method_rules,
    "__annotations__": {key: T for key, (T, _) in attrs.items()},
    "__post_init__": __post_init__,
    "__coerce_fields__": coerce_fields,
    # Add help for static type checkers
    "__type_hints__": spec_class_template,
  }
  for key, (T, d) in attrs.items():
    __dict__[key] = d if d is not Ellipsis else msgspec_fields[key]

  # Create the actual class
  result_cls = type(cls.__name__, bases, __dict__)
  
  # Add type checking hints via __class_getitem__ to make the class appear
  # like it has proper typing to static type checkers
  result_cls.__orig_bases__ = (msgspec.Struct,)
  
  # Copy attributes from original class to help with type checking
  for key, value in cls.__dict__.items():
    if key.startswith("__") and key.endswith("__"):
      continue  # Skip dunder methods/attributes
    if key not in result_cls.__dict__:
      setattr(result_cls, key, value)
  
  # Type checkers like pyright use this to understand the structure
  setattr(result_cls, "__dataclass_fields__", {
    key: T for key, (T, _) in attrs.items()
  })
  
  return result_cls
