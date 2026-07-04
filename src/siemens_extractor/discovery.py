from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from .models import PdfDocument
from .periods import quarter_code


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_pdfs(input_dir: Path) -> tuple[list[tuple[Path, str]], list[dict[str, str]]]:
    seen: dict[str, Path] = {}
    duplicates: list[dict[str, str]] = []
    result: list[tuple[Path, str]] = []
    for path in sorted(input_dir.glob("*.pdf")) + sorted(input_dir.glob("*.PDF")):
        digest = sha256(path)
        if digest in seen:
            duplicates.append(
                {"duplicate_pdf": path.name, "kept_pdf": seen[digest].name, "sha256": digest}
            )
            continue
        seen[digest] = path
        result.append((path, digest))
    return result, duplicates


def pdf_fiscal_period(path: Path) -> tuple[int, int]:
    match = re.search(r"(?P<year>20\d{2})-q(?P<quarter>[1-4])", path.name, re.I)
    if not match:
        raise ValueError(f"Cannot detect fiscal period from filename: {path.name}")
    return int(match.group("year")), int(match.group("quarter"))


def extract_pages(path: Path) -> list[str]:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - exercised only without deps.
        raise SystemExit(
            "Missing dependency: pdfplumber. Install it with `python3 -m pip install -r requirements.txt`."
        ) from exc

    logging.getLogger("pdfminer").setLevel(logging.ERROR)
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text(x_tolerance=1, y_tolerance=3) or "")
    return pages


def load_documents(input_dir: Path) -> tuple[list[PdfDocument], list[dict[str, str]]]:
    unique, duplicates = unique_pdfs(input_dir)
    documents: list[PdfDocument] = []
    for path, digest in unique:
        fiscal_year, quarter = pdf_fiscal_period(path)
        documents.append(
            PdfDocument(
                path=path,
                sha256=digest,
                fiscal_year=fiscal_year,
                quarter=quarter,
                code=quarter_code(quarter, fiscal_year),
                pages=extract_pages(path),
            )
        )
    return documents, duplicates
