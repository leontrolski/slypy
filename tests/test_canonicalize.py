from slypy import check, metatypes as m

import pytest

# Define some reusable class instances
A = m.Class(m.Name("A"), (), {})
B = m.Class(m.Name("B"), (), {})
C = m.Class(m.Name("C"), (), {})
D = m.Class(m.Name("D"), (), {})
Bool = m.Class(m.Name("builtins->bool"), (), {})


@pytest.mark.parametrize(
    "input_type, expected",
    [
        pytest.param(
            A,
            A,
            id="base_class",
        ),
        pytest.param(
            m.Union.make(A, m.Union.make(B)),
            m.Union.make(A, B),
            id="union_flatten",
        ),
        pytest.param(
            m.Intersection.make(A, m.Intersection.make(B)),
            m.Intersection.make(A, B),
            id="intersection_flatten",
        ),
        pytest.param(
            m.Intersection.make(A, m.Union.make(B, C)),
            m.Union.make(m.Intersection.make(A, B), m.Intersection.make(A, C)),
            id="intersection_distribute_union",
        ),
        pytest.param(
            m.Not(m.Not(A)),
            A,
            id="double_negation",
        ),
        pytest.param(
            m.Not(m.Union.make(A, B)),
            m.Intersection.make(m.Not(A), m.Not(B)),
            id="neg_union_to_intersection",
        ),
        pytest.param(
            m.Not(m.Intersection.make(A, B)),
            m.Union.make(m.Not(A), m.Not(B)),
            id="neg_intersection_to_union",
        ),
        pytest.param(
            m.Not(m.Any()),
            m.Union.make(),
            id="neg_any",
        ),
        pytest.param(
            m.Not(m.Union.make()),
            m.Any(),
            id="neg_never",
        ),
        pytest.param(
            m.Union.make(A, m.Union.make()),
            A,
            id="union_with_never",
        ),
        pytest.param(
            m.Intersection.make(A, m.Any()),
            A,
            id="intersection_with_any",
        ),
        pytest.param(
            m.Intersection.make(),
            m.Any(),
            id="empty_intersection",
        ),
        pytest.param(
            m.Union.make(),
            m.Union.make(),
            id="empty_union",
        ),
        pytest.param(
            m.Intersection.make(m.Intersection.make(A, m.Union.make(B, C)), D),
            m.Union.make(m.Intersection.make(A, B, D), m.Intersection.make(A, C, D)),
            id="deep_distributivity",
        ),
        pytest.param(
            m.Union.make(m.Union.make(A, B), m.Union.make(C, D)),
            m.Union.make(A, B, C, D),
            id="nested_unions_flatten",
        ),
        pytest.param(
            m.Intersection.make(m.Intersection.make(A, B), m.Intersection.make(C, D)),
            m.Intersection.make(A, B, C, D),
            id="nested_intersections_flatten",
        ),
        pytest.param(
            m.Not(m.Intersection.make(A, m.Union.make(B, C))),
            m.Union.make(
                m.Not(A),
                m.Intersection.make(m.Not(B), m.Not(C)),
            ),
            id="complex_negation",
        ),
    ],
)
def test_canonicalize(input_type: m.MetaType, expected: m.MetaType) -> None:
    actual = check.canonicalize(m.Registry(), input_type)
    assert actual == expected
