"""
https://github.com/domdfcoding/enum_tools/blob/master/enum_tools/custom_enums.py
"""

from enum import Enum, EnumMeta
from typing import Any, Type

__all__ = [
    "MemberDirEnum",
    "IntEnum",
    "StrEnum",
    "AutoNumberEnum",
    "OrderedEnum",
    "is_enum",
]


class EnumMixin(Enum):
    """
    Base class for all enum types
    """

    @classmethod
    def to_dict(cls) -> dict:
        """
        Allow each enum to be easily converted to dict
        """
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not isinstance(v, classmethod) and not k.startswith("_")
        }

    @classmethod
    def to_list(cls) -> list:
        """
        Allow each enum to be easily converted to list
        """
        return list(map(lambda c: c.value, cls))


class MemberDirEnum(EnumMixin):
    """
    :class:`~enum.Enum` which includes attributes as well as methods.
    This will be part of the :mod:`enum` module starting with Python 3.10.
    """

    def __dir__(self):
        return super().__dir__() + [m for m in self.__dict__ if m[0] != "_"]


class IntEnum(int, EnumMixin):
    """
    :class:`~enum.Enum` where members are also (and must be) ints.
    """


class StrEnum(str, EnumMixin):
    """
    :class:`~enum.Enum` where members are also (and must be) strings.
    """

    def __str__(self) -> str:
        return self.value

    def __new__(cls, *values):  # noqa: D102
        if len(values) > 3:
            raise TypeError(f"too many arguments for str(): {values!r}")
        if len(values) == 1:
            # it must be a string
            if not isinstance(values[0], str):
                raise TypeError(f"{values[0]!r} is not a string")
        if len(values) > 1:
            # check that encoding argument is a string
            if not isinstance(values[1], str):
                raise TypeError(f"encoding must be a string, not {values[1]!r}")
            if len(values) > 2:
                # check that error's argument is a string
                if not isinstance(values[2], str):
                    raise TypeError(f"errors must be a string, not {values[2]!r}")
        value = str(*values)
        member = str.__new__(cls, value)
        member._value_ = value
        return member


class AutoNumberEnum(EnumMixin):
    """
    :class:`~enum.Enum` that automatically assigns increasing values to members.
    """

    def __new__(cls, *args, **kwargs) -> Any:  # noqa: D102
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj


class OrderedEnum(EnumMixin):
    """
    :class:`~enum.Enum` that adds ordering based on the values of its members.
    """

    # noinspection PyProtectedMember
    def __ge__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self._value_ >= other._value_
        return NotImplemented

    # noinspection PyProtectedMember
    def __gt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self._value_ > other._value_
        return NotImplemented

    # noinspection PyProtectedMember
    def __le__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self._value_ <= other._value_
        return NotImplemented

    # noinspection PyProtectedMember
    def __lt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self._value_ < other._value_
        return NotImplemented


def is_enum(obj: Type) -> bool:
    """
    Returns :py:obj:`True` if ``obj`` is an :class:`enum.Enum`.
    :param obj:
    """
    # The enum itself is subclass of EnumMeta; enum members subclass Enum
    return isinstance(obj, EnumMeta)
