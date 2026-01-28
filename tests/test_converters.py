from __future__ import annotations

from pathlib import Path
from typing import Self
from slypy import converters, metatypes as m, typeshed
from slypy.typeshed import builtins

TESTS = Path(__file__).parent.resolve()


def f(x: int, *, y) -> int: ...  # type: ignore
def g(): ...  # type: ignore


class Bar:
    x: str
    y: int


class Recursive:
    z: int
    parent: Recursive | None = None
    children: list[Recursive] = []


class Baz:
    a: str
    b: float


class MyClass:
    # literal: Literal["one", "two"]
    # bool_: bool
    # int_or_none: int | None
    # decimal_: decimal.Decimal
    # none: None
    # object_: Bar
    # array_of_objects: list[Bar]
    # recursive: Recursive
    # union_none: Bar | Baz | None
    # union_array: list[Bar | Baz | None]
    # function: Callable[[int], int]

    def method(self, a: int) -> str: ...  # type: ignore

    @classmethod
    def class_method(cls, b: int) -> Self: ...  # type: ignore

    @staticmethod
    def static_method(c: int) -> str: ...  # type: ignore


def test_converters_function() -> None:
    registry = m.Registry()
    c = converters.Context([TESTS, typeshed.PATH], registry)

    int_name = c.add(builtins.int)

    name = c.add(f)
    assert name == m.Name("test_converters->f")
    assert registry.get(name) == m.Fn(
        name=name,
        parameters=(
            m.Parameter(
                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                name="x",
                t=int_name,
            ),
            m.Parameter(
                kind=m.ParameterKind.KEYWORD_ONLY,
                name="y",
                t=m.unknown.name,
            ),
        ),
        returns=int_name,
    )

    name = c.add(g)
    assert name == m.Name("test_converters->g")
    assert registry.get(name) == m.Fn(
        name=name,
        parameters=(),
        returns=m.unknown.name,
    )


def test_converters_cls() -> None:
    registry = m.Registry()
    c = converters.Context([TESTS, typeshed.PATH], registry)

    name = c.add(builtins.bool)
    assert registry.get(name) == m.Class(name, (m.object.name,), {})

    name = c.add(builtins.int)
    assert registry.get(name) == m.Class(name, (m.object.name,), {})

    name = c.add(MyClass)
