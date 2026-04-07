from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field, replace
import enum
import typing
from slypy import errors, helpers


@dataclass
class Registry:
    refs: dict[NameClass | NameFn, MetaType] = field(default_factory=dict)

    def get(self, n: NameClass | NameFn) -> MetaType:
        if n not in self:
            raise errors.SlyPyError(f"{n!r} not in registry")
        return self.refs[n]

    def __contains__(self, n: NameClass | NameFn) -> bool:
        return n in self.refs

    def add(self, n: NameClass | NameFn, t: MetaType) -> None:
        self.refs[n] = t


@dataclass(frozen=True)
class _WithPosition:
    _: KW_ONLY
    position: helpers.Position | None = field(default=None, repr=False)


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

    def is_any(self) -> bool:
        return not self.ts

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
    t: NameClass
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
    VAR_POSITIONAL = 3  # corresponds to *args
    KEYWORD_ONLY = 4  # those which appear after * or *args
    VAR_KEYWORD = 5  # corresponds to **kwargs


# see `inspect.signature`
@dataclass(frozen=True, kw_only=True)
class Parameter(_WithPosition):
    kind: ParameterKind
    name: str | None
    t: MetaType
    has_default: bool = False

    def __repr__(self) -> str:
        t = repr(self.t)
        if self.kind is ParameterKind.VAR_POSITIONAL:
            t = f"*{t}"
        if self.kind is ParameterKind.VAR_KEYWORD:
            t = f"**{t}"
        name = ""
        if self.name is not None:
            name = f"{self.name}: "
        return f"{name}{t}"


@dataclass(frozen=True, kw_only=True)
class Fn(_WithPosition):
    name: NameFn | None = None
    parameters: tuple[Parameter, ...]
    returns: MetaType

    def __repr__(self) -> str:
        parameters = ", ".join(repr(p) for p in self.parameters)
        if self.name is None:
            return f"Callable[[{parameters}], {repr(self.returns)}]"
        return f"def {self.name.value}({parameters}) -> {repr(self.returns)}"


@dataclass(frozen=True)
class TypeVar(_WithPosition):
    name: str
    at: NameClass | NameFn
    # We set to `Any` for `bound=None` and `tuple(...)` for `constraints=...`
    bound: MetaType | tuple[MetaType, ...]


@dataclass(frozen=True)
class Bound(_WithPosition):
    """Eg: list[int]"""

    t: NameClass | Class | Protocol
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
    t: Fn  # Should always be `Fn`

    def as_fn(self) -> Fn:
        if not isinstance(self.t, Fn):
            raise errors.SlyPyError("Expected Fn")
        return replace(self.t, parameters=self.t.parameters[1:])


@dataclass
class _Class:
    name: NameClass
    bases: tuple[MetaType, ...]
    ts: dict[str, MetaType]
    type_vars: tuple[TypeVar, ...] = ()
    _hash: int = field(repr=False, compare=False, default=0)

    position: helpers.Position | None = None

    def without_type_vars(self) -> typing.Self:
        return replace(self, type_vars=())

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


@dataclass
class Class(_Class):
    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return repr(self.name)


@dataclass
class Protocol(_Class):
    def __hash__(self) -> int:
        return super().__hash__()

    def __repr__(self) -> str:
        return f"{repr(self.name)}(Protocol)"

    def as_call(self) -> Fn | None:
        if (call := self.ts.get("__call__")) and isinstance(call, Method):
            return call.as_fn()
        return None


@dataclass(frozen=True)
class _Name(_WithPosition):
    absolute_name: str

    def __repr__(self) -> str:
        return self.absolute_name

    @property
    def module(self) -> str:
        return self.absolute_name.partition("->")[0]

    @property
    def value(self) -> str:
        return self.absolute_name.partition("->")[2] or "<no-name>"


@dataclass(frozen=True)
class NameClass(_Name): ...


@dataclass(frozen=True)
class NameFn(_Name): ...


@dataclass(frozen=True)
class Unknown(_WithPosition): ...


@dataclass(frozen=True)
class Self(_WithPosition): ...


MetaType = (
    NameClass  #
    | NameFn
    | Class
    | Protocol
    | Literal
    | Tuple
    | Fn
    | Method
    | ClassVar
    | TypeVar
    | Bound
    | ReadOnly
    | Type
    | Union
    | Intersection
    | Not
    | Self
    | Unknown  #
    | Error
)


def python_to_meta(t: type[typing.Any]) -> NameClass:
    if isinstance(t, type):
        return NameClass(f"{t.__module__}->{t.__name__}")
    raise errors.SlyPyError(f"Unhandled type: {t}")


def literal_to_type_name(value: LiteralValue) -> NameClass:
    if isinstance(value, bool):
        return NameClass("builtins->bool")
    if isinstance(value, int):
        return NameClass("builtins->int")
    if isinstance(value, float):
        return NameClass("builtins->float")
    if isinstance(value, bytes):
        return NameClass("builtins->bytes")
    if isinstance(value, str):
        return NameClass("builtins->str")
    if value is None:
        return NameClass("builtins->NoneType")
    if isinstance(value, EnumValue):
        return value.t
    typing.assert_never(value)


def assert_name(t: MetaType) -> NameClass:
    if not isinstance(t, NameClass):
        raise errors.SlyPyError(f"{t} is not a NameClass")
    return t

def assert_name_fn(t: MetaType) -> NameFn:
    if not isinstance(t, NameFn):
        raise errors.SlyPyError(f"{t} is not a NameFn")
    return t


def walk(t: MetaType, f: typing.Callable[[MetaType], MetaType]) -> MetaType:
    t = f(t)
    if isinstance(t, Unknown | Self | NameClass | NameFn | Error):
        return t
    elif isinstance(t, Not | Type | ClassVar | ReadOnly | Method):
        return t.__class__(
            t=walk(t.t, f),  # type: ignore[arg-type]
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
            position=t.position,
        )
    elif isinstance(t, Bound):
        return t.__class__(
            t=walk(t.t, f),  # type: ignore[arg-type]
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
