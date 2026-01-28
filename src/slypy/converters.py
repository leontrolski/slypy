from dataclasses import dataclass
import enum
import functools
import inspect
from pathlib import Path
import types
import typing
from typing import Any, Callable
from slypy import errors, metatypes as m
from slypy.typeshed import builtins

F = typing.TypeVar("F", bound=Callable[..., Any])
cache: Callable[[F], F] = functools.cache  # type: ignore
MethodKind = typing.Literal["method", "classmethod", "staticmethod"]
type Function = Callable[..., Any] | types.FunctionType | classmethod[Any, Any, Any] | staticmethod[Any, Any]

TYPING_ATOMS = (
    typing.Any,
    typing.AnyStr,
    typing.LiteralString,
    typing.Never,
    typing.NoReturn,
    typing.Self,
    typing.TypeAlias,
    typing.ParamSpecArgs,
    typing.ParamSpecKwargs,
    typing.TypeAliasType,
    typing.NamedTuple,
    typing.TypedDict,
    typing.Protocol,
)
TYPING_GENERICS = (
    typing.Union,
    types.UnionType,
    typing.Optional,
    typing.Concatenate,
    typing.Literal,
    typing.ClassVar,
    typing.Final,
    typing.Required,
    typing.NotRequired,
    typing.ReadOnly,
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
    typing.overload,
    typing.final,
    typing.no_type_check,
    typing.override,
)


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
        # Only add methods defined directly on class
        if not getattr(v, "__qualname__", "").startswith(f"{t.__name__}."):
            continue

        if isinstance(v, classmethod):
            out[k] = "classmethod", v
        elif isinstance(v, staticmethod):
            out[k] = "staticmethod", v
        elif inspect.isfunction(v):
            out[k] = "method", v

    return out


@dataclass
class Context:
    path: list[Path]
    registry: m.Registry

    def add(self, t: Any | type[inspect._empty]) -> m.MetaType:
        if t is inspect._empty:
            # TODO: convert these to replace(m.unknown, position=)
            return m.unknown.name

        if t in TYPING_ATOMS:
            if t is typing.Self:
                return m.self.name
            raise NotImplementedError()

        if typing.get_args(t):
            return convert_with_args(self, t)

        if isinstance(t, type):
            name = to_name(t)
            if name not in self.registry:
                meta_cls = convert_class(self, t)
                self.registry.add(name, meta_cls)
            return name

        if isinstance(t, types.FunctionType):
            name = to_name(t)
            if name not in self.registry:
                meta_fn = convert_function(self, t, name)
                self.registry.add(name, meta_fn)
            return name

        raise errors.SlyPyError(f"Cannot add type {t}")

    # TODO: will we ever need this?
    # type_name_map: dict[type[Any] | Function, m.Name] = field(default_factory=dict)
    # self.type_name_map[t] = name
    # def get(self, t: type[Any] | Function) -> m.MetaType:
    #     if t not in self.type_name_map:
    #         raise errors.SlyPyError(f"{t} not added")
    #     name = self.type_name_map[t]
    #     return self.registry.get(name)


def convert_with_args(c: Context, t: Any) -> m.MetaType:
    origin, args = typing.get_origin(t), typing.get_args(t)

    if origin in TYPING_GENERICS:
        if origin is typing.Literal:
            literals = list[m.Literal]()
            for arg in args:
                if not isinstance(arg, m.LiteralValueBefore):
                    raise errors.SlyPyError(f"Cannot use {arg} as Literal value")
                if isinstance(arg, enum.Enum):
                    arg = m.EnumValue(m.assert_name(c.add(arg.__class__)), arg.name, arg.value)
                literals.append(m.Literal(arg))
            return m.Union(*literals)
        if origin is typing.Union or origin is types.UnionType:
            return m.Union(*(c.add(arg) for arg in args))
        raise NotImplementedError()
    return m.Bound(c.add(origin), tuple(c.add(arg) for arg in args))


def convert_class(c: Context, t: type[Any]) -> m.Class:
    assert isinstance(t, type)
    name = to_name(t)
    ts = dict[str, m.MetaType]()
    for k, v in typing.get_type_hints(t).items():
        ts[k] = c.add(v)
    for k, [method_kind, method] in methods(t).items():
        method_name = m.Name(f"{name.absolute_name}.{k}")
        v = convert_function(c, method, method_name)
        if method_kind == "method":
            v = m.Method(v)
        elif method_kind == "classmethod":
            v = m.ClassVar(m.Method(v))
        elif method_kind == "staticmethod":
            pass
        else:
            typing.assert_never(method_kind)
        ts[k] = v
    bases = list[m.MetaType]()
    for base in t.__bases__:
        bases.append(c.add(base))
    return m.Class(name, tuple(bases), ts)


def convert_function(c: Context, t: Function, name: m.Name | None) -> m.Fn:
    if isinstance(t, classmethod):
        t = t.__func__
    sig = inspect.signature(typing.cast(Callable[..., Any], t), eval_str=True)
    parameters = list[m.Parameter]()
    for sig_name, sig_param in sig.parameters.items():
        parameter = m.Parameter(
            kind=PARAMETER_KIND_MAP[sig_param.kind],
            name=sig_name,
            t=c.add(sig_param.annotation),
        )
        parameters.append(parameter)
    returns = c.add(sig.return_annotation)
    return m.Fn(name=name, parameters=tuple(parameters), returns=returns)


PARAMETER_KIND_MAP = {
    inspect.Parameter.POSITIONAL_ONLY: m.ParameterKind.POSITIONAL_ONLY,
    inspect.Parameter.POSITIONAL_OR_KEYWORD: m.ParameterKind.POSITIONAL_OR_KEYWORD,
    inspect.Parameter.VAR_POSITIONAL: m.ParameterKind.VAR_POSITIONAL,
    inspect.Parameter.KEYWORD_ONLY: m.ParameterKind.KEYWORD_ONLY,
    inspect.Parameter.VAR_KEYWORD: m.ParameterKind.VAR_KEYWORD,
}
