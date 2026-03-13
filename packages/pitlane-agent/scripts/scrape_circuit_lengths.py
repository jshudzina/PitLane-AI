#!/usr/bin/env python3
"""One-time scraper: extract F1 circuit lengths from Wikipedia.

Uses only Python stdlib — no extra dependencies required.
Prints a formatted Python dict literal to stdout for review and
pasting into circuits.py.

Usage:
    python packages/pitlane-agent/scripts/scrape_circuit_lengths.py
"""

from __future__ import annotations

import re
import sys
import urllib.request
from datetime import date
from html.parser import HTMLParser

URL = "https://en.wikipedia.org/wiki/List_of_Formula_One_circuits"


def _clean(text: str) -> str:
    """Strip footnote markers, refs, and whitespace."""
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"[*†‡§]", "", text)
    return " ".join(text.split())


def _parse_km(cell: str) -> float | None:
    """Extract a numeric km value from a cell like '5.412 km (3.363 mi)'."""
    m = re.search(r"(\d+\.\d+)", cell)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+)", cell)
    if m:
        return float(m.group(1))
    return None


class TableParser(HTMLParser):
    """Collect all <table> contents as lists of row-lists."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = 0
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "table":
            self._in_table += 1
            if self._in_table == 1:
                self._current_table = []
        elif tag in ("tr",) and self._in_table == 1:
            self._in_row = True
            self._current_row = []
        elif tag in ("td", "th") and self._in_table == 1:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self._in_table == 1:
                self.tables.append(self._current_table)
            self._in_table -= 1
        elif tag == "tr" and self._in_table == 1:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._in_row = False
        elif tag in ("td", "th") and self._in_table == 1:
            self._current_row.append(_clean("".join(self._current_cell)))
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_cell.append(data)


def _find_circuit_table(tables: list[list[list[str]]]) -> list[list[str]] | None:
    """Return the table whose header row contains both circuit/location and length columns."""
    for table in tables:
        if not table:
            continue
        header = [c.lower() for c in table[0]]
        has_length = any("length" in h or "km" in h for h in header)
        has_circuit = any("circuit" in h or "location" in h for h in header)
        if has_length and has_circuit and len(table) > 10:
            return table
    return None


def main() -> None:
    print(f"# Fetching: {URL}", file=sys.stderr)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; pitlane-scraper/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    parser = TableParser()
    parser.feed(html)
    print(f"# Parsed {len(parser.tables)} tables", file=sys.stderr)

    table = _find_circuit_table(parser.tables)
    if table is None:
        print("ERROR: could not find the circuits table", file=sys.stderr)
        sys.exit(1)

    header = [c.lower() for c in table[0]]
    print(f"# Header: {table[0]}", file=sys.stderr)

    # Locate column indices
    location_idx = next(
        (i for i, h in enumerate(header) if "location" in h),
        next((i for i, h in enumerate(header) if "circuit" in h), None),
    )
    length_idx = next(
        (i for i, h in enumerate(header) if "length" in h),
        next((i for i, h in enumerate(header) if "km" in h), None),
    )

    if location_idx is None or length_idx is None:
        print(f"ERROR: could not find location/length columns in {table[0]}", file=sys.stderr)
        sys.exit(1)

    print(
        f"# location col={location_idx} ('{table[0][location_idx]}'),"
        f" length col={length_idx} ('{table[0][length_idx]}')",
        file=sys.stderr,
    )

    results: dict[str, float] = {}
    for row in table[1:]:
        if len(row) <= max(location_idx, length_idx):
            continue
        location = row[location_idx].lower().strip()
        if not location or location in ("location", "nan"):
            continue
        km = _parse_km(row[length_idx])
        if km is None:
            print(f"# SKIP (no length): {location!r} raw={row[length_idx]!r}", file=sys.stderr)
            continue
        # Keep the longer value when duplicates exist (GP layout vs shorter variants)
        if location not in results or km > results[location]:
            results[location] = km

    print(f"# Extracted {len(results)} circuits", file=sys.stderr)

    today = date.today().isoformat()
    print(f"# Generated by scripts/scrape_circuit_lengths.py on {today}")
    print("# Source: https://en.wikipedia.org/wiki/List_of_Formula_One_circuits")
    print("CIRCUIT_LENGTHS_KM: dict[str, float] = {")
    for location, km in sorted(results.items()):
        print(f'    "{location}": {km},')
    print("}")


if __name__ == "__main__":
    main()
