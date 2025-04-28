import inspect

from types import EllipsisType
from typing import Annotated, Callable, TypeVar, get_type_hints

import msgspec


__version__ = "0.1.0"


from ._hooks import default_deserializer


# -----------------------------------------------------------------------------
# symbolic expressions for `this` proxy


class SymbolicExpr:
  def __init__(self, op, left, right=None):
    self.op = op
    self.left = left
    self.right = right

  def __eq__(self, other):
    return SymbolicExpr("==", self, other)

  def __ne__(self, other):
    return SymbolicExpr("!=", self, other)

  def __lt__(self, other):
    return SymbolicExpr("<", self, other)

  def __le__(self, other):
    return SymbolicExpr("<=", self, other)

  def __gt__(self, other):
    return SymbolicExpr(">", self, other)

  def __ge__(self, other):
    return SymbolicExpr(">=", self, other)

  def __add__(self, other):
    return SymbolicExpr("+", self, other)

  def __sub__(self, other):
    return SymbolicExpr("-", self, other)

  def __mod__(self, other):
    return SymbolicExpr("%", self, other)

  def __mul__(self, other):
    return SymbolicExpr("*", self, other)

  def __truediv__(self, other):
    return SymbolicExpr("/", self, other)


class ThisRef:
  def __init__(self, name: str | None = "$"):
    self._name = name

  def __getattr__(self, attr):
    n = f"{self._name}.{attr}" if self._name else attr
    return ThisRef(n)

  def __repr__(self):
    return f"this.{self._name}"

  def __lt__(self, other):
    return SymbolicExpr("<", self, other)

  def __le__(self, other):
    return SymbolicExpr("<=", self, other)

  def __gt__(self, other):
    return SymbolicExpr(">", self, other)

  def __ge__(self, other):
    return SymbolicExpr(">=", self, other)

  def __eq__(self, other):
    return SymbolicExpr("==", self, other)

  def __ne__(self, other):
    return SymbolicExpr("!=", self, other)

  def __add__(self, other):
    return SymbolicExpr("+", self, other)

  def __sub__(self, other):
    return SymbolicExpr("-", self, other)

  def __mod__(self, other):
    return SymbolicExpr("%", self, other)

  def __mul__(self, other):
    return SymbolicExpr("*", self, other)

  def __truediv__(self, other):
    return SymbolicExpr("/", self, other)

  def __contains__(self, other):
    return SymbolicExpr("in", other, self)


this = ThisRef()

# -----------------------------------------------------------------------------
# rules


class Rule:
  def __init__(self, expr, bind=None, message=None):
    self.expr = expr
    self.bind = bind
    self.message = message

  def __call__(self, inst):
    inst = inst if not self.bind else getattr(inst, self.bind)
    ok = _eval_expr(self.expr, inst)

    if ok is None or ok:
      return True

    raise ValueError(self.message or f"Rule failed: {self.expr}")


def _eval_expr(expr, instance):
  if isinstance(expr, ThisRef):
    parts = expr._name.split(".")
    val = instance
    for p in parts:
      val = getattr(val, p)
    return val
  elif isinstance(expr, Callable):
    return expr(instance)
  elif isinstance(expr, SymbolicExpr):
    op = expr.op
    left = _eval_expr(expr.left, instance)
    right = _eval_expr(expr.right, instance) if expr.right is not None else None
    if op == "<":
      return left < right
    if op == "<=":
      return left <= right
    if op == ">":
      return left > right
    if op == ">=":
      return left >= right
    if op == "==":
      return left == right
    if op == "!=":
      return left != right
    if op == "+":
      return left + right
    if op == "-":
      return left - right
    if op == "*":
      return left * right
    if op == "/":
      return left / right
    if op == "%":
      return left % right
    raise RuntimeError(op)
  return expr


# -----------------------------------------------------------------------------
# fields


class Field:
  def __init__(self, default=..., constraints=None, rule=None, **kwargs) -> None:
    # constraints: dict (gt, ge, lt, le, min_length, max_length, pattern, etc)
    self.default = default
    self.constraints = constraints or {}
    self.field_kwargs = kwargs
    self.rule = rule


T = TypeVar("T")

Unknown = EllipsisType


def field(
  default: T | Unknown = ...,
  *,
  default_factory: Callable | None = None,
  rule: Callable[[T], None] | None = None,
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

  return Field(default, constraints, rule, name=name, default_factory=default_factory)


# -----------------------------------------------------------------------------
# rule collector for use in class body

_RULE_MARKER = "_marked_rule"


def rule(expr=None, message: str | None = None):
  if inspect.ismethod(expr):
    setattr(expr, _RULE_MARKER, True)
    return expr
  frame = inspect.currentframe().f_back
  local_vars = frame.f_locals
  local_vars.setdefault("__spec_rules__", []).append(Rule(expr, message=message))
  print(local_vars)


# -----------------------------------------------------------------------------
# main spec magic

T = TypeVar("T")


def spec(cls: type[T]) -> type[T]:
  spec_rules = getattr(cls, "__spec_rules__", [])

  # find @rule methods
  method_rules = []
  for name, mem in inspect.getmembers(cls):
    if getattr(mem, _RULE_MARKER, False):
      method_rules.append(mem)

  # type hints
  hints = get_type_hints(cls, include_extras=True)
  attrs = {}  # {name: (type, default/field)}
  msgspec_fields = {}

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
    if default is not Ellipsis:
      msgspec_fields[key] = msgspec.field(default=default, **info.field_kwargs)
    else:
      msgspec_fields[key] = msgspec.field()
    attrs[key] = (T, default)

  def __post_init__(self) -> None:
    # Pydantic-like validation on construction
    # data = msgspec.to_builtins(self, enc_hook=default_serializer)
    # re-validate as msgspec would do on decode (raises ValueError/TypeError)
    for key, T in self.__annotations__.items():
      raw = getattr(self, key)
      try:
        value = msgspec.convert(raw, T, dec_hook=default_deserializer)
      except msgspec.ValidationError as e:
        raise msgspec.ValidationError(str(e) + f" - at `$.{key}`")  # noqa: mimic original exceptions
      setattr(self, key, value)
    # rules checks
    for r in self.__rules__:
      r(self)
    for rm in self.__method_rules__:
      rm(self)
    # run user's __post_init__ once everything is validated
    if __user_post_init__ := getattr(cls, "__post_init__", None):
      __user_post_init__(self)

  # Build new Struct class dynamically
  bases = (msgspec.Struct,)

  __dict__ = {
    "__module__": cls.__module__,
    "__doc__": cls.__doc__,
    "__rules__": spec_rules,
    "__method_rules__": method_rules,
    "__annotations__": {key: T for key, (T, _) in attrs.items()},
    "__post_init__": __post_init__,
  }
  for key, (T, d) in attrs.items():
    __dict__[key] = d if d is not Ellipsis else msgspec_fields[key]

  return type(cls.__name__, bases, __dict__)
