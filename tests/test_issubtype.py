from slypy import check, metatypes as m

import pytest

# Define some reusable class instances
A = m.Class(m.NameClass("A"), (), {})
B = m.Class(m.NameClass("B"), (), {})
Bool = m.Class(m.NameClass("builtins->bool"), (), {})
Int = m.Class(m.NameClass("builtins->int"), (), {})


@pytest.mark.parametrize(
    "a, b, expected",
    [
        (A, A, True),
        (A, B, False),
        (m.Literal.make(1), Int, True),
        (m.Literal.make(1), m.Union.make(m.Literal.make(1)), True),
        (m.Literal.make(1), m.Union.make(m.Literal.make(1), m.Literal.make(2)), True),
        (m.Union.make(m.Literal.make(1), m.Literal.make(2)), m.Union.make(m.Literal.make(1), m.Literal.make(2)), True),
        (
            m.Union.make(m.Literal.make(1), m.Literal.make(2)),
            m.Union.make(m.Literal.make(1), m.Literal.make(2), m.Literal.make(4)),
            True,
        ),
        (
            m.Union.make(m.Literal.make(1), m.Literal.make(2), m.Literal.make(4)),
            m.Union.make(m.Literal.make(1), m.Literal.make(2)),
            False,
        ),
        (m.Union.make(m.Literal.make(1), m.Literal.make(2)), m.Literal.make(1), False),
        (Int, m.Literal.make(1), False),
    ],
)
def test_issubtype(a: m.MetaType, b: m.MetaType, expected: bool) -> None:
    registry = m.Registry()
    registry.add(m.NameClass("builtins->int"), m.Class(m.NameClass("builtins->int"), (), {}))
    actual = check.issubtype(registry, a, b)
    assert (actual is None) == expected
