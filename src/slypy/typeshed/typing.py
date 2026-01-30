# https://leontrolski.github.io/protocol.html
from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T")


class Iterator(Protocol[T]):
    def __next__(self) -> T: ...
    def __iter__(self) -> Iterator[T]: ...


class Iterable(Protocol[T]):
    def __iter__(self) -> Iterator[T]: ...
