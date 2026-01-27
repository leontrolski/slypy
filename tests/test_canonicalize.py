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
            m.Union(A, m.Union(B)),
            m.Union(A, B),
            id="union_flatten",
        ),
        pytest.param(
            m.Intersection(A, m.Intersection(B)),
            m.Intersection(A, B),
            id="intersection_flatten",
        ),
        pytest.param(
            m.Intersection(A, m.Union(B, C)),
            m.Union(m.Intersection(A, B), m.Intersection(A, C)),
            id="intersection_distribute_union",
        ),
        pytest.param(
            m.Not(m.Not(A)),
            A,
            id="double_negation",
        ),
        pytest.param(
            m.Not(m.Union(A, B)),
            m.Intersection(m.Not(A), m.Not(B)),
            id="neg_union_to_intersection",
        ),
        pytest.param(
            m.Not(m.Intersection(A, B)),
            m.Union(m.Not(A), m.Not(B)),
            id="neg_intersection_to_union",
        ),
        pytest.param(
            m.Not(m.Any),
            m.Never,
            id="neg_any",
        ),
        pytest.param(
            m.Not(m.Never),
            m.Any,
            id="neg_never",
        ),
        pytest.param(
            m.Union(A, m.Never),
            A,
            id="union_with_never",
        ),
        pytest.param(
            m.Intersection(A, m.Any),
            A,
            id="intersection_with_any",
        ),
        pytest.param(
            m.Intersection(),
            m.Any,
            id="empty_intersection",
        ),
        pytest.param(
            m.Union(),
            m.Never,
            id="empty_union",
        ),
        pytest.param(
            m.Intersection(m.Intersection(A, m.Union(B, C)), D),
            m.Union(m.Intersection(A, B, D), m.Intersection(A, C, D)),
            id="deep_distributivity",
        ),
        pytest.param(
            m.Union(m.Union(A, B), m.Union(C, D)),
            m.Union(A, B, C, D),
            id="nested_unions_flatten",
        ),
        pytest.param(
            m.Intersection(m.Intersection(A, B), m.Intersection(C, D)),
            m.Intersection(A, B, C, D),
            id="nested_intersections_flatten",
        ),
        pytest.param(
            m.Not(m.Intersection(A, m.Union(B, C))),
            m.Union(
                m.Not(A),
                m.Intersection(m.Not(B), m.Not(C)),
            ),
            id="complex_negation",
        ),
    ],
)
def test_canonicalize(input_type: m.MetaType, expected: m.MetaType) -> None:
    actual = check.canonicalize(m.Registry(), input_type)
    assert actual == expected
