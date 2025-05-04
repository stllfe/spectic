<div align="center">

# `spectic` 🧐

_unparanoid data validation, just a little bit spectical_

🔥 **Blazing fast, type-safe, drop-in alternative to pydantic, attrs, and dataclasses
for instant classes with validation, parsing, and serialization.**

@powered by [`msgspec`](https://jcristharif.com/msgspec/) 🚀

</div>

## Features

- **Python-first, declarative models:** via the `@spec` decorator
- **Ready-made types:** intervals, non-empty strings, emails, ...
- **Field and model-level validation:** using a simple `@rule` decorator at class definition
- **Dataclasses-like API:** `asdict`, `astuple`, `replace` extended with `fromdict`, `fromtuple`, `asjson` and many more ...
- **JSON/YAML/Msgpack:** serialization and deserialization with rich type support
- **Runtime function argument validation:** `@check` (similar to pydantic’s `@validate_call`)
- **Blazing speed:** uses msgspec under the hood

## Example

```python
from spectic import spec, field, rule, asdict, asjson, check
from spectic.types import ClosedUnitInterval, PositiveInt, NonEmptyStr

@spec
class User:
  name: NonEmptyStr
  age: PositiveInt

@spec
class Experiment:
  title: NonEmptyStr
  owner: User
  trust: ClosedUnitInterval
  attempts: PositiveInt
  threshold: float = field(ge=0, le=1)

  # spec-level rule: constraint involving multiple fields
  rule(lambda s: s.trust > s.threshold, "experiment trust must exceed threshold")
  rule(lambda s: s.owner.age >= s.attempts, "owner's age must be at least equal to attempts")
  rule(lambda s: s.title.lower() not in s.owner.name.lower(), "title must not include owner's name")

  # or as a method (will be accessible in this case)
  @rule
  def validate(self) -> None:
    if self.trust <= self.threshold:
      raise ValueError("experiment trust must exceed threshold")
    if self.owner.age < self.attempts:
      raise ValueError("owner's age must be at least equal to attempts")
    if self.title.lower() in self.owner.name.lower():
      raise ValueError("title must not include owner's name")

# strict construction: must pass typed values!
exp = Experiment(
  title="SuperTest",
  owner=User(name="alice", age=5),
  trust=0.8,
  attempts=3,
  threshold=0.7
)
# This will fail: Experiment(title="test", owner=User(...), trust=0.5, attempts=10, threshold=0.6)

from spectic import asdict, asjson, fromdict, fromjson

data = {
  "title": "big trial",
  "owner": {"name": "bob", "age": 15},
  "trust": 0.9,
  "attempts": 12,
  "threshold": 0.2,
}
exp2 = fromdict(data, Experiment)  # works: dicts auto-converted only on fromdict!

from spectic import check

@check
def calculate_area(height: PositiveInt, width: PositiveInt) -> PositiveInt:
  return height * width

# This will work: calculate_area(3, 4)
# This will fail: calculate_area(3, -5)
# This will fail: calculate_area(3, "4")
#   but with @check(coerce=True) it will work!

```

## Install

```bash
pip install spectic
```

## Philosophy

**`spectic` is built on a few clear and deliberate principles:**

- 😤 **strict means strict:**
  Spectic models can only be constructed with the types you declare—no silent auto-coercion of dicts or primitives into nested models. This ensures that bugs and mismatched data structures surface immediately, not later as silent failures

- 👀 **parsing is explicit:**
  Whenever you want to go from untyped data (like dict/json, user input, or cli config) to a spectic model, you use explicit parsing functions (`fromdict`, `fromjson`, etc). You choose when and how normalization/coercion happens—never by accident

- 🏎️ **validation is thorough, but stays out of your way:**
  Field-level constraints and spec-level (model) rules are always enforced at construction. Spec-level rules are designed for expressing invariants and dependencies *across fields*—not just single-attribute assertions, but real business/logic

- 🧩 **bare and composable:**
  Spectic classes are plain, attrs-like models—no clutter, no hidden magic methods. All helpers for parsing, serializing, or checking are regular functions, not class mixins or hidden metaclasses

- ⚡️ **performance should be a baseline, not a bonus:**
  Spectic is designed on msgspec for blazing validation and serialization speed, but never at the cost of clarity, correctness, or control.
  If you need runtime performance for data modeling, spectic delivers—without any “pay for magic” complexity tax
