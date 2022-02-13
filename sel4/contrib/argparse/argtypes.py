"""
https://github.com/eerimoq/argparse_addons/blob/master/argparse_addons.py
"""

import argparse
from typing import (
    Union,
    Any
)

import pydantic
from pydantic import validators
from rich import get_console

from sel4.utils.typeutils import OptionalInt


class PositiveIntArgType:
    def __init__(self):
        class PositiveIntValidator(pydantic.BaseModel):
            positive_int: pydantic.PositiveInt

        self.validator = PositiveIntValidator

    def __call__(self, v: Any) -> int:
        try:
            c = self.validator(positive_int=v)
            return c.positive_int
        except pydantic.ValidationError as e:
            get_console().print_exception()
            raise ValueError(str(e))

    def __repr__(self) -> str:
        return '[PositiveInt type]'


class ConstrainedIntArgType:
    def __init__(
            self, *,
            strict: bool = False, gt: int = None, ge: int = None, lt: int = None, le: int = None,
            multiple_of: int = None
    ):
        class ConstrainedIntValidator(pydantic.BaseModel):
            constrained_int: pydantic.ConstrainedInt = pydantic.conint(
                strict=strict, gt=gt, ge=ge, lt=lt, le=le, multiple_of=multiple_of
            )

        self.validator = ConstrainedIntValidator

    def __call__(self, v: Any) -> int:
        try:
            c = self.validator(positive_int=v)
            return c.constrained_int
        except pydantic.ValidationError as e:
            get_console().print_exception()
            raise ValueError(str(e))

    def __repr__(self) -> str:
        return '[ConstrainedIntArgType type]'


class ConstrainedNumberMeta:
    def __init__(self, *, gt: OptionalInt, ge: OptionalInt, lt: OptionalInt, le: OptionalInt):
        if gt is not None and ge is not None:
            raise argparse.ArgumentTypeError('bounds gt and ge cannot be specified at the same time')
        if lt is not None and le is not None:
            raise argparse.ArgumentTypeError('bounds lt and le cannot be specified at the same time')


class ConstrainedIntType(ConstrainedNumberMeta):

    def __init__(
            self, *,
            strict: bool = False,
            gt: OptionalInt = None, ge: OptionalInt = None,
            lt: OptionalInt = None, le: OptionalInt = None,
            multiple_of: OptionalInt = None
    ):
        super().__init__(gt=gt, ge=ge, lt=lt, le=le)
        self.strict = strict
        self.gt = gt
        self.ge = ge
        self.lt = lt
        self.le = le
        self.multiple_of = multiple_of

    def __call__(self, v: Union[str, int]) -> Union[int, None]:
        validator = validators.strict_int_validator if self.strict else validators.int_validator
        value = validator(v)
        return value

    def __repr__(self) -> str:
        return '[integer type]'
