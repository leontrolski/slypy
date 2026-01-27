from __future__ import annotations

from dataclasses import dataclass, field, replace
import enum
import typing
from slypy import errors, helpers


@dataclass
class Registry:
    refs: dict[Name, MetaType] = field(default_factory=dict)
    positions: dict[Name, helpers.Position] = field(default_factory=dict)

    def get(self, n: Name) -> MetaType:
        if n not in self:
            raise errors.SlyPyError(f"{n!r} not in registry")
        return self.refs[n]

    def __contains__(self, n: Name) -> bool:
        return n in self.refs

    def add(self, n: Name, t: MetaType, position: helpers.Position | None = None) -> None:
        self.refs[n] = t
        if position is not None:
            self.positions[n] = position


@dataclass(frozen=True)
class Union:
    ts: frozenset[MetaType]

    def __init__(self, *args: MetaType):
        self.__dict__["ts"] = frozenset(args)

    def __repr__(self) -> str:
        return "(" + " | ".join(repr(t) for t in self.ts) + ")"


Never = Union()


@dataclass(frozen=True)
class Intersection:
    ts: frozenset[MetaType]

    def __init__(self, *args: MetaType):
        self.__dict__["ts"] = frozenset(args)

    def __repr__(self) -> str:
        return "(" + " & ".join(repr(t) for t in self.ts) + ")"


@dataclass(frozen=True)
class Not:
    t: MetaType

    def __repr__(self) -> str:
        return f"~{self.t!r}"


@dataclass(frozen=True)
class Tuple:
    ts: tuple[MetaType, ...] | MetaType


@dataclass(frozen=True)
class Literal:
    value: helpers.LiteralValue
    t: MetaType

    def __init__(self, value: helpers.LiteralValue):
        self.__dict__["value"] = value
        self.__dict__["t"] = literal_to_type_name(value)

    def __repr__(self) -> str:
        return f"Literal[{self.value!r}]"


@dataclass(frozen=True)
class Error:
    kind: errors.ErrorKind
    message: str


@dataclass
class _Class:
    name: Name
    bases: tuple[MetaType, ...]
    ts: dict[str, MetaType]
    type_vars: frozenset[TypeVar] = field(default_factory=frozenset)
    bound: dict[TypeVar, MetaType] = field(default_factory=dict)
    _hash: int = 0

    def bind(self, bound: dict[TypeVar, MetaType]) -> typing.Self:
        out = replace(self, bound=bound)
        out.__post_init__()
        return out

    # We assume we never mutate .ts, .bound
    def __post_init__(self) -> None:
        as_tuple = (
            self.bases,
            *self.ts.items(),
            self.type_vars,
            *self.bound.items(),
        )
        self._hash = hash(as_tuple)

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return repr(self.name)


@dataclass
class Class(_Class):
    def __hash__(self) -> int:
        return super().__hash__()


@dataclass
class Protocol(_Class):
    def __hash__(self) -> int:
        return super().__hash__()


class ParameterKind(enum.Enum):
    POSITIONAL_ONLY = 1
    POSITIONAL_OR_KEYWORD = 2
    VAR_POSITIONAL = 3
    KEYWORD_ONLY = 4
    VAR_KEYWORD = 5


# see `inspect.signature`
@dataclass(frozen=True, kw_only=True)
class Parameter:
    kind: ParameterKind
    name: str
    t: MetaType


@dataclass(frozen=True, kw_only=True)
class Fn:
    parameters: tuple[Parameter, ...]
    returns: MetaType


@dataclass(frozen=True)
class TypeVar:
    name: str
    at: Name
    bound: MetaType | None
    constraints: tuple[MetaType, ...]
    variance: typing.Literal["invariant", "covariant", "contravariant"]


@dataclass(frozen=True)
class Type:
    t: MetaType


@dataclass(frozen=True)
class Name:
    absolute_name: str

    def __repr__(self) -> str:
        return self.absolute_name

    @property
    def module(self) -> str:
        return self.absolute_name.partition("->")[0]

    @property
    def value(self) -> str | None:
        return self.absolute_name.partition("->")[2] or None


Any = Class(Name("builtins->object"), (), {})
Unknown = Class(Name("<unknown>"), (), {})

MetaType = (
    Literal  #
    | Error
    | Tuple
    | Class
    | Protocol
    | Fn
    | Union
    | Intersection
    | Not
    | Type
    | TypeVar
    | Name
)


def python_to_meta(t: type[typing.Any]) -> Name:
    if isinstance(t, type):
        return Name(f"{t.__module__}->{t.__name__}")
    raise errors.SlyPyError(f"Unhandled type: {t}")


def literal_to_type_name(value: helpers.LiteralValue) -> Name:
    if isinstance(value, bool):
        return Name("builtins->bool")
    if isinstance(value, int):
        return Name("builtins->int")
    if isinstance(value, float):
        return Name("builtins->float")
    if isinstance(value, bytes):
        return Name("builtins->bytes")
    if isinstance(value, str):
        return Name("builtins->str")
    if value is None:
        return Name("builtins->NoneType")
    if isinstance(value, helpers.EnumValue):
        return Name(f"{value.absolute_name}.{value.name}")
    typing.assert_never(value)
