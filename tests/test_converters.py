from __future__ import annotations

import decimal
import enum
from typing import Annotated, Callable, ClassVar, Generic, Literal, Optional, Protocol, Self, TypeVar
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


def test_function() -> None:
    r = m.Registry()
    s = converters.Scope()
    int_name = m.assert_name(converters.convert_and_add(r, s, builtins.int))

    name = m.assert_name(converters.convert_and_add(r, s, f))
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

    name = m.assert_name(converters.convert_and_add(r, s, g))
    assert name == m.Name("test_converters->g")
    assert r.get(name) == m.Fn(
        name=name,
        parameters=(),
        returns=m.Unknown(),
    )


def test_cls() -> None:
    r = m.Registry()
    s = converters.Scope()
    name = m.assert_name(converters.convert_and_add(r, s, MyClass))
    assert r.get(name) == m.Class(
        m.Name("test_converters->MyClass"),
        (m.Name("builtins->object"),),
        {
            "class_var": m.ClassVar(m.Name("builtins->int")),
            "bool_": m.Name("builtins->bool"),
            "int_or_none": m.Union.make(m.Name("builtins->int"), m.Name("builtins->NoneType")),
            "optional": m.Union.make(m.Name("builtins->float"), m.Name("builtins->NoneType")),
            "decimal_": m.Name("decimal->Decimal"),
            "none": m.Name("builtins->NoneType"),
            "object_": m.Name("test_converters->Bar"),
            "array_of_objects": m.Bound(
                m.Name("builtins->list"),
                (m.Name("test_converters->Bar"),),
            ),
            "recursive": m.Name("test_converters->Recursive"),
            "literal": m.Union.make(m.Literal.make("one"), m.Literal.make("two")),
            "literal_enum": m.Union.make(
                m.Literal.make(m.EnumValue(converters.to_name(MyEnum), "A", "a")),
                m.Literal.make(m.EnumValue(converters.to_name(MyEnum), "B", "b")),
            ),
            "union_array": m.Bound(
                m.Name("builtins->list"),
                (m.Union.make(m.Name("builtins->int"), m.Name("builtins->NoneType")),),
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

    name = m.assert_name(converters.convert_and_add(r, s, Recursive))
    assert r.get(name) == m.Class(
        m.Name("test_converters->Recursive"),
        (m.Name("builtins->object"),),
        {
            "children": m.Bound(
                converters.to_name(list),
                (m.Name("test_converters->Recursive"),),
            ),
            "parent": m.Union.make(m.Name("test_converters->Recursive"), converters.to_name(type(None))),
            "z": converters.to_name(int),
        },
    )


class MyProtocol(Protocol):
    x: int

    @property
    def y(self) -> str: ...


def test_protocol() -> None:
    r = m.Registry()
    s = converters.Scope()
    name = m.assert_name(converters.convert_and_add(r, s, MyProtocol))
    assert r.get(name) == m.Protocol(
        m.Name("test_converters->MyProtocol"),
        (m.Name("builtins->object"),),
        {
            "x": m.Name("builtins->int"),
            "y": m.ReadOnly(m.Name("builtins->str")),
        },
    )


T = TypeVar("T", bound=int)
U = TypeVar("U")


class MyGeneric(Generic[T]):
    x: T


class MyGenericNewStyle[T: int](float):
    x: T


class MyGenericProtocolNoT(Protocol):
    x: int


TIntOrFloat = TypeVar("TIntOrFloat", int, float)


class MyGenericProtocol(Protocol[TIntOrFloat]):
    x: TIntOrFloat


class MyGenericNewStyleProtocol[T: int](Protocol):
    x: T


class ListOfInts(list[int]): ...


def test_generic() -> None:
    r = m.Registry()
    s = converters.Scope().with_at(m.Name("brr"))

    assert converters.get_bases(r, s, MyGeneric) == converters.Bases(
        bases=(m.Name("builtins->object"),),
        is_protocol=False,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.Name("brr"),
                bound=m.Name("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericNewStyle) == converters.Bases(
        bases=(m.Name("builtins->float"),),
        is_protocol=False,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.Name("brr"),
                bound=m.Name("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericProtocolNoT) == converters.Bases(
        bases=(m.Name("builtins->object"),),
        is_protocol=True,
        type_vars=(),
    )
    assert converters.get_bases(r, s, MyGenericProtocol) == converters.Bases(
        bases=(m.Name("builtins->object"),),
        is_protocol=True,
        type_vars=(
            m.TypeVar(
                name="TIntOrFloat",
                at=m.Name("brr"),
                bound=(
                    m.Name("builtins->int"),
                    m.Name("builtins->float"),
                ),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericNewStyleProtocol) == converters.Bases(
        bases=(m.Name("builtins->object"),),
        is_protocol=True,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.Name("brr"),
                bound=m.Name("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, ListOfInts) == converters.Bases(
        bases=(
            m.Bound(
                m.Name("builtins->list"),
                (m.Name("builtins->int"),),
            ),
        ),
        is_protocol=False,
        type_vars=(),
    )

    name = m.assert_name(converters.convert_and_add(r, s, MyGeneric))
    assert r.get(name) == m.Class(
        m.Name("test_converters->MyGeneric"),
        (m.Name("builtins->object"),),
        {
            "x": m.TypeVar(
                name="T",
                at=m.Name("test_converters->MyGeneric"),
                bound=m.Name("builtins->int"),
            ),
        },
        (
            m.TypeVar(
                name="T",
                at=m.Name("test_converters->MyGeneric"),
                bound=m.Name("builtins->int"),
            ),
        ),
    )


def f_with_generic(x: T) -> T:
    return x


def f_with_generic_new_style[V](x: V) -> tuple[V, ...]:
    return (x,)


def test_generic_functions() -> None:
    r = m.Registry()
    s = converters.Scope()

    name = m.assert_name(converters.convert_and_add(r, s, f_with_generic))
    assert r.get(name) == m.Fn(
        name=m.Name("test_converters->f_with_generic"),
        parameters=(
            m.Parameter(
                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                name="x",
                t=m.TypeVar(
                    name="T",
                    at=m.Name("test_converters->f_with_generic"),
                    bound=m.Name("builtins->int"),
                ),
            ),
        ),
        returns=m.TypeVar(
            name="T",
            at=m.Name("test_converters->f_with_generic"),
            bound=m.Name("builtins->int"),
        ),
    )

    name = m.assert_name(converters.convert_and_add(r, s, f_with_generic_new_style))
    assert r.get(name) == m.Fn(
        name=m.Name("test_converters->f_with_generic_new_style"),
        parameters=(
            m.Parameter(
                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                name="x",
                t=m.TypeVar(
                    name="V",
                    at=m.Name("test_converters->f_with_generic_new_style"),
                    bound=m.Intersection.make(),
                ),
            ),
        ),
        returns=m.Tuple(
            m.TypeVar(
                name="V",
                at=m.Name("test_converters->f_with_generic_new_style"),
                bound=m.Intersection.make(),
            )
        ),
    )


class MyGenericWithMethods(Generic[T]):
    def f(self) -> list[T]:
        return []

    def g(self, x: U) -> list[U]:
        return [x]


def test_generic_with_methods() -> None:
    r = m.Registry()
    s = converters.Scope()
    name = m.assert_name(converters.convert_and_add(r, s, MyGenericWithMethods))
    assert r.get(name) == m.Class(
        m.Name("test_converters->MyGenericWithMethods"),
        (m.Name("builtins->object"),),
        {
            "f": m.Method(
                m.Fn(
                    name=m.Name("test_converters->MyGenericWithMethods.f"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.Unknown(),
                        ),
                    ),
                    returns=m.Bound(
                        m.Name("builtins->list"),
                        (
                            m.TypeVar(
                                name="T",
                                at=m.Name("test_converters->MyGenericWithMethods"),
                                bound=m.Name("builtins->int"),
                            ),
                        ),
                    ),
                )
            ),
            "g": m.Method(
                m.Fn(
                    name=m.Name("test_converters->MyGenericWithMethods.g"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.Unknown(),
                        ),
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="x",
                            t=m.TypeVar(
                                name="U",
                                at=m.Name("test_converters->MyGenericWithMethods.g"),
                                bound=m.Intersection.make(),
                            ),
                        ),
                    ),
                    returns=m.Bound(
                        m.Name("builtins->list"),
                        (
                            m.TypeVar(
                                name="U",
                                at=m.Name("test_converters->MyGenericWithMethods.g"),
                                bound=m.Intersection.make(),
                            ),
                        ),
                    ),
                )
            ),
        },
        (
            m.TypeVar(
                name="T",
                at=m.Name("test_converters->MyGenericWithMethods"),
                bound=m.Name("builtins->int"),
            ),
        ),
    )


# TODO: test scoped TypeVars
# class Foo[T]:
#     class Bar[T]:
#         ...
#     ...
# We will never hit this as we're not looking in function bodies
# at runtime.
# def f(x: T) -> T:
#     def g(y: T) -> T:
#         return y
#     return x
