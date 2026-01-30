from typing import Literal, Callable, Protocol, cast
from slypy import check, converters, metatypes as m

import pytest
from slypy.typeshed import builtins


class A: ...


class B: ...


Callable1 = Callable[[int], int]
Callable2 = Callable[[int, int], int]
CallableInt = Callable[[int], int]
CallableIntOrStr = Callable[[int | str], int]
CallableToInt = Callable[[], int]
CallableToIntOrStr = Callable[[], int | str]


class Callable2Name(Protocol):
    def __call__(self, a: int, b: int, /) -> int: ...


class Callable2NameDefault(Protocol):
    def __call__(self, a: int, b: int, c: int = 4, /) -> int: ...


class Callable2ab(Protocol):
    def __call__(self, a: int, b: int) -> int: ...


class Callable2bc(Protocol):
    def __call__(self, b: int, c: int) -> int: ...


class Callable1Kwargs(Protocol):
    def __call__(self, a: int, **kwargs: int) -> int: ...


class CallableKwargs(Protocol):
    def __call__(self, **kwargs: int) -> int: ...


class CallableKwargsName(Protocol):
    def __call__(self, *, a: int, **kwargs: int) -> int: ...


class CallableOptional(Protocol):
    def __call__(self, x: int, y: int = 1) -> int: ...


class CallableRequired(Protocol):
    def __call__(self, x: int) -> int: ...


class CallableArgs(Protocol):
    def __call__(self, *args: int) -> int: ...


class CallableTwoArgs(Protocol):
    def __call__(self, x: int, y: int) -> int: ...


# Check everything aligns with mypy, TBH, I'm not totally confident mypy is correct
# result: b = cast(a, None)
_true: int | str = cast(int, None)
_false: int = cast(int | str, None)  # type: ignore[assignment]
_true_1: Callable2Name = cast(Callable2, None)
_true_2: Callable2 = cast(Callable2Name, None)
_false_3: Callable2ab = cast(Callable2bc, None)  # type: ignore[assignment]
_false_4: CallableKwargs = cast(Callable1Kwargs, None)  # type: ignore[assignment]
_false_5: Callable1Kwargs = cast(CallableKwargs, None)  # type: ignore[assignment]
_false_6: CallableKwargs = cast(CallableKwargsName, None)  # type: ignore[assignment]
_true_7: CallableKwargsName = cast(CallableKwargs, None)
_true_8: Callable2Name = cast(Callable2NameDefault, None)
_false_9: Callable2NameDefault = cast(Callable2Name, None)  # type: ignore[assignment]
_true_10: CallableToIntOrStr = cast(CallableToInt, None)
_false_11: CallableToInt = cast(CallableToIntOrStr, None)  # type: ignore[assignment]
_false_12: CallableIntOrStr = cast(CallableInt, None)  # type: ignore[assignment]
_true_13: CallableInt = cast(CallableIntOrStr, None)
_false_14: CallableOptional = cast(CallableRequired, None)  # type: ignore[assignment]
_true_15: CallableRequired = cast(CallableOptional, None)
_false_16: CallableTwoArgs = cast(CallableArgs, None)  # type: ignore[assignment]
_false_17: CallableArgs = cast(CallableTwoArgs, None)  # type: ignore[assignment]
_true_18: Callable2Name = cast(CallableArgs, None)


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (A, A, True),
        (A, B, False),
        (Literal[1], int, True),
        (Literal[1], Literal[1], True),
        (Literal[1], Literal[1, 2], True),
        (Literal[1, 2], Literal[1, 2], True),
        (Literal[1, 2], Literal[1, 2, 4], True),
        (Literal[1, 2, 4], Literal[1, 2], False),
        (Literal[1, 2], Literal[1], False),
        (int, Literal[1], False),
        (int, int | str, True),
        (int | str, int, False),
        (Callable1, Callable2, False),
        (Callable2, Callable1, False),
        (Callable2, Callable2Name, True),
        (Callable2Name, Callable2, True),
        (Callable2bc, Callable2ab, False),
        (Callable1Kwargs, CallableKwargs, False),
        (CallableKwargs, Callable1Kwargs, False),
        # Interesting cases:
        (CallableKwargsName, CallableKwargs, False),
        (CallableKwargs, CallableKwargsName, True),
        (Callable2NameDefault, Callable2Name, True),
        (Callable2Name, Callable2NameDefault, False),
        (CallableToInt, CallableToIntOrStr, True),
        (CallableToIntOrStr, CallableToInt, False),
        (CallableInt, CallableIntOrStr, False),
        (CallableIntOrStr, CallableInt, True),
        (CallableRequired, CallableOptional, False),
        (CallableOptional, CallableRequired, True),
        (CallableArgs, CallableTwoArgs, False),
        (CallableTwoArgs, CallableArgs, False),
        (CallableArgs, Callable2Name, True),
    ],
)
def test_issubtype_e2e(a: m.MetaType, b: m.MetaType, expected: bool) -> None:
    r = m.Registry()
    s = converters.Scope()
    converters.convert_and_add(r, s, builtins.int)
    converters.convert_and_add(r, s, builtins.str)
    a_meta = converters.convert_and_add(r, s, a)
    b_meta = converters.convert_and_add(r, s, b)
    actual = check.issubtype(r, a_meta, b_meta)
    assert (actual is None) == expected
