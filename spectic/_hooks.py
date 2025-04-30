from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from datetime import date
from datetime import datetime
from datetime import time
from decimal import Decimal
from functools import partial
from os import PathLike
from pathlib import Path
from pathlib import PurePath
from re import Pattern
from typing import Any, Callable, Mapping, TypeAlias, TypeVar, overload
from uuid import UUID

import msgspec

from msgspec import UNSET
from msgspec import UnsetType

from .exceptions import SpecException
from .types.secrets import SecretBytes
from .types.secrets import SecretStr
from .utils import get_origin_or_inner_type


PathType: TypeAlias = Path | PathLike | str
TypeDecodersSequence: TypeAlias = Sequence[tuple[Callable[[Any], bool], Callable[[Any, Any], Any]]]  # noqa
TypeEncodersMap: TypeAlias = Mapping[Any, Callable[[Any], Any]]
Serializer: TypeAlias = Callable[[Any], Any]

__all__ = (
  "decode_json",
  "default_deserializer",
  "default_serializer",
  "encode_json",
  "get_serializer",
)

T = TypeVar("T")

DEFAULT_TYPE_ENCODERS: TypeEncodersMap = {
  Path: str,
  PurePath: str,
  datetime: lambda val: val.isoformat(),
  date: lambda val: val.isoformat(),
  time: lambda val: val.isoformat(),
  deque: list,
  Decimal: lambda val: int(val) if val.as_tuple().exponent >= 0 else float(val),
  Pattern: lambda val: val.pattern,
  SecretBytes: lambda val: val.get_obscured().decode("utf-8"),
  SecretStr: lambda val: val.get_obscured(),
  # support subclasses of stdlib types, If no previous type matched, these will be
  # the last type in the mro, so we use this to (attempt to) convert a subclass into
  # its base class. # see https://github.com/jcrist/msgspec/issues/248
  # and https://github.com/litestar-org/litestar/issues/1003
  str: str,
  int: int,
  float: float,
  set: set,
  frozenset: frozenset,
  bytes: bytes,
}


def default_serializer(value: Any, type_encoders: Mapping[Any, Callable[[Any], Any]] | None = None) -> Any:
  """Transform values non-natively supported by ``msgspec``

  Args:
      value: A value to serialized
      type_encoders: Mapping of types to callables to transforming types
  Returns:
      A serialized value
  Raises:
      TypeError: if value is not supported
  """
  type_encoders = {**DEFAULT_TYPE_ENCODERS, **(type_encoders or {})}

  for base in value.__class__.__mro__[:-1]:
    try:
      encoder = type_encoders[base]
      return encoder(value)
    except KeyError:
      continue

  raise TypeError(f"Unsupported type: {type(value)!r}")


def default_deserializer(
  target_type: Any, value: Any, type_decoders: TypeDecodersSequence | None = None
) -> Any:  # pragma: no cover
  """Transform values non-natively supported by ``msgspec``

  Args:
      target_type: Encountered type
      value: Value to coerce
      type_decoders: Optional sequence of type decoders

  Returns:
      A ``msgspec``-supported type
  """

  try:
    if isinstance(value, target_type):
      return value
  except TypeError as exc:
    # we might get a TypeError here if target_type is a subscribed generic. For
    # performance reasons, we let this happen and only unwrap this when we're
    # certain this might be the case
    if (origin := get_origin_or_inner_type(target_type)) is not None:
      target_type = origin
      if isinstance(value, target_type):
        return value
    else:
      raise exc

  if type_decoders:
    for predicate, decoder in type_decoders:
      if predicate(target_type):
        return decoder(target_type, value)

  if issubclass(target_type, (Path, PurePath, UUID)):
    return target_type(value)

  if issubclass(target_type, SecretBytes) and isinstance(value, (bytes, str)):
    return SecretBytes(value.encode("utf-8") if isinstance(value, str) else value)

  if issubclass(target_type, SecretStr) and isinstance(value, str):
    return SecretStr(value)

  raise TypeError(f"Unsupported type: {type(value)!r}")


_msgspec_json_encoder = msgspec.json.Encoder(enc_hook=default_serializer)
_msgspec_json_decoder = msgspec.json.Decoder(dec_hook=default_deserializer)


def encode_json(value: Any, serializer: Callable[[Any], Any] | None = None) -> bytes:
  """Encode a value into JSON.

  Args:
      value: Value to encode
      serializer: Optional callable to support non-natively supported types.

  Returns:
      JSON as bytes

  Raises:
      SpecException: If error encoding ``obj``.
  """
  try:
    return msgspec.json.encode(value, enc_hook=serializer) if serializer else _msgspec_json_encoder.encode(value)
  except (TypeError, msgspec.EncodeError) as msgspec_error:
    raise SpecException(str(msgspec_error)) from msgspec_error


@overload
def decode_json(value: str | bytes, strict: bool = ...) -> Any: ...


@overload
def decode_json(value: str | bytes, type_decoders: TypeDecodersSequence | None, strict: bool = ...) -> Any: ...


@overload
def decode_json(value: str | bytes, target_type: type[T], strict: bool = ...) -> T: ...


@overload
def decode_json(
  value: str | bytes,
  target_type: type[T],
  type_decoders: TypeDecodersSequence | None,
  strict: bool = ...,
) -> T: ...


def decode_json(  # type: ignore[misc]
  value: str | bytes,
  target_type: type[T] | UnsetType = UNSET,  # pyright: ignore
  type_decoders: TypeDecodersSequence | None = None,
  strict: bool = True,
) -> Any:
  """Decode a JSON string/bytes into an object.

  Args:
      value: Value to decode
      target_type: An optional type to decode the data into
      type_decoders: Optional sequence of type decoders
      strict: Whether type coercion rules should be strict. Setting to False enables
          a wider set of coercion rules from string to non-string types for all values

  Returns:
      An object

  Raises:
      SpecException: If error decoding ``value``.
  """
  try:
    if target_type is UNSET:
      return _msgspec_json_decoder.decode(value)
    return msgspec.json.decode(
      value,
      dec_hook=partial(
        default_deserializer,
        type_decoders=type_decoders,
      ),
      type=target_type,
      strict=strict,
    )
  except msgspec.DecodeError as msgspec_error:
    raise SpecException(str(msgspec_error)) from msgspec_error


def get_serializer(type_encoders: TypeEncodersMap | None = None) -> Serializer:
  """Get the serializer for the given type encoders."""

  if type_encoders:
    return partial(default_serializer, type_encoders=type_encoders)

  return default_serializer
