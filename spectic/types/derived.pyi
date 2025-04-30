"""Type definitions for the derived types module"""

from typing import Annotated, TypeAlias

# -----------------------------------------------------------------------------
# Numeric Types

PositiveInt: TypeAlias = Annotated[int, "gt=0"]
NonNegativeInt: TypeAlias = Annotated[int, "ge=0"]
NegativeInt: TypeAlias = Annotated[int, "lt=0"]
NonPositiveInt: TypeAlias = Annotated[int, "le=0"]

PositiveFloat: TypeAlias = Annotated[float, "gt=0"]
NonNegativeFloat: TypeAlias = Annotated[float, "ge=0"]
NegativeFloat: TypeAlias = Annotated[float, "lt=0"]
NonPositiveFloat: TypeAlias = Annotated[float, "le=0"]

# -----------------------------------------------------------------------------
# Common interval types

ClosedUnitInterval: TypeAlias = Annotated[float, "ge=0,le=1"]  # [0,1]
OpenUnitInterval: TypeAlias = Annotated[float, "gt=0,lt=1"]  # (0,1)
LeftOpenUnitInterval: TypeAlias = Annotated[float, "gt=0,le=1"]  # (0,1]
RightOpenUnitInterval: TypeAlias = Annotated[float, "ge=0,lt=1"]  # [0,1)

# -----------------------------------------------------------------------------
# String Types

NonEmptyStr: TypeAlias = Annotated[str, "pattern=r'^.*[^ ].*$'"]
EmailStr: TypeAlias = Annotated[str, "pattern=r'^[^@ ]+@[^@ ]+\\.[^@ ]+$'"]
HexStr: TypeAlias = Annotated[str, "pattern=r'^[0-9A-Fa-f]+$'"]