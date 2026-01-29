from typing import Literal
from slypy import check, converters, metatypes as m

import pytest
from slypy.typeshed import builtins


class A: ...


class B: ...


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
    ],
)
def test_issubtype_e2e(a: m.MetaType, b: m.MetaType, expected: bool) -> None:
    r = m.Registry()
    s = converters.Scope()
    converters.convert_and_add(r, s, builtins.int)
    converters.convert_and_add(r, s, builtins.bool)
    a_meta = converters.convert_and_add(r, s, a)
    b_meta = converters.convert_and_add(r, s, b)
    actual = check.issubtype(r, a_meta, b_meta)
    assert (actual is None) == expected
