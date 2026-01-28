from __future__ import annotations

import decimal
import enum
from pathlib import Path
from typing import Literal, Self
from slypy import converters, metatypes as m, typeshed
from slypy.typeshed import builtins

TESTS = Path(__file__).parent.resolve()


def f(x: int, *, y) -> int: ...  # type: ignore
def g(): ...  # type: ignore


class MyEnum(enum.Enum):
    A = "a"
    B = "b"
    C = "c"


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
    bool_: bool
    literal: Literal["one", "two"]
    literal_enum: Literal[MyEnum.A, MyEnum.B]
    int_or_none: int | None
    decimal_: decimal.Decimal
    none: None
    object_: Bar
    array_of_objects: list[Bar]
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

    int_name = m.assert_name(c.add(builtins.int))

    name = m.assert_name(c.add(f))
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

    name = m.assert_name(c.add(g))
    assert name == m.Name("test_converters->g")
    assert registry.get(name) == m.Fn(
        name=name,
        parameters=(),
        returns=m.unknown.name,
    )


def test_converters_cls() -> None:
    registry = m.Registry()
    c = converters.Context([TESTS, typeshed.PATH], registry)

    name = m.assert_name(c.add(MyClass))
    assert registry.get(name) == m.Class(
        name,
        (m.object.name,),
        {
            "bool_": m.Name("builtins->bool"),
            "int_or_none": m.Union(m.Name("builtins->int"), m.Name("builtins->NoneType")),
            "decimal_": m.Name("decimal->Decimal"),
            "none": m.Name("builtins->NoneType"),
            "object_": m.Name("test_converters->Bar"),
            "array_of_objects": m.Bound(
                m.Name("builtins->list"),
                (m.Name("test_converters->Bar"),),
            ),
            "literal": m.Union(m.Literal("one"), m.Literal("two")),
            "literal_enum": m.Union(
                m.Literal(m.EnumValue(converters.to_name(MyEnum), "A", "a")),
                m.Literal(m.EnumValue(converters.to_name(MyEnum), "B", "b")),
            ),
            "method": m.Method(
                m.Fn(
                    name=m.Name("test_converters->MyClass.method"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.unknown.name,
                        ),
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="a",
                            t=converters.to_name(builtins.int),
                        ),
                    ),
                    returns=converters.to_name(builtins.str),
                )
            ),
            "class_method": m.ClassVar(
                m.Method(
                    m.Fn(
                        name=m.Name("test_converters->MyClass.class_method"),
                        parameters=(
                            m.Parameter(
                                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                                name="cls",
                                t=m.unknown.name,
                            ),
                            m.Parameter(
                                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                                name="b",
                                t=converters.to_name(builtins.int),
                            ),
                        ),
                        returns=converters.to_name(Self),
                    )
                )
            ),
            "static_method": m.Fn(
                name=m.Name("test_converters->MyClass.static_method"),
                parameters=(
                    m.Parameter(
                        kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                        name="c",
                        t=converters.to_name(builtins.int),
                    ),
                ),
                returns=converters.to_name(builtins.str),
            ),
        },
    )
