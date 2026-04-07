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


def test_typeshed() -> None:
    r = m.Registry()
    s = converters.Scope()
    name = converters.convert_and_add(r, s, builtins.int)
    assert name == m.NameClass("builtins->int")


def test_function() -> None:
    r = m.Registry()
    s = converters.Scope()
    int_name = m.assert_name(converters.convert_and_add(r, s, builtins.int))

    name = m.assert_name_fn(converters.convert_and_add(r, s, f))
    assert name == m.NameFn("test_converters->f")
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

    name = m.assert_name_fn(converters.convert_and_add(r, s, g))
    assert name == m.NameFn("test_converters->g")
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
        m.NameClass("test_converters->MyClass"),
        (m.NameClass("builtins->object"),),
        {
            "class_var": m.ClassVar(m.NameClass("builtins->int")),
            "bool_": m.NameClass("builtins->bool"),
            "int_or_none": m.Union.make(m.NameClass("builtins->int"), m.NameClass("builtins->NoneType")),
            "optional": m.Union.make(m.NameClass("builtins->float"), m.NameClass("builtins->NoneType")),
            "decimal_": m.NameClass("decimal->Decimal"),
            "none": m.NameClass("builtins->NoneType"),
            "object_": m.NameClass("test_converters->Bar"),
            "array_of_objects": m.Bound(
                m.NameClass("builtins->list"),
                (m.NameClass("test_converters->Bar"),),
            ),
            "recursive": m.NameClass("test_converters->Recursive"),
            "literal": m.Union.make(m.Literal.make("one"), m.Literal.make("two")),
            "literal_enum": m.Union.make(
                m.Literal.make(m.EnumValue(converters.get_name(MyEnum), "A", "a")),
                m.Literal.make(m.EnumValue(converters.get_name(MyEnum), "B", "b")),
            ),
            "union_array": m.Bound(
                m.NameClass("builtins->list"),
                (m.Union.make(m.NameClass("builtins->int"), m.NameClass("builtins->NoneType")),),
            ),
            "function": m.Fn(
                position=None,
                name=None,
                parameters=(
                    m.Parameter(
                        position=None,
                        kind=m.ParameterKind.POSITIONAL_ONLY,
                        name=None,
                        t=m.NameClass("builtins->int"),
                    ),
                ),
                returns=m.NameClass("builtins->int"),
            ),
            "method": m.Method(
                m.Fn(
                    name=m.NameFn("test_converters->MyClass.method"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.Unknown(),
                        ),
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="a",
                            t=converters.get_name(builtins.int),
                        ),
                    ),
                    returns=converters.get_name(builtins.str),
                )
            ),
            "class_method": m.ClassVar(
                m.Method(
                    m.Fn(
                        name=m.NameFn("test_converters->MyClass.class_method"),
                        parameters=(
                            m.Parameter(
                                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                                name="cls",
                                t=m.Unknown(),
                            ),
                            m.Parameter(
                                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                                name="b",
                                t=converters.get_name(builtins.int),
                            ),
                        ),
                        returns=m.Self(),
                    )
                )
            ),
            "static_method": m.Fn(
                name=m.NameFn("test_converters->MyClass.static_method"),
                parameters=(
                    m.Parameter(
                        kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                        name="c",
                        t=converters.get_name(builtins.int),
                    ),
                ),
                returns=converters.get_name(builtins.str),
            ),
        },
    )

    name = m.assert_name(converters.convert_and_add(r, s, Recursive))
    assert r.get(name) == m.Class(
        m.NameClass("test_converters->Recursive"),
        (m.NameClass("builtins->object"),),
        {
            "children": m.Bound(
                converters.get_name(list),
                (m.NameClass("test_converters->Recursive"),),
            ),
            "parent": m.Union.make(m.NameClass("test_converters->Recursive"), converters.get_name(type(None))),
            "z": converters.get_name(int),
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
        m.NameClass("test_converters->MyProtocol"),
        (m.NameClass("builtins->object"),),
        {
            "x": m.NameClass("builtins->int"),
            "y": m.ReadOnly(m.NameClass("builtins->str")),
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
    s = converters.Scope().with_at(m.NameClass("brr"))

    assert converters.get_bases(r, s, MyGeneric) == converters.Bases(
        bases=(m.NameClass("builtins->object"),),
        is_protocol=False,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.NameClass("brr"),
                bound=m.NameClass("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericNewStyle) == converters.Bases(
        bases=(m.NameClass("builtins->float"),),
        is_protocol=False,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.NameClass("brr"),
                bound=m.NameClass("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericProtocolNoT) == converters.Bases(
        bases=(m.NameClass("builtins->object"),),
        is_protocol=True,
        type_vars=(),
    )
    assert converters.get_bases(r, s, MyGenericProtocol) == converters.Bases(
        bases=(m.NameClass("builtins->object"),),
        is_protocol=True,
        type_vars=(
            m.TypeVar(
                name="TIntOrFloat",
                at=m.NameClass("brr"),
                bound=(
                    m.NameClass("builtins->int"),
                    m.NameClass("builtins->float"),
                ),
            ),
        ),
    )
    assert converters.get_bases(r, s, MyGenericNewStyleProtocol) == converters.Bases(
        bases=(m.NameClass("builtins->object"),),
        is_protocol=True,
        type_vars=(
            m.TypeVar(
                name="T",
                at=m.NameClass("brr"),
                bound=m.NameClass("builtins->int"),
            ),
        ),
    )
    assert converters.get_bases(r, s, ListOfInts) == converters.Bases(
        bases=(
            m.Bound(
                m.NameClass("builtins->list"),
                (m.NameClass("builtins->int"),),
            ),
        ),
        is_protocol=False,
        type_vars=(),
    )

    name = m.assert_name(converters.convert_and_add(r, s, MyGeneric))
    assert r.get(name) == m.Class(
        m.NameClass("test_converters->MyGeneric"),
        (m.NameClass("builtins->object"),),
        {
            "x": m.TypeVar(
                name="T",
                at=m.NameClass("test_converters->MyGeneric"),
                bound=m.NameClass("builtins->int"),
            ),
        },
        (
            m.TypeVar(
                name="T",
                at=m.NameClass("test_converters->MyGeneric"),
                bound=m.NameClass("builtins->int"),
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

    name = m.assert_name_fn(converters.convert_and_add(r, s, f_with_generic))
    assert r.get(name) == m.Fn(
        name=m.NameFn("test_converters->f_with_generic"),
        parameters=(
            m.Parameter(
                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                name="x",
                t=m.TypeVar(
                    name="T",
                    at=m.NameFn("test_converters->f_with_generic"),
                    bound=m.NameClass("builtins->int"),
                ),
            ),
        ),
        returns=m.TypeVar(
            name="T",
            at=m.NameFn("test_converters->f_with_generic"),
            bound=m.NameClass("builtins->int"),
        ),
    )

    name = m.assert_name_fn(converters.convert_and_add(r, s, f_with_generic_new_style))
    assert r.get(name) == m.Fn(
        name=m.NameFn("test_converters->f_with_generic_new_style"),
        parameters=(
            m.Parameter(
                kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                name="x",
                t=m.TypeVar(
                    name="V",
                    at=m.NameFn("test_converters->f_with_generic_new_style"),
                    bound=m.Intersection.make(),
                ),
            ),
        ),
        returns=m.Tuple(
            m.TypeVar(
                name="V",
                at=m.NameFn("test_converters->f_with_generic_new_style"),
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
        m.NameClass("test_converters->MyGenericWithMethods"),
        (m.NameClass("builtins->object"),),
        {
            "f": m.Method(
                m.Fn(
                    name=m.NameFn("test_converters->MyGenericWithMethods.f"),
                    parameters=(
                        m.Parameter(
                            kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                            name="self",
                            t=m.Unknown(),
                        ),
                    ),
                    returns=m.Bound(
                        m.NameClass("builtins->list"),
                        (
                            m.TypeVar(
                                name="T",
                                at=m.NameClass("test_converters->MyGenericWithMethods"),
                                bound=m.NameClass("builtins->int"),
                            ),
                        ),
                    ),
                )
            ),
            "g": m.Method(
                m.Fn(
                    name=m.NameFn("test_converters->MyGenericWithMethods.g"),
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
                                at=m.NameFn("test_converters->MyGenericWithMethods.g"),
                                bound=m.Intersection.make(),
                            ),
                        ),
                    ),
                    returns=m.Bound(
                        m.NameClass("builtins->list"),
                        (
                            m.TypeVar(
                                name="U",
                                at=m.NameFn("test_converters->MyGenericWithMethods.g"),
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
                at=m.NameClass("test_converters->MyGenericWithMethods"),
                bound=m.NameClass("builtins->int"),
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
