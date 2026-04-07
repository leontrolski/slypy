from __future__ import annotations

from dataclasses import dataclass, field
from typing import assert_never
from slypy import canonicalize, metatypes as m

Unsupported = m.Type | m.ClassVar | m.TypeVar | m.Tuple | m.Not | m.Intersection | m.Self | m.ReadOnly


@dataclass
class NotIsSubType:
    a: m.MetaType
    b: m.MetaType
    message: str
    because: list[NotIsSubType] = field(default_factory=list)


# TODO: some caching (readonly registry?) + think about how often to `canonicalize`
def issubtype(r: m.Registry, a: m.MetaType, b: m.MetaType) -> NotIsSubType | None:
    a, b = canonicalize.canonicalize(r, a), canonicalize.canonicalize(r, b)

    if isinstance(a, Unsupported):
        raise NotImplementedError()
    if isinstance(b, Unsupported):
        raise NotImplementedError()

    if isinstance(b, m.NameClass | m.NameFn):
        return issubtype(r, a, r.get(b))
    if isinstance(a, m.NameClass | m.NameFn):
        return issubtype(r, r.get(a), b)

    if isinstance(b, m.Intersection) and b.is_any():
        return None
    if isinstance(a, m.Intersection) and a.is_any():
        return None

    if isinstance(b, m.Unknown):
        return NotIsSubType(a, b, "{b} is Unknown")
    if isinstance(a, m.Unknown):
        return NotIsSubType(a, b, "{a} is Unknown")

    if isinstance(b, m.Error):
        return NotIsSubType(a, b, "{b} is an Error")
    if isinstance(a, m.Error):
        return NotIsSubType(a, b, "{a} is an Error")

    if isinstance(a, m.Union):
        return issubtype_a_union(r, a, b)
    if isinstance(b, m.Union):
        return issubtype_b_union(r, a, b)

    if isinstance(b, m.Literal):
        return issubtype_b_literal(r, a, b)
    if isinstance(a, m.Literal):
        return issubtype_a_literal(r, a, b)

    if isinstance(b, m.Protocol):
        return issubtype_b_protocol(r, a, b)
    if isinstance(a, m.Protocol):
        return issubtype_a_protocol(r, a, b)

    if isinstance(b, m.Bound):
        return issubtype_b_bound(r, a, b)
    if isinstance(a, m.Bound):
        return issubtype_a_bound(r, a, b)

    if isinstance(b, m.Class):
        return issubtype_b_class(r, a, b)
    if isinstance(a, m.Class):
        return NotIsSubType(a, b, "cannot compare class {a} to non-class {b}")

    # I'm not totally convinced this is correct
    if isinstance(b, m.Method):
        return issubtype(r, a, b.as_fn())
    if isinstance(a, m.Method):
        return issubtype(r, a.as_fn(), b)

    if isinstance(a, m.Fn):
        return issubtype_a_fn(r, a, b)
    if isinstance(b, m.Fn):
        return NotIsSubType(a, b, "cannot compare non-function {a} to function {b}")

    # TODO: handle truthiness like `ty`
    # if isinstance(a, m._AlwaysTruthy | m._AlwaysFalsy) or isinstance(b, m._AlwaysTruthy | m._AlwaysFalsy):
    #     raise NotImplementedError()
    assert_never(a)
    assert_never(b)


def issubtype_b_union(
    r: m.Registry,
    a: m.MetaType,
    b: m.Union,
) -> NotIsSubType | None:
    # return any(issubtype(r, a, y) for y in b.ts)
    inner = [issubtype(r, a, y) for y in b.ts]
    because = [x for x in inner if x is not None]
    if len(inner) == len(because):
        return NotIsSubType(a, b, "{a} is not a subtype of union {b}", because)
    return None


def issubtype_a_union(
    r: m.Registry,
    a: m.Union,
    b: m.MetaType,
) -> NotIsSubType | None:
    # return all(issubtype(r, x, b) for x in a.ts)
    inner = [issubtype(r, x, b) for x in a.ts]
    because = [x for x in inner if x is not None]
    if because:
        return NotIsSubType(a, b, "union {a} is not a subtype of {b}", because)
    return None


def issubtype_b_literal(
    r: m.Registry,
    a: m.Literal | m.Class | m.Protocol | m.Fn | m.Method | m.Bound,
    b: m.Literal,
) -> NotIsSubType | None:
    if a == b:
        return None
    return NotIsSubType(a, b, "{a} != {b}")


def issubtype_a_literal(
    r: m.Registry,
    a: m.Literal,
    b: m.Class | m.Protocol | m.Fn | m.Method | m.Bound,
) -> NotIsSubType | None:
    next_ = issubtype(r, a.t, b)
    if next_ is None:
        return None
    because = [next_]
    return NotIsSubType(a, b, "type of {a} is not a subtype of {b}", because)


def issubtype_b_protocol(
    r: m.Registry,
    a: m.Protocol | m.Class | m.Fn | m.Method | m.Bound,
    b: m.Protocol,
) -> NotIsSubType | None:
    if isinstance(a, m.Fn):
        if call := b.as_call():
            return issubtype(r, a, call)
        return NotIsSubType(a, b, "{a} does not conform to protocol with no __call__ {b}", [])
    if isinstance(a, m.Method):
        raise NotImplementedError()
    if isinstance(a, m.Protocol):
        b_ts = all_ts(r, b)
        a_ts = all_ts(r, a)
        because = list[NotIsSubType]()
        for k, u in b_ts.items():
            next_ = issubtype(r, u, a_ts.get(k, m.Unknown()))
            if isinstance(next_, NotIsSubType):
                because.append(next_)
        if because:
            return NotIsSubType(a, b, "{a} does not conform to protocol {b}", because)
        return None
    if isinstance(a, m.Class):
        raise NotImplementedError()
    if isinstance(a, m.Bound):
        raise NotImplementedError()
    assert_never(a)


def issubtype_a_protocol(
    r: m.Registry,
    a: m.Protocol,
    b: m.Class | m.Fn | m.Method | m.Bound,
) -> NotIsSubType | None:
    if isinstance(b, m.Fn):
        if call := a.as_call():
            return issubtype(r, call, b)
        return NotIsSubType(a, b, "cannot compare protocol with no __call__ {a} to function {b}", [])
    return NotIsSubType(a, b, "cannot compare protocol {a} to non-protocol {b}")


def issubtype_b_bound(
    r: m.Registry,
    a: m.Class | m.Fn | m.Method | m.Bound,
    b: m.Bound,
) -> NotIsSubType | None:
    raise NotImplementedError()


def issubtype_a_bound(
    r: m.Registry,
    a: m.Bound,
    b: m.Class | m.Fn | m.Method,
) -> NotIsSubType | None:
    raise NotImplementedError()


def issubtype_b_class(
    r: m.Registry,
    a: m.Class | m.Fn | m.Method | m.Bound,
    b: m.Class,
) -> NotIsSubType | None:
    # TODO: handle generics
    if isinstance(a, m.Class):
        if a.name == b.name:
            return None
        for base in a.bases:
            if issubtype(r, base, b) is None:
                return None
    return NotIsSubType(a, b, "{a} is not a subtype of class {b}")


def issubtype_a_fn(
    r: m.Registry,
    a: m.Fn,
    b: m.Fn,
) -> NotIsSubType | None:
    returns_error = issubtype(r, a.returns, b.returns)  # covariant
    if returns_error is not None:
        return NotIsSubType(a, b, "return type mismatch", [returns_error])

    aligned = align_parameters(a, b)
    if isinstance(aligned, NotIsSubType):
        return aligned
    param_errors = []
    for p_a, p_b in aligned:
        param_error = issubtype(r, p_b.t, p_a.t)  # contravariant
        if param_error:
            param_errors.append(param_error)
    if param_errors:
        return NotIsSubType(a, b, "parameter type mismatches", param_errors)

    return None


def bind(r: m.Registry, t: m.Bound) -> m.MetaType:
    u: m.MetaType = t.t
    if isinstance(u, m.NameClass):
        u = r.get(u)

    if isinstance(u, m.Class | m.Protocol):
        map = dict(zip(u.type_vars, t.bound))

        def f(t: m.MetaType) -> m.MetaType:
            if isinstance(t, m.TypeVar) and t in map:
                return map[t]
            return t

        return m.walk(u.without_type_vars(), f)

    raise NotImplementedError()


def all_ts(r: m.Registry, t: m.MetaType) -> dict[str, m.MetaType]:
    if isinstance(t, m.NameClass):
        return all_ts(r, r.get(t))
    if isinstance(t, m.Bound):
        return all_ts(r, bind(r, t))
    if isinstance(t, m.Class | m.Protocol):
        out = dict[str, m.MetaType]()
        for base in t.bases:
            out |= all_ts(r, base)
        return out | t.ts
    raise NotImplementedError()


def align_parameters(a: m.Fn, b: m.Fn) -> list[tuple[m.Parameter, m.Parameter]] | NotIsSubType:
    a_var_positional: m.Parameter | None = None
    a_var_keyword: m.Parameter | None = None
    a_positional = list[m.Parameter]()
    a_keyword = dict[str, m.Parameter]()

    b_var_positional: m.Parameter | None = None
    b_var_keyword: m.Parameter | None = None
    b_positional = list[m.Parameter]()
    b_positional_exclude_has_default = list[m.Parameter]()
    b_keyword = dict[str, m.Parameter]()
    b_keyword_exclude_has_default = dict[str, m.Parameter]()

    for p in a.parameters:
        if p.kind is m.ParameterKind.VAR_POSITIONAL:
            a_var_positional = p
        if p.kind is m.ParameterKind.VAR_KEYWORD:
            a_var_keyword = p
        if p.kind in {m.ParameterKind.POSITIONAL_ONLY, m.ParameterKind.POSITIONAL_OR_KEYWORD}:
            a_positional.append(p)
        if p.name is not None and p.kind in {m.ParameterKind.KEYWORD_ONLY, m.ParameterKind.POSITIONAL_OR_KEYWORD}:
            a_keyword[p.name] = p

    for p in b.parameters:
        if p.kind is m.ParameterKind.VAR_POSITIONAL:
            b_var_positional = p
        if p.kind is m.ParameterKind.VAR_KEYWORD:
            b_var_keyword = p
        if p.kind in {m.ParameterKind.POSITIONAL_ONLY, m.ParameterKind.POSITIONAL_OR_KEYWORD}:
            b_positional.append(p)
            if not p.has_default:
                b_positional_exclude_has_default.append(p)
        if p.name is not None and p.kind in {m.ParameterKind.KEYWORD_ONLY, m.ParameterKind.POSITIONAL_OR_KEYWORD}:
            b_keyword[p.name] = p
            if not p.has_default:
                b_keyword_exclude_has_default[p.name] = p

    pairs = list[tuple[m.Parameter, m.Parameter]]()

    if len(b_positional_exclude_has_default) > len(a_positional):
        return NotIsSubType(a, b, "{b} has too many positional parameters")
    for i in range(len(a_positional)):
        if i < len(b_positional):
            pairs.append((a_positional[i], b_positional[i]))
        elif b_var_positional:
            pairs.append((a_positional[i], b_var_positional))
        else:
            return NotIsSubType(a, b, "{b} has too few positional parameters")
    if a_var_positional:
        if b_var_positional:
            pairs.append((a_var_positional, b_var_positional))
        else:
            return NotIsSubType(a, b, "{b} doesn't handle *args")

    if set(b_keyword_exclude_has_default) - set(a_keyword):
        return NotIsSubType(a, b, "{b} has too many keyword parameters")
    for k in a_keyword:
        if k in b_keyword:
            pairs.append((a_keyword[k], b_keyword[k]))
        elif b_var_keyword:
            pairs.append((a_keyword[k], b_var_keyword))
        else:
            return NotIsSubType(a, b, "{b} missing parameter for keyword {k}")
    if a_var_keyword:
        if b_var_keyword:
            pairs.append((a_var_keyword, b_var_keyword))
        else:
            return NotIsSubType(a, b, "{b} doesn't handle **kwargs")

    return pairs
