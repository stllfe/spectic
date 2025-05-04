import json
import pytest
import msgspec

try:
    import yaml
except ImportError:
    yaml = None

from spectic import Rule
from spectic import asdict
from spectic import asjson
from spectic import asyaml
from spectic import check
from spectic import field
from spectic import fromdict
from spectic import fromjson
from spectic import fromyaml
from spectic import rule
from spectic import spec
from spectic.types import ClosedUnitInterval
from spectic.types import NonEmptyStr
from spectic.types import PositiveInt


@spec
class User:
  name: NonEmptyStr
  age: PositiveInt


@spec
class Person:
  name: str = field(min_length=1, coerce=True)
  age: int = field(ge=0, coerce=True)


@spec
class Experiment:
  title: NonEmptyStr
  owner: User
  trust: ClosedUnitInterval
  attempts: PositiveInt
  threshold: float = field(ge=0, le=1)

  # Using method approach
  @rule
  def validate_trust(self):
    if self.trust <= self.threshold:
      raise ValueError("experiment trust must exceed threshold")

  # Using method approach for age validation too
  @rule
  def validate_age(self):
    if self.owner.age < self.attempts:
      raise ValueError("owner's age must be at least equal to attempts")


def test_spec_rule_with_lambdas_valid():
  exp = Experiment(
    title="Alpha",
    owner=User(name="bob", age=20),
    trust=0.9,
    attempts=5,
    threshold=0.4,
  )
  assert exp.trust > exp.threshold
  assert exp.owner.age >= exp.attempts


def test_spec_rule_with_lambdas_invalid():
  # Test that creating an experiment with trust < threshold fails
  with pytest.raises(ValueError, match="trust must exceed threshold"):
    Experiment(
      title="Alpha",
      owner=User(name="bob", age=20),
      trust=0.3,
      attempts=5,
      threshold=0.4,
    )

  # Test that creating an experiment with owner.age < attempts fails
  with pytest.raises(ValueError, match="owner's age must be at least equal to attempts"):
    Experiment(
      title="Alpha",
      owner=User(name="bob", age=2),
      trust=0.6,
      attempts=5,
      threshold=0.3,
    )


def test_field_level_rule():
  @spec
  class Product:
    name: str
    price: float = field(gt=0, rule=lambda price: price < 1000, message="Price must be less than 1000")

  # Valid price
  product = Product(name="Widget", price=99.99)
  assert product.price == 99.99

  # Invalid price - too high
  with pytest.raises(ValueError, match="Price must be less than 1000"):
    Product(name="Expensive Widget", price=1500)


def test_lambda_rules():
  @spec
  class Order:
    items: int = field(gt=0)
    total: float = field(gt=0)
    discount: float = field(ge=0, le=1)

    # Direct lambda rule in class body
    rule(lambda self: self.total > 0, "Order total must be positive")
    rule(lambda self: self.items * self.discount < self.total, "Discount cannot exceed total value")

  # Valid order
  order = Order(items=5, total=100.0, discount=0.1)
  assert order.total == 100.0

  # Invalid order - discount too high
  with pytest.raises(ValueError, match="Discount cannot exceed total value"):
    Order(items=10, total=5.0, discount=0.9)


def test_field_coercion():
  # String should be coerced to int for age
  person = Person(name="Alice", age="30")
  assert person.age == 30
  assert isinstance(person.age, int)

  # Test with a non-coercible value
  with pytest.raises(msgspec.ValidationError):
    Person(name="Bob", age="not_a_number")

  # Test that coercion is not applied if not needed
  person2 = Person(name="Charlie", age=25)
  assert person2.age == 25


def test_field_no_coercion():
  @spec
  class StrictPerson:
    name: str
    age: int

  # Type checking should fail without coercion
  with pytest.raises(msgspec.ValidationError):
    StrictPerson(name="Dave", age="40")


def test_check_decorator():
  @check
  def calculate_area(width: PositiveInt, height: PositiveInt) -> float:
    return width * height

  # Valid arguments
  assert calculate_area(5, 10) == 50

  # Valid arguments with type coercion
  assert calculate_area("5", "10") == 50

  # Invalid arguments - negative numbers don't fit PositiveInt
  try:
    calculate_area(-5, 10)
    pytest.fail("Should have raised an exception for negative number")
  except (TypeError, ValueError, msgspec.ValidationError):
    # Accept any of these exceptions
    pass

  # Invalid string that can't be converted
  try:
    calculate_area("not_a_number", 10)
    pytest.fail("Should have raised an exception for invalid string")
  except (TypeError, ValueError):
    # Accept any of these exceptions
    pass


def test_check_with_custom_types():
  @check
  def greet_user(user: User) -> str:
    return f"Hello, {user.name}! You are {user.age} years old."

  # Valid user object
  user = User(name="Eva", age=25)
  assert greet_user(user) == "Hello, Eva! You are 25 years old."

  # Invalid user object (should not coerce dict to User)
  try:
    greet_user({"name": "Frank", "age": 30})
    pytest.fail("Should have raised an exception for dict instead of User")
  except (TypeError, ValueError, msgspec.ValidationError):
    # Accept any of these exceptions
    pass


def test_check_with_nested_objects():
  @check
  def get_experiment_summary(exp: Experiment) -> str:
    return f"{exp.title}: {exp.owner.name} runs {exp.attempts} attempts with {exp.trust} trust"

  # Valid experiment
  exp = Experiment(
    title="Beta",
    owner=User(name="Grace", age=40),
    trust=0.7,
    attempts=3,
    threshold=0.5,
  )
  assert get_experiment_summary(exp) == "Beta: Grace runs 3 attempts with 0.7 trust"


def test_asdict():
  user = User(name="Alice", age=30)
  data = asdict(user)
  assert isinstance(data, dict)
  assert data["name"] == "Alice"
  assert data["age"] == 30


def test_asjson():
  user = User(name="Bob", age=25)
  json_bytes = asjson(user)
  assert isinstance(json_bytes, bytes)
  data = json.loads(json_bytes)
  assert data["name"] == "Bob"
  assert data["age"] == 25

  # Test with indent
  json_bytes_indented = asjson(user, indent=2)
  assert b"  " in json_bytes_indented


def test_fromjson():
  json_str = '{"name": "Charlie", "age": 35}'
  user = fromjson(json_str, User)
  assert isinstance(user, User)
  assert user.name == "Charlie"
  assert user.age == 35


@pytest.mark.skipif(yaml is None, reason="pyyaml not installed")
def test_asyaml():
  user = User(name="Dave", age=40)
  yaml_str = asyaml(user)
  assert isinstance(yaml_str, str)
  data = yaml.safe_load(yaml_str)
  assert data["name"] == "Dave"
  assert data["age"] == 40


@pytest.mark.skipif(yaml is None, reason="pyyaml not installed")
def test_fromyaml():
  yaml_str = """
  name: Eve
  age: 45
  """
  user = fromyaml(yaml_str, User)
  assert isinstance(user, User)
  assert user.name == "Eve"
  assert user.age == 45


def test_nested_conversion():
  # create an experiment
  exp = Experiment(
    title="Test Experiment",
    owner=User(name="Frank", age=50),
    trust=0.8,
    attempts=4,
    threshold=0.6,
  )

  # convert to dict and verify structure
  data = asdict(exp)
  assert data["title"] == "Test Experiment"
  assert isinstance(data["owner"], dict)
  assert data["owner"]["name"] == "Frank"

  # convert to JSON and back
  json_bytes = asjson(exp)
  exp2 = fromjson(json_bytes, Experiment)
  assert isinstance(exp2, Experiment)
  assert exp2.title == exp.title
  assert exp2.owner.name == exp.owner.name

  # test yaml conversion if available
  if yaml is not None:
    # convert to YAML and back
    yaml_str = asyaml(exp)
    exp3 = fromyaml(yaml_str, Experiment)
    assert isinstance(exp3, Experiment)
    assert exp3.title == exp.title
    assert exp3.trust == exp.trust
