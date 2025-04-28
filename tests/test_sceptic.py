import pytest

from spectic import field, fromdict, rule, spec, this
from spectic.types import ClosedUnitInterval, NonEmptyStr, PositiveInt


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

    rule(this.trust > this.threshold, "experiment trust must exceed threshold")
    rule(
        this.owner.age >= this.attempts,
        "owner's age must be at least equal to attempts",
    )


def test_spec_rule_multi_field_valid():
    exp = Experiment(
        title="Alpha",
        owner=User(name="bob", age=20),
        trust=0.9,
        attempts=5,
        threshold=0.4,
    )
    assert exp.trust > exp.threshold
    assert exp.owner.age >= exp.attempts


def test_spec_rule_multi_field_invalid():
    with pytest.raises(ValueError, match="trust must exceed threshold"):
        Experiment(
            title="Alpha",
            owner=User(name="bob", age=20),
            trust=0.3,
            attempts=5,
            threshold=0.4,
        )
    with pytest.raises(
        ValueError, match="owner's age must be at least equal to attempts"
    ):
        Experiment(
            title="Alpha",
            owner=User(name="bob", age=2),
            trust=0.6,
            attempts=5,
            threshold=0.3,
        )


def test_fromdict_helpers():
    data = {
        "title": "new exp",
        "owner": {"name": "lana", "age": 10},
        "trust": 0.8,
        "attempts": 6,
        "threshold": 0.4,
    }
    exp = fromdict(Experiment, data)
    assert isinstance(exp, Experiment)
    assert isinstance(exp.owner, User)


def test_strict_construction():
    # Passing a dict for owner won't work
    with pytest.raises(TypeError):
        Experiment(
            title="fail exp",
            owner={"name": "fail", "age": 1},
            trust=0.8,
            attempts=2,
            threshold=0.1,
        )
