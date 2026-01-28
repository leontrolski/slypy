from collections import abc
import enum
import functools
import inspect
import types
import typing
from typing import Any, Callable, get_origin
from slypy import errors, metatypes as m
from slypy.typeshed import builtins

F = typing.TypeVar("F", bound=Callable[..., Any])
cache: Callable[[F], F] = functools.cache  # type: ignore
MethodKind = typing.Literal["method", "classmethod", "staticmethod", "property"]
type Function = Callable[..., Any] | types.FunctionType | classmethod[Any, Any, Any] | staticmethod[Any, Any]


TYPING_ATOMS = {
    typing.Any: m.Any,
    typing.AnyStr: None,
    typing.LiteralString: None,
    typing.Never: None,
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


def convert_and_add(r: m.Registry, t: Any | type[inspect._empty]) -> m.MetaType:
    if t is inspect._empty:
        return m.Unknown()

    if typing.get_args(t):
        return convert_with_args(r, t)

    if t in TYPING_ATOMS:
        if (meta_atom_cls := TYPING_ATOMS[t]) is not None:
            return meta_atom_cls()
        raise NotImplementedError()

    if isinstance(t, type):
        name = to_name(t)
        if name not in r:
            r.add(name, name)
            meta_cls = convert_class(r, t)
            r.add(name, meta_cls)
        return name

    if isinstance(t, types.FunctionType):
        name = to_name(t)
        if name not in r:
            r.add(name, name)
            meta_fn = convert_function(r, t, name)
            r.add(name, meta_fn)
        return name

    raise errors.SlyPyError(f"Cannot add type {t}")


def convert_with_args(r: m.Registry, t: Any) -> m.MetaType:
    origin, args = typing.get_origin(t), typing.get_args(t)

    if origin in TYPING_GENERICS:
        if origin is typing.ClassVar:
            [arg] = args
            return m.ClassVar(convert_and_add(r, arg))
        if origin is typing.Literal:
            literals = list[m.Literal]()
            for arg in args:
                if not isinstance(arg, m.LiteralValueBefore):
                    raise errors.SlyPyError(f"Cannot use {arg} as Literal value")
                if isinstance(arg, enum.Enum):
                    arg = m.EnumValue(m.assert_name(convert_and_add(r, arg.__class__)), arg.name, arg.value)
                literals.append(m.Literal(arg))
            return m.Union(*literals)
        if origin is typing.Union or origin is types.UnionType:
            return m.Union(*(convert_and_add(r, arg) for arg in args))
        if origin is abc.Callable:
            [params, return_type] = args
            parameters = (
                tuple(
                    m.Parameter(kind=m.ParameterKind.POSITIONAL_ONLY, name=None, t=convert_and_add(r, param))
                    for param in params
                )
                if isinstance(params, list)
                else None
            )
            return m.Fn(parameters=parameters, returns=convert_and_add(r, return_type))
        raise NotImplementedError()

    return m.Bound(convert_and_add(r, origin), tuple(convert_and_add(r, arg) for arg in args))


def convert_class(r: m.Registry, t: type[Any]) -> m.Class | m.Protocol:
    assert isinstance(t, type)
    name = to_name(t)
    ts = dict[str, m.MetaType]()
    for k, v in typing.get_type_hints(t).items():
        ts[k] = convert_and_add(r, v)
    for k, [method_kind, method] in methods(t).items():
        method_name = m.Name(f"{name.absolute_name}.{k}")
        v = convert_function(r, method, method_name)
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
    bases = list[m.MetaType]()
    is_protocol = False
    for base in t.__bases__:
        if base is typing.Protocol:  # type: ignore[comparison-overlap]
            is_protocol = True
        elif get_origin(base) is typing.Protocol:
            raise NotImplementedError()
        else:
            bases.append(convert_and_add(r, base))
    if is_protocol:
        return m.Protocol(name, tuple(bases), ts)
    return m.Class(name, tuple(bases), ts)


def convert_function(r: m.Registry, t: Function, name: m.Name | None) -> m.Fn:
    sig = inspect.signature(typing.cast(Callable[..., Any], t), eval_str=True)
    parameters = list[m.Parameter]()
    for sig_name, sig_param in sig.parameters.items():
        parameter = m.Parameter(
            kind=PARAMETER_KIND_MAP[sig_param.kind],
            name=sig_name,
            t=convert_and_add(r, sig_param.annotation),
        )
        parameters.append(parameter)
    returns = convert_and_add(r, sig.return_annotation)
    return m.Fn(name=name, parameters=tuple(parameters), returns=returns)


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
