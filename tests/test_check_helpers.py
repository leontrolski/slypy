from slypy import metatypes as m, check, converters
from slypy.typeshed import builtins


def test_bind() -> None:
    r = m.Registry()
    s = converters.Scope()
    converters.convert_and_add(r, s, builtins.object)
    converters.convert_and_add(r, s, builtins.list)
    t = check.bind(
        r,
        m.Bound(
            m.NameClass("builtins->list"),
            (m.NameClass("X"),),
        ),
    )
    assert isinstance(t, m.Class)
    assert t.ts["__iter__"] == m.Method(
        m.Fn(
            name=m.NameFn("builtins->list.__iter__"),
            parameters=(
                m.Parameter(
                    kind=m.ParameterKind.POSITIONAL_OR_KEYWORD,
                    name="self",
                    t=m.Unknown(),
                ),
            ),
            returns=m.Bound(t=m.NameClass("typing->Iterator"), bound=(m.NameClass("X"),)),
        )
    )


class A:
    x: int
    y: str


class B:
    x: str


class C(A, B):  # type: ignore
    z: float


class D(B, A):  # type: ignore
    z: float


def test_all_ts() -> None:
    r = m.Registry()
    s = converters.Scope()
    name = m.assert_name(converters.convert_and_add(r, s, C))
    t = r.get(name)
    assert isinstance(t, m.Class)
    assert t.ts.keys() == {"z"}

    ts = check.all_ts(r, name)
    assert ts.keys() == {"x", "y", "z"}
    assert ts["x"] == m.NameClass("builtins->str")

    name = m.assert_name(converters.convert_and_add(r, s, D))
    ts = check.all_ts(r, name)
    assert ts.keys() == {"x", "y", "z"}
    assert ts["x"] == m.NameClass("builtins->int")
