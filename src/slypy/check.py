from functools import partial
from typing import assert_never
from slypy import metatypes as m

Unsupported = (
    m.Protocol  #
    | m.Fn
    | m.Type
    | m.ClassVar
    | m.Method
    | m.TypeVar
    | m.Bound
    | m.Tuple
    | m.Not
    | m.Intersection
)


# TODO: some caching
def issubtype(registry: m.Registry, a: m.MetaType, b: m.MetaType) -> bool:
    a, b = canonicalize(registry, a), canonicalize(registry, b)
    # reasons = list[str]()

    def _issubtype(a: m.MetaType, b: m.MetaType) -> bool:
        if isinstance(a, m.Name):
            return f(registry.get(a), b)
        if isinstance(b, m.Name):
            return f(a, registry.get(b))

        if isinstance(a, Unsupported):
            raise NotImplementedError()
        if isinstance(b, Unsupported):
            raise NotImplementedError()

        if isinstance(a, m.Error) or isinstance(b, m.Error):
            return False

        # TODO: handle truthiness
        # if isinstance(a, m._AlwaysTruthy | m._AlwaysFalsy) or isinstance(b, m._AlwaysTruthy | m._AlwaysFalsy):
        #     raise NotImplementedError()  # TODO: handle Literal[0] etc. see BOOL_MAP and ty tests with `int` gotchas

        if isinstance(a, m.Union):
            return all(f(x, b) for x in a.ts)
        if isinstance(b, m.Union):
            return any(f(a, y) for y in b.ts)

        if isinstance(b, m.Literal):
            return a == b
        if isinstance(a, m.Literal):
            return f(a.t, b)

        if isinstance(b, m.Class):
            # TODO: handle generics, subclassing
            return isinstance(a, m.Class) and a.name == b.name
        if isinstance(a, m.Class):
            return isinstance(b, m.Class) and a.name == a.name

        assert_never(a)
        assert_never(b)

    f = _issubtype
    return f(a, b)


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
            return f(m.Intersection(*(f(m.Not(u)) for u in u.ts)))
        if isinstance(u, m.Intersection):
            # ~(A & B) -> ~A | ~B
            return f(m.Union(*(f(m.Not(u)) for u in u.ts)))
        if isinstance(u, m.Class):
            if u.name == m.object.name:
                return m.Never  # ~Any = Never
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
        return m.Union(*new_members)

    if isinstance(t, m.Intersection):
        # Flatten intersections and canonicalize members
        new_members = frozenset()
        for u in t.ts:
            u = f(u)
            new_members |= (
                u.ts  #
                if isinstance(u, m.Intersection)
                else set()
                if isinstance(u, m.Class) and u.name == m.object.name
                else {u}
            )

        # Push intersection over any union
        for u in new_members:
            if isinstance(u, m.Union):
                # Found a union to distribute over
                distributed = frozenset[m.MetaType]()
                others = new_members - {u}
                for v in u.ts:
                    dist = f(m.Intersection(*(others | {v})))
                    distributed |= dist.ts if isinstance(dist, m.Union) else {dist}
                return m.Union(*distributed)

        if not new_members:
            return m.object  # Intersection of zero = Any
        if len(new_members) == 1:
            return next(iter(new_members))

        # TODO: handle truthiness, generalise for Literals etc.
        # if len(new_members) == 2:
        #     if (truthys := new_members & set(BOOL_MAP)) and (bools := new_members - set(BOOL_MAP)):
        #         [truthy], [bool_] = truthys, bools
        #         if isinstance(bool_, m.Class) and bool_.absolute_name == constants.NAME_BOOL:
        #             return BOOL_MAP[truthy]

        return m.Intersection(*new_members)

    assert_never(t)
