from dataclasses import dataclass
import enum
from pathlib import Path


class Enum(enum.Enum):
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


@dataclass(frozen=True, kw_only=True)
class Position:
    path: Path
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int


def path_to_module(root: Path, path: Path) -> str:
    s = str(path.relative_to(root))
    if s.endswith(".py"):
        s = s[: -len(".py")]
    if s.endswith(".pyi"):
        s = s[: -len(".pyi")]
    if s.endswith("/__init__"):
        s = s[: -len("/__init__")]
    return s.replace("/", ".")


def read_source(p: Position) -> str:
    lines = p.path.read_text().splitlines()
    if p.lineno == p.end_lineno:
        return lines[p.lineno - 1][p.col_offset : p.end_col_offset]
    return "\n".join(
        [
            lines[p.lineno - 1][p.col_offset :],
            *lines[p.lineno : p.end_lineno - 2],
            lines[p.end_lineno - 1][: p.end_col_offset],
        ]
    )
