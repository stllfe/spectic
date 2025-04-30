"""Exception classes for spectic."""

class SpecException(Exception):
    """Base exception for all spectic errors."""
    pass

class SpecError(SpecException):
    """Error raised when a spec validation rule fails."""
    pass

class ConversionError(SpecException):
    """Error raised when conversion between types fails."""
    pass
