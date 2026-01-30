from __future__ import annotations

from functools import partial
from typing import assert_never
from slypy import metatypes as m


Passthrough = (
    m.Literal  #
    | m.Error
    | m.Class
    | m.ClassVar
    | m.Method
    | m.Protocol
    | m.Type
    | m.Fn
    | m.TypeVar
    | m.Bound
    | m.ReadOnly
    | m.Unknown
    | m.Self
)


def canonicalize(registry: m.Registry, t: m.MetaType) -> m.MetaType:
    """Canonicalize types.

    Any concrete MetaType can be rewritten as:

        Union[
            Intersection[...],
            Intersection[...],
            ...
        ]

    with each intersection containing only base types, flattened,
    and duplicates/subsumed types removed.

    This is the canonical Disjunctive Normal Form.
    """
    f = partial(canonicalize, registry)

    if isinstance(t, m.Name):
        return f(registry.get(t))

    if isinstance(t, Passthrough):
        return t

    if isinstance(t, m.Tuple):
        if isinstance(t.ts, tuple):
            return m.Tuple(tuple(f(u) for u in t.ts))
        return m.Tuple(f(t.ts))

    if isinstance(t, m.Not):
        # Push negation inwards if possible (De Morgan)
        u = t.t
        if isinstance(u, m.Not):
            # Double negation
            return f(u.t)
        if isinstance(u, m.Union):
            # ~(A | B) -> ~A & ~B
            return f(m.Intersection.make(*(f(m.Not(u)) for u in u.ts)))
        if isinstance(u, m.Intersection):
            # ~(A & B) -> ~A | ~B
            return f(m.Union.make(*(f(m.Not(u)) for u in u.ts)))
        if isinstance(u, m.Class):
            return m.Not(u)
        return m.Not(u)

    if isinstance(t, m.Union):
        # Flatten unions and canonicalize members
        new_members = frozenset[m.MetaType]()
        for u in t.ts:
            u = f(u)
            new_members |= u.ts if isinstance(u, m.Union) else {u}

        if len(new_members) == 1:
            return next(iter(new_members))
        return m.Union.make(*new_members)

    if isinstance(t, m.Intersection):
        # Flatten intersections and canonicalize members
        new_members = frozenset()
        for u in t.ts:
            u = f(u)
            new_members |= (
                u.ts  #
                if isinstance(u, m.Intersection)
                else {u}
            )

        # Push intersection over any union
        for u in new_members:
            if isinstance(u, m.Union):
                # Found a union to distribute over
                distributed = frozenset[m.MetaType]()
                others = new_members - {u}
                for v in u.ts:
                    dist = f(m.Intersection.make(*(others | {v})))
                    distributed |= dist.ts if isinstance(dist, m.Union) else {dist}
                return m.Union.make(*distributed)

        if len(new_members) == 1:
            return next(iter(new_members))

        # TODO: handle truthiness, generalise for Literals etc.
        # if len(new_members) == 2:
        #     if (truthys := new_members & set(BOOL_MAP)) and (bools := new_members - set(BOOL_MAP)):
        #         [truthy], [bool_] = truthys, bools
        #         if isinstance(bool_, m.Class) and bool_.absolute_name == constants.NAME_BOOL:
        #             return BOOL_MAP[truthy]

        return m.Intersection.make(*new_members)

    assert_never(t)
