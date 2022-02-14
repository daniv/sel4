"""
    https://github.com/invl/retry
"""
import random
import time
from functools import partial, wraps
from typing import Callable, Optional, ParamSpecArgs, ParamSpecKwargs, Tuple, Type

# sys.maxint / 2, since Python 3.2 doesn't have a sys.maxint...
from pydantic import Field, PositiveFloat, PositiveInt, validate_arguments

from sel4.utils.typeutils import AnyCallable, OptionalFloat

_MAX_WAIT = 1_073_741_823


__all__ = ["retry", "retry_call"]


def __retry_internal(
    func: Callable,
    exceptions: Type[Exception] | Tuple[Type[Exception]],
    tries=-1,
    delay=0.0,
    timeout_ms=_MAX_WAIT,
    max_delay: OptionalFloat = None,
    backoff=1.0,
    jitter=0.0,
):
    """
    Executes a function and retries it if it failed.
    :param func: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param timeout_ms: max retries delay. default: _MAX_WAIT.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :returns: the result of the func function.
    """
    _tries, _delay = tries, delay
    attempt_number = 1
    start_time = int(round(time.time() * 1000))
    while _tries:
        try:
            return func()
        except exceptions as e:
            _tries -= 1
            if not _tries:
                raise e
            delay_since_first_attempt_ms = int(round(time.time() * 1000)) - start_time
            if delay_since_first_attempt_ms > timeout_ms:
                raise e

            # LOGGER.warning('%s, retrying in %s seconds... (attempt #%d)', e, _delay, attempt_number)

            time.sleep(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)
            attempt_number += 1


@validate_arguments
def retry(
    exceptions: Type[Exception]
    | Tuple[Type[Exception]] = Field(default_factory=Exception),
    tries: int = Field(default=-1),
    delay: float = Field(default=0, ge=0),
    max_delay: OptionalFloat = Field(default=None, ge=0.0),
    timeout_ms: PositiveInt = Field(default=_MAX_WAIT),
    backoff: PositiveFloat = Field(default=1.0),
    jitter: PositiveFloat = Field(default=0.0),
):
    """Returns a retry decorator.

    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param timeout_ms: max retries delay. default: _MAX_WAIT.
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :returns: a retry decorator.
    """

    @decorator
    def retry_decorator(func, *f_args: ParamSpecArgs, **f_kwargs: ParamSpecKwargs):
        args = f_args if f_args else list()
        kwargs = f_kwargs if f_kwargs else dict()
        return __retry_internal(
            partial(func, *args, **kwargs),
            exceptions=exceptions,
            tries=tries,
            delay=delay,
            max_delay=max_delay,
            timeout_ms=timeout_ms,
            backoff=backoff,
            jitter=jitter,
        )

    return retry_decorator


def decorator(caller):
    """Turns caller into a decorator.
    Unlike decorator module, function signature is not preserved.
    :param caller: caller(f, *args, **kwargs)
    """

    def decor(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            return caller(f, *args, **kwargs)

        return wrapper

    return decor


# class RetryError(Exception):
#     """
#     A RetryError encapsulates the last Attempt instance right before giving up.
#     """
#
#     def __init__(self, last_attempt):
#         self.last_attempt = last_attempt
#
#     def __str__(self):
#         return f"RetryError[{self.last_attempt}]"


@validate_arguments(config=dict(arbitrary_types_allowed=True))
def retry_call(
    func: AnyCallable,
    f_args: Optional[ParamSpecArgs] = None,
    f_kwargs: Optional[ParamSpecKwargs] = None,
    exceptions: Type[Exception] | Tuple[Type[Exception]] = Exception,
    tries: int = -1,
    delay: float = 0,
    max_delay: OptionalFloat = None,
    backoff=1.0,
    jitter=0.0,
):
    """
    Calls a function and re-executes it if it failed.

    :param func: the function to execute.
    :param f_args: the positional arguments of the function to execute.
    :param f_kwargs: the named arguments of the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :returns: the result of the f function.
    """
    args = f_args if f_args else list()
    kwargs = f_kwargs if f_kwargs else dict()
    return __retry_internal(
        partial(func, *args, **kwargs),
        exceptions,
        tries,
        delay,
        _MAX_WAIT,
        max_delay,
        backoff,
        jitter,
    )
