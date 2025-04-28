from typing import Annotated

import msgspec


# -----------------------------------------------------------------------------
# Numeric Types

PositiveInt = Annotated[int, msgspec.Meta(gt=0)]
NonNegativeInt = Annotated[int, msgspec.Meta(ge=0)]
NegativeInt = Annotated[int, msgspec.Meta(lt=0)]
NonPositiveInt = Annotated[int, msgspec.Meta(le=0)]

PositiveFloat = Annotated[float, msgspec.Meta(gt=0)]
NonNegativeFloat = Annotated[float, msgspec.Meta(ge=0)]
NegativeFloat = Annotated[float, msgspec.Meta(lt=0)]
NonPositiveFloat = Annotated[float, msgspec.Meta(le=0)]

# -----------------------------------------------------------------------------
# Common interval types for [0,1] and (0,1):
ClosedUnitInterval = Annotated[float, msgspec.Meta(ge=0, le=1)]  # [0,1]
OpenUnitInterval = Annotated[float, msgspec.Meta(gt=0, lt=1)]  # (0,1)
LeftOpenUnitInterval = Annotated[float, msgspec.Meta(gt=0, le=1)]  # (0,1]
RightOpenUnitInterval = Annotated[float, msgspec.Meta(ge=0, lt=1)]  # [0,1)

# -----------------------------------------------------------------------------
# String Types

NonEmptyStr = Annotated[str, msgspec.Meta(pattern=r"^.*[^ ].*$")]
r"""str restricted to non-empty pattern ^.*[^ ].*$"""

EmailStr = Annotated[str, msgspec.Meta(pattern=r"^[^@ ]+@[^@ ]+\.[^@ ]+$")]
r"str restricted to the email pattern ^[^@ ]+@[^@ ]+\.[^@ ]+$"

HexStr = Annotated[str, msgspec.Meta(pattern=r"^[0-9A-Fa-f]+$")]
