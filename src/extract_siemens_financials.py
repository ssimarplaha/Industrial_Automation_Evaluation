#!/usr/bin/env python3
"""Public CLI/import wrapper for the Siemens financial extractor."""

from __future__ import annotations

from siemens_extractor import extract_all, int_tokens, main

__all__ = ["extract_all", "int_tokens", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
