from __future__ import annotations

from dataclasses import dataclass, field
from typing import assert_never
from slypy import canonicalize, metatypes as m

Unsupported = m.Type | m.ClassVar | m.TypeVar | m.Bound | m.Tuple | m.Not | m.Intersection | m.Self | m.ReadOnly


@dataclass
class NotIsSubType:
    a: m.MetaType
    b: m.MetaType
    message: str
    because: list[NotIsSubType] = field(default_factory=list)


# TODO: some caching + think about how often to `canonicalize`
def issubtype(registry: m.Registry, a: m.MetaType, b: m.MetaType) -> NotIsSubType | None:
    a, b = canonicalize.canonicalize(registry, a), canonicalize.canonicalize(registry, b)

    def _issubtype(a: m.MetaType, b: m.MetaType) -> NotIsSubType | None:
        if isinstance(a, m.Intersection) and a.is_any():
            return None
        if isinstance(b, m.Intersection) and b.is_any():
            return None
        if isinstance(a, Unsupported) or isinstance(b, Unsupported):
            raise NotImplementedError()

        if isinstance(a, m.Name):
            return f(registry.get(a), b)
        if isinstance(b, m.Name):
            return f(a, registry.get(b))
        if isinstance(a, m.Unknown):
            return NotIsSubType(a, b, "{a} is Unknown")
        if isinstance(b, m.Unknown):
            return NotIsSubType(a, b, "{b} is Unknown")
        if isinstance(a, m.Error):
            return NotIsSubType(a, b, "{a} is an Error")
        if isinstance(b, m.Error):
            return NotIsSubType(a, b, "{b} is an Error")

        # TODO: handle truthiness
        # if isinstance(a, m._AlwaysTruthy | m._AlwaysFalsy) or isinstance(b, m._AlwaysTruthy | m._AlwaysFalsy):
        #     raise NotImplementedError()  # TODO: handle Literal[0] etc. see BOOL_MAP and ty tests with `int` gotchas

        if isinstance(a, m.Union):
            # return all(f(x, b) for x in a.ts)
            inner = [f(x, b) for x in a.ts]
            because = [x for x in inner if x is not None]
            if because:
                return NotIsSubType(a, b, "union {a} is not a subtype of {b}", because)
            return None
        if isinstance(b, m.Union):
            # return any(f(a, y) for y in b.ts)
            inner = [f(a, y) for y in b.ts]
            because = [x for x in inner if x is not None]
            if len(inner) == len(because):
                return NotIsSubType(a, b, "{a} is not a subtype of union {b}", because)
            return None

        if isinstance(b, m.Literal):
            if a == b:
                return None
            return NotIsSubType(a, b, "{a} != {b}")

        if isinstance(a, m.Literal):
            next_ = f(a.t, b)
            if next_ is None:
                return None
            because = [next_]
            return NotIsSubType(a, b, "type of {a} is not a subtype of {b}", because)

        if isinstance(b, m.Class):
            # TODO: handle generics, subclassing
            if isinstance(a, m.Class) and a.name == b.name:
                return None
            return NotIsSubType(a, b, "{a} is not a subtype of class {b}")
        if isinstance(a, m.Class):
            if isinstance(b, m.Class) and a.name == b.name:
                return None
            return NotIsSubType(a, b, "class {a} is not a subtype of {b}")

        if isinstance(b, m.Protocol):
            if isinstance(a, m.Fn) and (call := b.as_call()):
                return f(a, call)
            if isinstance(a, m.Protocol):
                because = list[NotIsSubType]()
                for k, u in b.ts.items():
                    # TODO: implement parent classes
                    next_ = f(u, a.ts.get(k, m.Unknown()))
                    if isinstance(next_, NotIsSubType):
                        because.append(next_)
                if because:
                    return NotIsSubType(a, b, "{a} does not conform to protocol {b}", because)
                return None
            raise NotImplementedError()
        if isinstance(a, m.Protocol):
            if isinstance(b, m.Fn) and (call := a.as_call()):
                return f(call, b)
            raise NotImplementedError()

        # I'm not totally convinced this is correct
        if isinstance(b, m.Method):
            return f(a, b.as_fn())
        if isinstance(a, m.Method):
            return f(a.as_fn(), b)

        if isinstance(a, m.Fn):
            if not isinstance(b, m.Fn):
                return NotIsSubType(a, b, "cannot compare function to non-function")

            returns_error = f(a.returns, b.returns)  # covariant
            if returns_error is not None:
                return NotIsSubType(a, b, "return type mismatch", [returns_error])

            aligned = align_parameters(a, b)
            if isinstance(aligned, NotIsSubType):
                return aligned
            param_errors = []
            for p_a, p_b in aligned:
                param_error = f(p_b.t, p_a.t)  # contravariant
                if param_error:
                    param_errors.append(param_error)
            if param_errors:
                return NotIsSubType(a, b, "parameter type mismatches", param_errors)

            return None
        if isinstance(b, m.Fn):
            return NotIsSubType(a, b, "cannot compare function to non-function")

        assert_never(a)
        assert_never(b)

    f = _issubtype
    return f(a, b)


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
