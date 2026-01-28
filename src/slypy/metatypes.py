from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
import enum
import typing
from slypy import errors, helpers


@dataclass
class Registry:
    refs: dict[Name, MetaType] = field(default_factory=dict)

    def get(self, n: Name) -> MetaType:
        if n not in self:
            raise errors.SlyPyError(f"{n!r} not in registry")
        return self.refs[n]

    def __contains__(self, n: Name) -> bool:
        return n in self.refs

    def add(self, n: Name, t: MetaType) -> None:
        self.refs[n] = t


@dataclass(frozen=True)
class _WithPosition:
    _: KW_ONLY
    position: helpers.Position | None = field(
        default=None,
        hash=False,
        compare=False,
    )


@dataclass(frozen=True)
class Union(_WithPosition):
    ts: frozenset[MetaType]

    def __init__(self, *args: MetaType):
        self.__dict__["ts"] = frozenset(args)

    def __repr__(self) -> str:
        return "(" + " | ".join(repr(t) for t in self.ts) + ")"


Never = Union()


@dataclass(frozen=True)
class Intersection(_WithPosition):
    ts: frozenset[MetaType]

    def __init__(self, *args: MetaType):
        self.__dict__["ts"] = frozenset(args)

    def __repr__(self) -> str:
        return "(" + " & ".join(repr(t) for t in self.ts) + ")"


@dataclass(frozen=True)
class Not(_WithPosition):
    t: MetaType

    def __repr__(self) -> str:
        return f"~{self.t!r}"


@dataclass(frozen=True)
class Tuple(_WithPosition):
    ts: tuple[MetaType, ...] | MetaType


@dataclass(frozen=True)
class EnumValue:
    t: Name
    name: str
    value: str | int


LiteralValueBefore = bool | int | float | bytes | str | enum.Enum | None
LiteralValue = bool | int | float | bytes | str | EnumValue | None


@dataclass(frozen=True)
class Literal(_WithPosition):
    value: LiteralValue
    t: MetaType

    def __init__(self, value: LiteralValue) -> None:
        self.__dict__["value"] = value
        self.__dict__["t"] = literal_to_type_name(value)

    def __repr__(self) -> str:
        return f"Literal[{self.value!r}]"


@dataclass(frozen=True)
class Error(_WithPosition):
    kind: errors.ErrorKind
    message: str


class ParameterKind(enum.Enum):
    POSITIONAL_ONLY = 1
    POSITIONAL_OR_KEYWORD = 2
    VAR_POSITIONAL = 3
    KEYWORD_ONLY = 4
    VAR_KEYWORD = 5


# see `inspect.signature`
@dataclass(frozen=True, kw_only=True)
class Parameter(_WithPosition):
    kind: ParameterKind
    name: str | None
    t: MetaType


@dataclass(frozen=True, kw_only=True)
class Fn(_WithPosition):
    name: Name | None = None
    parameters: tuple[Parameter, ...] | None
    returns: MetaType


@dataclass(frozen=True)
class TypeVar(_WithPosition):
    name: str
    at: Name
    bound: MetaType | None
    constraints: tuple[MetaType, ...]
    variance: typing.Literal["invariant", "covariant", "contravariant"]


@dataclass(frozen=True)
class Bound(_WithPosition):
    t: MetaType
    bound: tuple[MetaType, ...]


@dataclass(frozen=True)
class Type(_WithPosition):
    t: MetaType


@dataclass(frozen=True)
class ClassVar(_WithPosition):
    t: MetaType


@dataclass(frozen=True)
class Method(_WithPosition):
    t: Fn


@dataclass
class _Class:
    name: Name
    bases: tuple[MetaType, ...]
    ts: dict[str, MetaType]
    type_vars: frozenset[TypeVar] = field(default_factory=frozenset)
    _hash: int = field(repr=False, compare=False, default=0)

    position: helpers.Position | None = None

    # We assume we never mutate .ts, .bound
    def __post_init__(self) -> None:
        as_tuple = (
            self.name,
            self.bases,
            *self.ts.items(),
            self.type_vars,
            # *self.bound.items(),
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


@dataclass(frozen=True)
class Name(_WithPosition):
    absolute_name: str

    def __repr__(self) -> str:
        return self.absolute_name

    @property
    def module(self) -> str:
        return self.absolute_name.partition("->")[0]

    @property
    def value(self) -> str | None:
        return self.absolute_name.partition("->")[2] or None


@dataclass(frozen=True)
class Any(_WithPosition): ...


@dataclass(frozen=True)
class Unknown(_WithPosition): ...


@dataclass(frozen=True)
class Self(_WithPosition): ...


MetaTypeAtoms = (
    Any  #
    | Unknown
    | Self
)
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
    | ClassVar
    | Method
    | TypeVar
    | Bound
    | Name
    | MetaTypeAtoms
)


def python_to_meta(t: type[typing.Any]) -> Name:
    if isinstance(t, type):
        return Name(f"{t.__module__}->{t.__name__}")
    raise errors.SlyPyError(f"Unhandled type: {t}")


def literal_to_type_name(value: LiteralValue) -> Name:
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
    if isinstance(value, EnumValue):
        return value.t
    typing.assert_never(value)


def assert_name(t: MetaType) -> Name:
    if not isinstance(t, Name):
        raise errors.SlyPyError(f"{t} is not a Name")
    return t
