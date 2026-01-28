from dataclasses import dataclass
import functools
import inspect
from pathlib import Path
from types import FunctionType
from typing import assert_never, Any, Callable, Literal, TypeVar, cast, get_type_hints
from slypy import metatypes as m
from slypy.typeshed import builtins

F = TypeVar("F", bound=Callable[..., Any])
cache: Callable[[F], F] = functools.cache  # type: ignore
MethodKind = Literal["method", "classmethod", "staticmethod"]
type Function = Callable[..., Any] | FunctionType | classmethod[Any, Any, Any] | staticmethod[Any, Any]


@cache
def to_name(t: type[Any] | Function) -> m.Name:
    module = t.__module__
    if module == builtins.__name__:
        module = "builtins"
    return m.Name(f"{module}->{t.__name__}")


def methods(t: type[Any]) -> dict[str, tuple[MethodKind, Any]]:
    out = dict[str, tuple[MethodKind, Function]]()
    for k, v in t.__dict__.items():
        if isinstance(v, classmethod):
            out[k] = "classmethod", v
        elif isinstance(v, staticmethod):
            out[k] = "staticmethod", v
        elif inspect.isfunction(v):
            out[k] = "method", v

    # Only return methods defined directly on class
    prefix = f"{t.__name__}."
    return {k: (s, v) for k, (s, v) in out.items() if v.__qualname__.startswith(prefix)}


@dataclass
class Context:
    path: list[Path]
    registry: m.Registry

    def add(self, t: type[Any] | Function | type[inspect._empty]) -> m.Name:
        if t is inspect._empty:
            return m.unknown.name
        name = to_name(t)
        if name not in self.registry:
            meta_type: m.MetaType
            if isinstance(t, type):
                meta_type = convert_type(self, t)
            else:
                meta_type = convert_function(self, t)
            self.registry.add(name, meta_type)
        return name

    # TODO: will we ever need this?
    # type_name_map: dict[type[Any] | Function, m.Name] = field(default_factory=dict)
    # self.type_name_map[t] = name
    # def get(self, t: type[Any] | Function) -> m.MetaType:
    #     if t not in self.type_name_map:
    #         raise errors.SlyPyError(f"{t} not added")
    #     name = self.type_name_map[t]
    #     return self.registry.get(name)


def convert_type(c: Context, t: type[Any]) -> m.Class:
    if not isinstance(t, type):
        raise NotImplementedError()
    name = to_name(t)
    ts = dict[str, m.MetaType]()
    for k, v in get_type_hints(t).items():
        1 / 0
    for k, [kind, v] in methods(t).items():
        if kind == "method":
            ...
        elif kind == "classmethod":
            ...
        elif kind == "staticmethod":
            ...
        else:
            assert_never(kind)
        print(k, kind, v)
    bases = list[m.Name]()
    for base in t.__bases__:
        bases.append(c.add(base))
    return m.Class(name, tuple(bases), ts)


def convert_function(c: Context, t: Function) -> m.Fn:
    name = to_name(t)
    sig = inspect.signature(cast(Callable[..., Any], t), eval_str=True)
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
