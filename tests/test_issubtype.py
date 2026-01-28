from slypy import check, metatypes as m

import pytest

# Define some reusable class instances
A = m.Class(m.Name("A"), (), {})
B = m.Class(m.Name("B"), (), {})
Bool = m.Class(m.Name("builtins->bool"), (), {})
Int = m.Class(m.Name("builtins->int"), (), {})


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (A, A, True),
        (A, B, False),
        (m.Literal(1), Int, True),
        (m.Literal(1), m.Union(m.Literal(1)), True),
        (m.Literal(1), m.Union(m.Literal(1), m.Literal(2)), True),
        (m.Union(m.Literal(1), m.Literal(2)), m.Union(m.Literal(1), m.Literal(2)), True),
        (m.Union(m.Literal(1), m.Literal(2)), m.Union(m.Literal(1), m.Literal(2), m.Literal(4)), True),
        (m.Union(m.Literal(1), m.Literal(2), m.Literal(4)), m.Union(m.Literal(1), m.Literal(2)), False),
        (m.Union(m.Literal(1), m.Literal(2)), m.Literal(1), False),
        (Int, m.Literal(1), False),
    ],
)
def test_issubtype(a: m.MetaType, b: m.MetaType, expected: bool) -> None:
    registry = m.Registry()
    registry.add(m.Name("builtins->int"), m.Class(m.Name("builtins->int"), (), {}))
    actual = check.issubtype(registry, a, b)
    assert (actual is None) == expected
