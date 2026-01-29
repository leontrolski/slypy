# TODO - required for MVP

- Add end to end `issubtype` tests for everything.
- Work through `Unsupported`, `Passthrough`.
- Infer all `INFER`s
- Replace loads of `raise errors.` with `return errors.`

# TODO - nice to haves

- `dataclass_transform` + `dataclass.field(...)`
- `overload`
- `TypedDict` + `Required` + `NotRequired` + `ReadOnly`
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
