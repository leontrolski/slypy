# Development

```shell
uv init --lib --package --build-backend uv --no-pin-python
uv add --dev mypy pytest ruff
uv run mypy src tests
uv run ruff format && uv run ruff check --fix && echo "ruff  ✅"
uv run pytest
```
