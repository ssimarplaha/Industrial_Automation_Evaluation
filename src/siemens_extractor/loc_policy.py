"""Line-count policy enforcement for maintained Siemens extractor files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SOFT_LINE_LIMIT = 650
HARD_LINE_LIMIT = 675

SCANNED_SUFFIXES = {".py", ".md"}
SCANNED_ROOT_FILES = {"AGENTS.md"}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "data",
    "output",
}


@dataclass(frozen=True)
class LineCountViolation:
    """A soft or hard line-count policy violation for one maintained file."""

    path: Path
    line_count: int
    limit: int
    severity: str
    message: str


def maintained_files(root: Path) -> list[Path]:
    """Return source, test, and agent-doc files covered by the LOC policy."""
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if relative.parts[0] == "src" and path.suffix == ".py":
            files.append(path)
            continue
        if relative.parts[0] == ".agents" and path.suffix in SCANNED_SUFFIXES:
            files.append(path)
            continue
        if str(relative) in SCANNED_ROOT_FILES:
            files.append(path)
    return sorted(files)


def count_lines(path: Path) -> int:
    """Count physical lines in a UTF-8 maintained file."""
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def line_count_violations(
    root: Path,
    allowlist: set[str] | None = None,
) -> list[LineCountViolation]:
    """Collect line-count policy violations, honoring soft-limit allowlists."""
    allowed = allowlist or set()
    violations: list[LineCountViolation] = []
    for path in maintained_files(root):
        relative = path.relative_to(root).as_posix()
        line_count = count_lines(path)
        if line_count > HARD_LINE_LIMIT:
            violations.append(
                LineCountViolation(
                    path=path,
                    line_count=line_count,
                    limit=HARD_LINE_LIMIT,
                    severity="hard",
                    message=(
                        f"{relative} has {line_count} lines, above the hard ceiling of "
                        f"{HARD_LINE_LIMIT}. Split this file before merging."
                    ),
                )
            )
        elif line_count > SOFT_LINE_LIMIT and relative not in allowed:
            violations.append(
                LineCountViolation(
                    path=path,
                    line_count=line_count,
                    limit=SOFT_LINE_LIMIT,
                    severity="soft",
                    message=(
                        f"{relative} has {line_count} lines, above the target limit of "
                        f"{SOFT_LINE_LIMIT}. Split this file before merging or add an explicit allowlist entry."
                    ),
                )
            )
    return violations
