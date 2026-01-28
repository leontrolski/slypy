from __future__ import annotations

import decimal
import enum
from typing import Annotated, Callable, ClassVar, Literal, Optional, Protocol, Self
from slypy import converters, metatypes as m
from slypy.typeshed import builtins


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
    class_var: ClassVar[int]
    bool_: bool
    literal: Literal["one", "two"]
    literal_enum: Literal[MyEnum.A, MyEnum.B]
    int_or_none: int | None
    optional: Annotated[Optional[float], "Blergg"]
    decimal_: decimal.Decimal
    none: None
    object_: Bar
    array_of_objects: list[Bar]
    recursive: Recursive
    union_array: list[int | None]
    function: Callable[[int], int]

    def method(self, a: int) -> str: ...  # type: ignore

    @classmethod
    def class_method(cls, b: int) -> Self: ...  # type: ignore

    @staticmethod
    def static_method(c: int) -> str: ...  # type: ignore


def test_converters_function() -> None:
    r = m.Registry()
    int_name = m.assert_name(converters.convert_and_add(r, builtins.int))

    name = m.assert_name(converters.convert_and_add(r, f))
    assert name == m.Name("test_converters->f")
    assert r.get(name) == m.Fn(
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
                t=m.Unknown(),
            ),
        ),
        returns=int_name,
    )

    name = m.assert_name(converters.convert_and_add(r, g))
    assert name == m.Name("test_converters->g")
    assert r.get(name) == m.Fn(
        name=name,
        parameters=(),
        returns=m.Unknown(),
    )


def test_converters_cls() -> None:
    r = m.Registry()
    name = m.assert_name(converters.convert_and_add(r, MyClass))
    assert r.get(name) == m.Class(
        m.Name("test_converters->MyClass"),
        (m.Name("builtins->object"),),
        {
            "class_var": m.ClassVar(m.Name("builtins->int")),
            "bool_": m.Name("builtins->bool"),
            "int_or_none": m.Union(m.Name("builtins->int"), m.Name("builtins->NoneType")),
            "optional": m.Union(m.Name("builtins->float"), m.Name("builtins->NoneType")),
            "decimal_": m.Name("decimal->Decimal"),
            "none": m.Name("builtins->NoneType"),
            "object_": m.Name("test_converters->Bar"),
            "array_of_objects": m.Bound(
                m.Name("builtins->list"),
                (m.Name("test_converters->Bar"),),
            ),
            "recursive": m.Name("test_converters->Recursive"),
            "literal": m.Union(m.Literal("one"), m.Literal("two")),
            "literal_enum": m.Union(
                m.Literal(m.EnumValue(converters.to_name(MyEnum), "A", "a")),
                m.Literal(m.EnumValue(converters.to_name(MyEnum), "B", "b")),
            ),
            "union_array": m.Bound(
                m.Name("builtins->list"),
                (m.Union(m.Name("builtins->int"), m.Name("builtins->NoneType")),),
            ),
            "function": m.Fn(
                position=None,
                name=None,
                parameters=(
                    m.Parameter(
                        position=None,
                        kind=m.ParameterKind.POSITIONAL_ONLY,
                        name=None,
                        t=m.Name("builtins->int"),
                    ),
                ),
                returns=m.Name("builtins->int"),
            ),
            "method": m.Method(
                m.Fn(
                    name=m.Name("test_converters->MyClass.method"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.Unknown(),
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
                                t=m.Unknown(),
                            ),
                            m.Parameter(
                                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                                name="b",
                                t=converters.to_name(builtins.int),
                            ),
                        ),
                        returns=m.Self(),
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

    name = m.assert_name(converters.convert_and_add(r, Recursive))
    assert r.get(name) == m.Class(
        m.Name("test_converters->Recursive"),
        (m.Name("builtins->object"),),
        {
            "children": m.Bound(
                converters.to_name(list),
                (m.Name("test_converters->Recursive"),),
            ),
            "parent": m.Union(m.Name("test_converters->Recursive"), converters.to_name(type(None))),
            "z": converters.to_name(int),
        },
    )


class MyProtocol(Protocol):
    x: int

    @property
    def y(self) -> str: ...


def test_converters_protocol() -> None:
    r = m.Registry()
    name = m.assert_name(converters.convert_and_add(r, MyProtocol))
    assert r.get(name) == m.Protocol(
        m.Name("test_converters->MyProtocol"),
        (),
        {
            "x": m.Name("builtins->int"),
            "y": m.ReadOnly(m.Name("builtins->str")),
        },
    )
