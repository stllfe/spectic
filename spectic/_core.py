import inspect
import functools
from types import EllipsisType
from typing import Annotated, Any, Callable, ClassVar, TypeVar, get_type_hints, get_origin, get_args, cast

# Import dataclass_transform for IDE support
try:
    from typing import dataclass_transform  # Python 3.11+
except ImportError:
    try:
        from typing_extensions import dataclass_transform  # Python 3.8-3.10
    except ImportError:
        # Fallback - create a no-op decorator for older Python versions without typing_extensions
        def dataclass_transform(*args, **kwargs):
            def decorator(cls):
                return cls
            return decorator

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


# Define this variable at the module level
T = TypeVar("T")

def annotate_spec(cls: type[T]) -> type[T]:
    """Annotate a spec class with IDE-friendly metadata.
    
    This function can be used to explicitly mark a class for IDE
    autocomplete support when normal typing isn't working well.
    
    Example:
        User = annotate_spec(User)  # Now IDE will show proper fields
    """
    # Add type hints for the most demanding type checkers
    
    # PyCharm support
    try:
        # PyCharm uses __pydantic_model__ to recognize data models
        setattr(cls, "__pydantic_model__", True)
        
        # PyCharm/VSCode attribute inspection
        if not hasattr(cls, "__dataclass_fields__"):
            annotations = getattr(cls, "__annotations__", {})
            dataclass_fields = {}
            for field_name, field_type in annotations.items():
                field_obj = type('Field', (), {
                    'name': field_name,
                    'type': field_type,
                    'default': getattr(cls, field_name, None),
                    'default_factory': None,
                    'init': True,
                    'repr': True, 
                    'compare': True,
                    'hash': True,
                })
                dataclass_fields[field_name] = field_obj
            setattr(cls, "__dataclass_fields__", dataclass_fields)
            
        # Make it look like a standard class with variables
        for field_name, field_type in getattr(cls, "__annotations__", {}).items():
            if not hasattr(cls, field_name) or isinstance(getattr(cls, field_name), Field):
                setattr(cls, f"__{field_name}_type__", field_type)
    except Exception:
        pass  # Ignore any errors - this is just for IDE support
        
    return cls


# type vars for better hints
T = TypeVar("T")


# Utility functions for data conversion
def fromdict(data: dict[str, Any], cls: type[T]) -> T:
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


def fromjson(json_str: str | bytes, cls: type[T]) -> T:
    """Convert a JSON string to an instance of the specified class."""
    return msgspec.json.decode(json_str, type=cls, dec_hook=default_deserializer)


def asyaml(obj: Any, *, indent: int = 2) -> str:
    """Convert an object to a YAML string."""
    try:
        import yaml
        return yaml.dump(asdict(obj), indent=indent, sort_keys=False)
    except ImportError:
        raise ImportError("pyyaml is required for YAML support")


def fromyaml(yaml_str: str, cls: type[T]) -> T:
    """Convert a YAML string to an instance of the specified class."""
    try:
        import yaml
        data = yaml.safe_load(yaml_str)
        return fromdict(data, cls)
    except ImportError:
        raise ImportError("pyyaml is required for YAML support")


# -----------------------------------------------------------------------------
# fields


class Field:
  """Field definition that works with the @spec decorator.
  
  This class helps define fields with validations and constraints.
  """
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
    
    # Help IDEs with type inspection
    self.type = None  # Will be set during class creation
    self.name = None  # Will be set during class creation
    self.metadata = kwargs  # Store metadata for type checkers
    
  def __get__(self, obj, objtype=None):
    """Support descriptor protocol for better IDE integration.
    
    This makes Field instances behave like the values they represent
    when accessed at runtime.
    """
    if obj is None:
      return self
    return getattr(obj, self.name)
    
  def __set_name__(self, owner, name):
    """Support descriptor protocol for better IDE integration."""
    self.name = name

  # Make Field play nice with type checkers by pretending to be the target type
  def __iter__(self): 
    """Support iteration for sequence types."""
    yield from []  # Empty iterator - just to satisfy type checker
    
  def __getitem__(self, key):
    """Support indexing for dict/list types."""
    raise IndexError("Field is not indexable at class definition time")
  
  # Help type checkers with common operations
  def __add__(self, other): return NotImplemented
  def __sub__(self, other): return NotImplemented
  def __mul__(self, other): return NotImplemented
  def __truediv__(self, other): return NotImplemented
  
  # Special methods to make Field compatible with type checkers
  def __call__(self, *args, **kwargs):
    """Support calling Field() instances as if they were the target type."""
    return None
    
  # Make Field pretend to be any basic type
  def __str__(self): return ""
  def __int__(self): return 0
  def __float__(self): return 0.0
  def __bool__(self): return False
  
  # For sequence types
  def __len__(self): return 0
  
  def __repr__(self):
    """Better representation for debugging."""
    type_str = f": {self.type.__name__}" if hasattr(self, "type") and self.type else ""
    default_str = f" = {self.default}" if self.default is not Ellipsis else ""
    return f"{self.name or '?'}{type_str}{default_str}"


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
    
    # Capture location information for better error messages
    try:
      if inspect.isfunction(expr) or isinstance(expr, type(lambda: None)):
        frame = inspect.currentframe().f_back.f_back  # Two frames back to get caller of rule()
        self.filename = frame.f_code.co_filename
        self.lineno = frame.f_lineno
        # Try to get source if it's a lambda
        if isinstance(expr, type(lambda: None)):
          try:
            source_lines, start_line = inspect.getsourcelines(frame)
            # Find the line with "lambda" in it near our line number
            for i, line in enumerate(source_lines):
              if "lambda" in line and i + start_line <= frame.f_lineno:
                self.source = line.strip()
                break
          except Exception:
            self.source = str(expr)
        else:
          self.source = str(expr)
    except Exception:
      self.filename = None
      self.lineno = None
      self.source = str(expr)

  def __call__(self, inst):
    inst = inst if not self.bind else getattr(inst, self.bind)
    
    try:
      ok = self.expr(inst)
      
      if ok is None or ok:
        return True
        
      error_message = self.message or f"Rule failed: {self.source if hasattr(self, 'source') else self.expr}"
      if hasattr(self, 'filename') and hasattr(self, 'lineno') and self.filename and self.lineno:
        error_message += f" (defined at {self.filename}:{self.lineno})"
        
      raise ValueError(error_message)
      
    except Exception as e:
      if not isinstance(e, ValueError) and self.message:
        # If an exception occurred in the rule itself, wrap it with our message
        error_message = f"{self.message} (rule execution failed: {e})"
        if hasattr(self, 'filename') and hasattr(self, 'lineno') and self.filename and self.lineno:
          error_message += f" (defined at {self.filename}:{self.lineno})"
        raise ValueError(error_message) from e
      raise


# -----------------------------------------------------------------------------
# rule collector for use in class body

_RULE_MARKER = "_marked_rule"


def rule(expr=None, message: str | None = None):
  """Define a validation rule for a spec class.

  Can be used in three ways:
  1. As a decorator for methods: @rule
  2. As a decorator with message: @rule(message="error message")
  3. Directly in class body with lambda: rule(lambda self: self.x > 0, "x must be positive")

  Examples:
      @rule
      def validate(self):
          if self.x <= 0:
              raise ValueError("x must be positive")

      # OR

      rule(lambda self: self.x > 0, "x must be positive")
  """
  # For lambdas and all callables in class body
  if expr is not None and callable(expr):
    # Create a Rule object for the expression
    rule_obj = Rule(expr, message=message)
    
    # Try to detect if we're in a class body
    try:
      frame = inspect.currentframe().f_back
      if frame and frame.f_locals is not None:
        # Look for signs we're in a class definition
        if "__module__" in frame.f_locals:
          # We're in a class definition, add to __spec_rules__
          frame.f_locals.setdefault("__spec_rules__", []).append(rule_obj)
    except Exception:
      # Fallback in case of frame access issues
      pass
    
    # If it's a method, mark it
    if inspect.ismethod(expr) or inspect.isfunction(expr):
      setattr(expr, _RULE_MARKER, True)
      
    return rule_obj if not (inspect.ismethod(expr) or inspect.isfunction(expr)) else expr

  # if rule is called directly (rule(...))
  # or if it's used as a decorator with arguments
  if expr is None:
    # used as @rule() decorator with optional message
    def decorator(func):
      # Create and attach rule
      rule_obj = Rule(func, message=message)
      
      # Mark the function
      setattr(func, _RULE_MARKER, True)
      
      # Try to add to class body if in class definition
      try:
        frame = inspect.currentframe().f_back
        if frame and frame.f_locals is not None:
          if "__module__" in frame.f_locals:
            frame.f_locals.setdefault("__spec_rules__", []).append(rule_obj)
      except Exception:
        pass
        
      return func
    return decorator

  # Direct rule in class body for non-callable expressions (rare)
  try:
    frame = inspect.currentframe().f_back
    if frame and frame.f_locals is not None:
      # We're in a class definition
      local_vars = frame.f_locals
      local_vars.setdefault("__spec_rules__", []).append(Rule(expr, message=message))
  except Exception:
    # Fallback in case of any frame access issues
    pass

  return expr


# -----------------------------------------------------------------------------
# typecheck

def check(func, *, coerce=True):
  """Decorator that validates function arguments based on type annotations.

  This decorator performs runtime type checking and conversion for function
  arguments based on their type annotations. It attempts to convert values
  to the expected type when possible.

  Args:
      func: The function to decorate
      coerce: Whether to attempt coercion for basic types (default: True)

  Returns:
      A wrapped function with argument validation

  Example:
      @check
      def calculate_area(width: PositiveInt, height: PositiveInt) -> float:
          return width * height

      # This will work - strings are converted to ints
      calculate_area("10", "20")
  """
  if func is None:
    return functools.partial(check, coerce=coerce)

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

        # Handle string to numeric conversion if coerce=True
        if coerce and isinstance(value, str):
            if base_type is int:
                try:
                    bound.arguments[name] = int(value)
                    continue
                except (ValueError, TypeError):
                    pass
            elif base_type is float:
                try:
                    bound.arguments[name] = float(value)
                    continue
                except (ValueError, TypeError):
                    pass

        # Let msgspec handle the validation and conversion
        try:
            converted = msgspec.convert(value, expected_type, dec_hook=default_deserializer)
            bound.arguments[name] = converted
        except Exception as e:
            if isinstance(value, (int, float, str, bool)) and not isinstance(value, base_type):
                # More friendly error for simple type mismatches
                raise TypeError(f"Cannot convert {type(value).__name__} to {base_type.__name__}: {value}")
            raise  # Re-raise original exception

    return func(*bound.args, **bound.kwargs)

  return wrapper


# -----------------------------------------------------------------------------
# main spec magic

T = TypeVar("T")


# Apply dataclass_transform to help IDEs understand our class transformer
@dataclass_transform(
    field_specifiers=(Field, field),
    kw_only_default=False,
)
def spec(cls: type[T]) -> type[T]:
  """Class decorator that transforms a regular class into a validated specification.

  The decorated class becomes a msgspec.Struct with validation, coercion and rule checking.
  
  Example:
      ```python
      @spec
      class User:
          name: str
          email: str = field(pattern=r"^[^@]+@[^@]+\.[^@]+$")
          age: int = field(ge=0)
      
      # Type checkers understand the __init__ signature
      user = User(name="John", email="john@example.com", age=30)
      ```
  """
  # For type checkers, create a class template
  spec_class_template = {}

  # Extract rules - get the rules defined in class namespace
  namespace = cls.__dict__.copy()
  spec_rules = []

  # Get rules directly from the class's __spec_rules__ attribute if present
  if "__spec_rules__" in namespace:
    spec_rules.extend(namespace["__spec_rules__"])
  # For backward compatibility - check for __rules__ too
  elif "__rules__" in namespace:
    spec_rules.extend(namespace["__rules__"])

  # Also add any rules created via rule(...) calls in the class body
  for key, value in list(namespace.items()):
    if key.startswith("__rule_") and isinstance(value, Rule):
      spec_rules.append(value)

  # find @rule methods
  method_rules = []
  for name, mem in inspect.getmembers(cls):
    if callable(mem) and hasattr(mem, _RULE_MARKER) and getattr(mem, _RULE_MARKER, False):
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
      
      # Set type information on the Field object to help IDEs
      info.type = T
      info.name = key
      
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
      if not should_coerce:
        try:
          # Try direct isinstance first
          if isinstance(raw, base_type):
            continue
        except TypeError:
          # If that fails, try to handle complex types more carefully
          try:
            # Get the origin type without subscripts (e.g., List from List[str])
            origin_type = get_origin(base_type)
            if origin_type and isinstance(raw, origin_type):
              continue
              
            # Special case for basic types that are commonly used
            if base_type in (str, int, float, bool, list, dict, set, tuple) and isinstance(raw, base_type):
              continue
          except TypeError:
            # If we still can't check, let the conversion happen
            pass

      # always try to convert, which will also validate
      try:
        # Skip ClassVar and similar utility types
        if get_origin(T) in (ClassVar, type, Any):
          continue
            
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
        try:
          value = msgspec.convert(raw, T, dec_hook=default_deserializer)
          if value is not raw:  # only set if value actually changed
            setattr(self, key, value)
        except (TypeError, ValueError) as e:
          if "ClassVar" in str(e) or "is not supported" in str(e):
            # Skip unsupported types
            continue
          raise
      except msgspec.ValidationError as e:
        raise msgspec.ValidationError(str(e) + f" - at `$.{key}`")  # noqa: mimic original exceptions

    # Apply all rules - keep this for backward compatibility
    # In case SpecStruct.__post_init__ is not called
    for r in self.__rules__:
        r(self)

    # Apply method rules
    for rm in self.__method_rules__:
        rm(self)
    
    # run user's __post_init__ if it exists
    if __user_post_init__ := getattr(cls, "__post_init__", None):
      __user_post_init__(self)

  # build new Struct class using our SpecStruct as the base
  try:
    from .struct import SpecStruct
    bases = (SpecStruct,)
  except ImportError:
    # Fallback to standard msgspec.Struct if our implementation isn't available
    bases = (msgspec.Struct,)

  __dict__ = {
    "__module__": cls.__module__,
    "__doc__": cls.__doc__,
    # Keep both names for compatibility
    "__spec_rules__": spec_rules,
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

  # Since msgspec.StructMeta is immutable, we can't modify it directly.
  # Instead, we'll set hints via other mechanisms that IDEs look for.
  
  # Create a class_getitem method that allows IDE autocompletion via Generic[T] pattern
  def class_getitem(cls, params):
    # This is needed for type checking with subscripted types
    return cls
    
  result_cls.__class_getitem__ = classmethod(class_getitem)
  
  # Type checkers like pyright use this to understand the structure
  dataclass_fields = {}
  for field_name, (field_type, default) in attrs.items():
    field_obj = type('Field', (), {
      'name': field_name,
      'type': field_type,
      'default': default if default is not Ellipsis else None,
      'default_factory': None,
      'init': True,
      'repr': True,
      'compare': True,
      'metadata': {},
      'hash': True,
    })
    dataclass_fields[field_name] = field_obj
  
  setattr(result_cls, "__dataclass_fields__", dataclass_fields)
  
  # Add class annotations for IDE support
  annotations = {}
  for field_name, (field_type, _) in attrs.items():
    annotations[field_name] = field_type
  setattr(result_cls, "__annotations__", annotations)
  
  # Add a custom __init_subclass__ that copies annotations
  def __init_subclass__(cls, **kwargs):
    super(result_cls, cls).__init_subclass__(**kwargs)
    # Copy annotations to help type checkers
    parent_annotations = getattr(result_cls, "__annotations__", {})
    cls_annotations = getattr(cls, "__annotations__", {})
    for name, type_hint in parent_annotations.items():
      if name not in cls_annotations:
        cls_annotations[name] = type_hint
    setattr(cls, "__annotations__", cls_annotations)
  
  setattr(result_cls, "__init_subclass__", classmethod(__init_subclass__))
  
  # Add various hints for different IDEs and type checkers
  # PyCharm specific
  setattr(result_cls, "__pydantic_model__", True)
  
  # Add field class variables - helps static type checkers
  for field_name, (field_type, _) in attrs.items():
    # This pattern is recognized by many type checkers
    setattr(result_cls, f"__field_{field_name}__", field_type)
  
  # Support mypy plugin pattern
  result_cls.__origin__ = cls
  result_cls.__mypyc_attrs__ = {k: v for k, (v, _) in attrs.items()}
  
  # Add methods to support various type checking protocols
  def __get_type_hints(cls):
    return {k: v for k, (v, _) in attrs.items()}
  
  setattr(result_cls, "__get_type_hints__", classmethod(__get_type_hints))
  
  # Support pydantic compatibility for PyCharm
  def __get_validators__(cls):
    return []
  
  setattr(result_cls, "__get_validators__", classmethod(__get_validators__))
  
  # Support attrs typing pattern
  result_cls.__attrs_attrs__ = [
    type('Attribute', (), {'name': k, 'type': v})
    for k, (v, _) in attrs.items()
  ]
  
  return result_cls
