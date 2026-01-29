from __future__ import annotations

from collections import abc
from dataclasses import dataclass, field, replace
import enum
import functools
import inspect
import types
import typing
from typing import Any, Callable, TypeVar
from slypy import errors, metatypes as m
from slypy.typeshed import builtins

F = typing.TypeVar("F", bound=Callable[..., Any])
cache: Callable[[F], F] = functools.cache  # type: ignore
MethodKind = typing.Literal["method", "classmethod", "staticmethod", "property"]
type Function = Callable[..., Any] | types.FunctionType | classmethod[Any, Any, Any] | staticmethod[Any, Any]


@dataclass
class Scope:
    at: m.Name | None = None
    type_var_scope: dict[str, m.TypeVar] = field(default_factory=dict)

    def with_at(self, at: m.Name) -> Scope:
        return replace(self, at=at)

    def with_type_vars(self, type_vars: tuple[m.TypeVar, ...]) -> Scope:
        new_scope = {type_var.name: type_var for type_var in type_vars}
        return replace(self, type_var_scope=self.type_var_scope | new_scope)


TYPING_ATOMS = {
    typing.Any: m.Intersection.make,
    typing.AnyStr: None,
    typing.LiteralString: None,
    typing.Never: m.Union.make,
    typing.NoReturn: None,
    typing.Self: m.Self,
    typing.TypeAlias: None,
    typing.ParamSpecArgs: None,
    typing.ParamSpecKwargs: None,
    typing.TypeAliasType: None,
    typing.NamedTuple: None,
    typing.TypedDict: None,
    typing.Protocol: None,
}
TYPING_GENERICS = (
    tuple,
    abc.Callable,
    typing.Union,
    types.UnionType,
    typing.Optional,
    typing.Concatenate,
    typing.Literal,
    typing.ClassVar,
    typing.Final,
    typing.Required,  # Used in TypedDict
    typing.NotRequired,  # Used in TypedDict
    typing.ReadOnly,  # Used in TypedDict
    typing.Annotated,
    typing.TypeIs,
    typing.TypeGuard,
    typing.Unpack,
    typing.Generic,
    typing.Protocol,
)
TYPING_CONSTRUCTORS = (
    typing.TypeVar,
    typing.TypeVarTuple,
    typing.ParamSpec,
    typing.NewType,
)
TYPING_DECORATORS = (
    typing.dataclass_transform,
    typing.overload,
    typing.final,
    typing.no_type_check,
    typing.override,
)


def convert_and_add(r: m.Registry, s: Scope, t: Any | type[inspect._empty]) -> m.MetaType:
    if t is inspect._empty:
        return m.Unknown()

    if isinstance(t, typing.TypeVar):
        return convert_type_var(r, s, t)

    if typing.get_args(t):
        return convert_with_args(r, s, t)

    if t in TYPING_ATOMS:
        if (meta_atom_cls := TYPING_ATOMS[t]) is not None:
            return meta_atom_cls()
        raise NotImplementedError()

    if isinstance(t, type):
        name = to_name(t)
        if name not in r:
            r.add(name, name)
            meta_cls = convert_class(r, s, t)
            r.add(name, meta_cls)
        return name

    if isinstance(t, types.FunctionType):
        name = to_name(t)
        if name not in r:
            r.add(name, name)
            meta_fn = convert_function(r, s, t, name)
            r.add(name, meta_fn)
        return name

    raise errors.SlyPyError(f"Cannot add type {t}")


def convert_with_args(r: m.Registry, s: Scope, t: Any) -> m.MetaType:
    origin, args = typing.get_origin(t), typing.get_args(t)

    if origin in TYPING_GENERICS:
        if origin is tuple:
            if len(args) == 2 and args[1] == ...:
                return m.Tuple(convert_and_add(r, s, args[0]))
            return m.Tuple(tuple(convert_and_add(r, s, arg) for arg in args))
        if origin is typing.ClassVar:
            [arg] = args
            return m.ClassVar(convert_and_add(r, s, arg))
        if origin is typing.Literal:
            literals = list[m.Literal]()
            for arg in args:
                if not isinstance(arg, m.LiteralValueBefore):
                    raise errors.SlyPyError(f"Cannot use {arg} as Literal value")
                if isinstance(arg, enum.Enum):
                    arg = m.EnumValue(m.assert_name(convert_and_add(r, s, arg.__class__)), arg.name, arg.value)
                literals.append(m.Literal.make(arg))
            return m.Union.make(*literals)
        if origin is typing.Union or origin is types.UnionType:
            return m.Union.make(*(convert_and_add(r, s, arg) for arg in args))
        if origin is abc.Callable:
            [params, return_type] = args
            parameters = (
                tuple(
                    m.Parameter(kind=m.ParameterKind.POSITIONAL_ONLY, name=None, t=convert_and_add(r, s, param))
                    for param in params
                )
                if isinstance(params, list)
                else None
            )
            return m.Fn(parameters=parameters, returns=convert_and_add(r, s, return_type))
        raise NotImplementedError()
    return m.Bound(convert_and_add(r, s, origin), tuple(convert_and_add(r, s, arg) for arg in args))


def convert_class(r: m.Registry, s: Scope, t: type[Any]) -> m.Class | m.Protocol:
    assert isinstance(t, type)
    name = to_name(t)

    bases_plus = get_bases(r, s.with_at(name), t)
    s = s.with_type_vars(bases_plus.type_vars)

    ts = dict[str, m.MetaType]()
    for k, v in typing.get_type_hints(t).items():
        ts[k] = convert_and_add(r, s, v)
    for k, [method_kind, method] in methods(t).items():
        method_name = m.Name(f"{name.absolute_name}.{k}")
        v = convert_function(r, s, method, method_name)
        if method_kind == "method":
            v = m.Method(v)
        elif method_kind == "classmethod":
            v = m.ClassVar(m.Method(v))
        elif method_kind == "staticmethod":
            pass
        elif method_kind == "property":
            v = m.ReadOnly(v.returns)
        else:
            typing.assert_never(method_kind)
        ts[k] = v

    # TODO: at this point, infer all the variances and make a new `ts`

    if bases_plus.is_protocol:
        return m.Protocol(name, bases_plus.bases, ts, bases_plus.type_vars)
    return m.Class(name, bases_plus.bases, ts, bases_plus.type_vars)


def convert_function(r: m.Registry, s: Scope, t: Function, name: m.Name | None) -> m.Fn:
    if name is not None:
        s = s.with_at(name)
    sig = inspect.signature(typing.cast(Callable[..., Any], t), eval_str=True)
    parameters = list[m.Parameter]()
    for sig_name, sig_param in sig.parameters.items():
        parameter = m.Parameter(
            kind=PARAMETER_KIND_MAP[sig_param.kind],
            name=sig_name,
            t=convert_and_add(r, s, sig_param.annotation),
        )
        parameters.append(parameter)
    returns = convert_and_add(r, s, sig.return_annotation)
    return m.Fn(name=name, parameters=tuple(parameters), returns=returns)


@dataclass
class Bases:
    bases: tuple[m.MetaType, ...]  # including bound TypeVars
    is_protocol: bool
    type_vars: tuple[m.TypeVar, ...]


def get_bases(r: m.Registry, s: Scope, t: type[Any]) -> Bases:
    raw_bases = list[type[Any]]()
    is_protocol = False
    raw_type_vars = list[typing.TypeVar]()
    for u in getattr(t, "__orig_bases__", t.__bases__):
        v = typing.get_origin(u) or u
        if v is typing.Protocol:
            is_protocol = True
            raw_type_vars.extend(typing.get_args(u))
        elif v is typing.Generic:
            raw_type_vars.extend(typing.get_args(u))
        else:
            raw_bases.append(u)

    bases = tuple(convert_and_add(r, s, base) for base in raw_bases)
    if not bases:
        bases = (m.Name("builtins->object"),)
    type_vars = tuple(convert_type_var(r, s, type_var) for type_var in raw_type_vars)
    return Bases(bases, is_protocol, type_vars)


def convert_type_var(r: m.Registry, s: Scope, t: TypeVar) -> m.TypeVar:
    name = t.__name__
    if name in s.type_var_scope:
        return s.type_var_scope[name]
    if s.at is None:
        raise errors.SlyPyError("No name to attach TypeVar to")

    # Note for t.__covariant__, t.__contravariant__, we pretend always t.__infer_variance__
    bound: m.MetaType | tuple[m.MetaType, ...] = m.Intersection.make()
    if t.__bound__ is not None:
        bound = convert_and_add(r, s, t.__bound__)
    if t.__constraints__:
        bound = tuple(convert_and_add(r, s, constraint) for constraint in t.__constraints__)
    return m.TypeVar(
        name=name,
        at=s.at,
        bound=bound,
    )


PARAMETER_KIND_MAP = {
    inspect.Parameter.POSITIONAL_ONLY: m.ParameterKind.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD: m.ParameterKind.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL: m.ParameterKind.VAR_POSITIONAL,
    inspect.Parameter.KEYWORD_ONLY: m.ParameterKind.KEYWORD_ONLY,
    inspect.Parameter.VAR_KEYWORD: m.ParameterKind.VAR_KEYWORD,
}


@cache
def to_name(t: Any) -> m.Name:
    module = t.__module__
    if module == builtins.__name__:
        module = "builtins"
    return m.Name(f"{module}->{t.__name__}")


@cache
def methods(t: type[Any]) -> dict[str, tuple[MethodKind, Function]]:
    out = dict[str, tuple[MethodKind, Function]]()
    for k, v in t.__dict__.items():
        pair: tuple[MethodKind, Function]
        if isinstance(v, classmethod):
            v = v.__func__
            pair = "classmethod", v
        elif isinstance(v, staticmethod):
            pair = "staticmethod", v
        elif isinstance(v, property):
            assert v.fget is not None
            v = v.fget
            pair = "property", v
        elif inspect.isfunction(v):
            pair = "method", v
        else:
            continue

        # Only add methods defined directly on class
        if not getattr(v, "__qualname__", "").startswith(f"{t.__name__}."):
            continue

        out[k] = pair

    return out
