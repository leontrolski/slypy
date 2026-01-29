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
    position: helpers.Position | None = None


@dataclass(frozen=True)
class Union(_WithPosition):
    ts: frozenset[MetaType]

    @classmethod
    def make(cls, *args: MetaType, position: helpers.Position | None = None) -> typing.Self:
        return cls(
            ts=frozenset(args),
            position=position,
        )

    def __repr__(self) -> str:
        return "(" + " | ".join(repr(t) for t in self.ts) + ")"


@dataclass(frozen=True)
class Intersection(_WithPosition):
    ts: frozenset[MetaType]

    @classmethod
    def make(cls, *args: MetaType, position: helpers.Position | None = None) -> typing.Self:
        return cls(
            ts=frozenset(args),
            position=position,
        )

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

    @classmethod
    def make(cls, value: LiteralValue, position: helpers.Position | None = None) -> typing.Self:
        return cls(
            value=value,
            t=literal_to_type_name(value),
            position=position,
        )

    def __repr__(self) -> str:
        return f"Literal[{self.value!r}]"


@dataclass(frozen=True)
class Error(_WithPosition):
    kind: errors.ErrorKind
    message: str


class ParameterKind(helpers.Enum):
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


class Variance(helpers.Enum):
    INVARIANT = "INVARIANT"
    COVARIANT = "COVARIANT"
    CONTRAVARIANT = "CONTRAVARIANT"
    INFER = "INFER"

    def check_inferred(self) -> typing.Literal[Variance.INVARIANT, Variance.COVARIANT, Variance.CONTRAVARIANT]:
        if self is Variance.INFER:
            raise errors.SlyPyError("Variance not inferred yet")
        return self


@dataclass(frozen=True)
class TypeVar(_WithPosition):
    name: str
    at: Name
    # We set to `Any` for `bound=None` and `tuple(...)` for `constraints=...`
    bound: MetaType | tuple[MetaType, ...]
    variance: Variance


@dataclass(frozen=True)
class Bound(_WithPosition):
    t: MetaType
    bound: tuple[MetaType, ...]


@dataclass(frozen=True)
class ReadOnly(_WithPosition):
    t: MetaType


@dataclass(frozen=True)
class Type(_WithPosition):
    t: MetaType


@dataclass(frozen=True)
class ClassVar(_WithPosition):
    t: MetaType


@dataclass(frozen=True)
class Method(_WithPosition):
    t: MetaType  # Should always be `Fn`


@dataclass
class _Class:
    name: Name
    bases: tuple[MetaType, ...]
    ts: dict[str, MetaType]
    type_vars: tuple[TypeVar, ...] = ()
    _hash: int = field(repr=False, compare=False, default=0)

    position: helpers.Position | None = None

    # We assume we never mutate .ts
    def __post_init__(self) -> None:
        as_tuple = (
            self.name,
            self.bases,
            *self.ts.items(),
            self.type_vars,
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
    | ReadOnly
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


def walk(t: MetaType, f: typing.Callable[[MetaType], MetaType]) -> MetaType:
    t = f(t)
    if isinstance(t, Any | Unknown | Self | Name | Error):
        return t
    elif isinstance(t, Not | Type | ClassVar | ReadOnly | Method):
        return t.__class__(
            t=walk(t.t, f),
            position=t.position,
        )
    elif isinstance(t, Literal):
        return t.__class__(
            value=t.value,
            t=t.t,
            position=t.position,
        )
    elif isinstance(t, Union | Intersection):
        return t.__class__(
            ts=frozenset(walk(u, f) for u in t.ts),
            position=t.position,
        )
    elif isinstance(t, Tuple):
        return t.__class__(
            ts=tuple(walk(u, f) for u in t.ts) if isinstance(t.ts, tuple) else walk(t.ts, f),
            position=t.position,
        )
    elif isinstance(t, Fn):
        return t.__class__(
            name=t.name,
            parameters=None
            if t.parameters is None
            else tuple(
                Parameter(
                    kind=p.kind,
                    name=p.name,
                    t=walk(p.t, f),
                    position=p.position,
                )
                for p in t.parameters
            ),
            returns=walk(t.returns, f),
            position=t.position,
        )
    elif isinstance(t, TypeVar):
        return t.__class__(
            name=t.name,
            at=t.at,
            bound=tuple(walk(b, f) for b in t.bound) if isinstance(t.bound, tuple) else walk(t.bound, f),
            variance=t.variance,
            position=t.position,
        )
    elif isinstance(t, Bound):
        return t.__class__(
            t=walk(t.t, f),
            bound=tuple(walk(b, f) for b in t.bound),
            position=t.position,
        )
    elif isinstance(t, Class | Protocol):
        return t.__class__(
            name=t.name,
            bases=tuple(walk(b, f) for b in t.bases),
            ts={k: walk(v, f) for k, v in t.ts.items()},
            type_vars=tuple(typing.cast(TypeVar, walk(v, f)) for v in t.type_vars),
            position=t.position,
        )
    typing.assert_never(t)
