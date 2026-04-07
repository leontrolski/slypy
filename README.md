# Notes

- `Any` AKA `builtins->object` is equivalent to `Intersection([])`
- `Any` is distinct from `Unknown` - see `ty` docs.
- `Never` is equivalent to `Union([])`
- `TypeVar(covariant=True, contravariant=True)` are ignored and we always pretend `TypeVar(infer_variance=True)` as per the new `class MyClass[T]:` syntax.

# TODO - required for MVP

- Handle parent classes/generics in `issubtype`.
- Work through `Unsupported`, `Passthrough`.
- Tests for Method Resolution Order
- `converters.Scope` - I'm a bit worried about the `str` -> `TypeVar` map. What if there's `Generic[a.T, b.T]` - is that even allowed? Is the scoping remotely the same as lexical scoping? It shouldn't follow `Name`s or something.
- Infer variance.
- Replace most `raise errors.` with `return errors.`

# TODO - nice to haves

- `overload`
- `dataclass_transform` + `dataclass.field(...)`
- `TypedDict` + `Required` + `NotRequired` + `ReadOnly`
- Copy tests from `ty`
- `NamedTuple`
- `TypeIs`
- `TypeVarTuple` + `Unpack`
- `NewType`
- `Final`
- `final`
- `AnyStr`
- `LiteralString`
- `Never`
- `NoReturn`
- `TypeAlias`
- `ParamSpec` + `ParamSpecArgs` + `ParamSpecKwargs`
- `TypeAliasType`
- `Concatenate`
- `TypeGuard`
- `no_type_check`
- `override`

# Development

```shell
uv init --lib --package --build-backend uv --no-pin-python
uv add --dev mypy pytest ruff
uv run mypy src tests
uv run ruff format && uv run ruff check --fix && echo "ruff  ✅"
uv run pytest
```
