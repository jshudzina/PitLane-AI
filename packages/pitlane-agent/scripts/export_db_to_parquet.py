#!/usr/bin/env python3
"""One-time migration: export pitlane.duckdb to year-partitioned Parquet files.

Reads from a legacy pitlane.duckdb and writes Zstd-compressed Parquet files
into the target data directory using the same layout expected by the current
Parquet-based data access layer:

    race_entries_{year}.parquet       — one file per year
    qualifying_entries_{year}.parquet — one file per year
    elo_snapshots_{year}.parquet      — one file per year
    elo_model_state.parquet           — single file (all years)
    session_stats.parquet             — single file (all years)

Usage:
    python scripts/export_db_to_parquet.py
    python scripts/export_db_to_parquet.py --db-path /path/to/pitlane.duckdb
    python scripts/export_db_to_parquet.py --data-dir /path/to/output/
    python scripts/export_db_to_parquet.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

_DEFAULT_DB = Path(__file__).parent.parent / "src" / "pitlane_agent" / "data" / "pitlane.duckdb"
_DEFAULT_DATA_DIR = _DEFAULT_DB.parent

_YEAR_PARTITIONED = [
    "race_entries",
    "qualifying_entries",
    "elo_snapshots",
]

_SINGLE_FILE = [
    "elo_model_state",
    "session_stats",
]


def export(db_path: Path, data_dir: Path, *, dry_run: bool = False) -> None:
    if not db_path.exists():
        print(f"ERROR: DuckDB file not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    data_dir.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        for table in _YEAR_PARTITIONED:
            years = [r[0] for r in con.execute(f"SELECT DISTINCT year FROM {table} ORDER BY year").fetchall()]
            for year in years:
                out_path = data_dir / f"{table}_{year}.parquet"
                if dry_run:
                    count = con.execute(f"SELECT COUNT(*) FROM {table} WHERE year = {year}").fetchone()[0]
                    print(f"[dry-run] would write {out_path} ({count} rows)")
                else:
                    con.execute(
                        f"COPY (SELECT * FROM {table} WHERE year = {year} ORDER BY year, round)"
                        f" TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
                    )
                    size_kb = out_path.stat().st_size // 1024
                    print(f"  wrote {out_path.name} ({size_kb} KB)")

        for table in _SINGLE_FILE:
            out_path = data_dir / f"{table}.parquet"
            if dry_run:
                count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"[dry-run] would write {out_path} ({count} rows)")
            else:
                con.execute(
                    f"COPY (SELECT * FROM {table})"
                    f" TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
                )
                size_kb = out_path.stat().st_size // 1024
                print(f"  wrote {out_path.name} ({size_kb} KB)")

    finally:
        con.close()

    if not dry_run:
        total_kb = sum(p.stat().st_size for p in data_dir.glob("*.parquet")) // 1024
        print(f"\nDone. Total Parquet size: {total_kb} KB")
        print(f"You can now delete {db_path} and add *.duckdb to .gitignore.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db-path", type=Path, default=_DEFAULT_DB, help="Path to pitlane.duckdb")
    parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR, help="Output directory for Parquet files")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be written without writing")
    args = parser.parse_args()

    print(f"Source: {args.db_path}")
    print(f"Output: {args.data_dir}")
    if args.dry_run:
        print("(dry run — no files will be written)\n")
    else:
        print()

    export(args.db_path, args.data_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
