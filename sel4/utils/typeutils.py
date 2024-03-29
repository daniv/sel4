from decimal import Decimal
from os import PathLike
from typing import Any
from typing import Callable as TypingCallable
from typing import Dict, Generator, List, Optional, Set, Tuple

from typing_extensions import Literal

NoneStr = Optional[str]
NoneBytes = Optional[bytes]
StrBytes = str | bytes
NoneStrBytes = Optional[StrBytes]
OptionalInt = Optional[int]
OptionalIntFloat = OptionalInt | float
OptionalIntFloatDecimal = OptionalIntFloat | Decimal
StrIntFloat = str | int | float
OptionalInt = Optional[int]
OptionalFloat = Optional[float]
OptionalIntFloat = OptionalInt | float
Number = int | float | Decimal
StrBytes = str | bytes
OptionalInt = Optional[int]
OptionalBool = Optional[bool]
DictStrAny = Dict[str, Any]
DictStrStr = Dict[str, str]
DictAny = Dict[Any, Any]
SetStr = Set[str]
ListStr = List[str]
IntStr = int | str
AnyCallable = TypingCallable[..., Any]
TupleGenerator = Generator[Tuple[str, Any], None, None]
CallableGenerator = Generator[AnyCallable, None, None]
StrPath = str | PathLike
AnyCallable = TypingCallable[..., Any]
NoArgAnyCallable = TypingCallable[[], Any]
LogLevelName = Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR"]
