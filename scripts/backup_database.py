#!/usr/bin/env python3
"""
404 FOUNDERS — Database Backup & Integrity Engine
Performs safe, live WAL-compatible SQLite database backups using sqlite3.Connection.backup.
Validates database integrity (PRAGMA integrity_check), counts table records,
and writes verified backups to the backups/ directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from database.connection import DEFAULT_DB_PATH, DatabaseManager


def check_integrity(conn: sqlite3.Connection) -> Tuple[bool, str]:
    """Runs PRAGMA integrity_check and returns status."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    rows = cursor.fetchall()
    if len(rows) == 1 and rows[0][0] == "ok":
        return True, "ok"
    return False, "; ".join(str(r[0]) for r in rows)


def inspect_table_counts(conn: sqlite3.Connection) -> dict:
    """Inspects row counts for all user and system tables."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]
    counts = {}
    for tbl in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM \"{tbl}\"")
            counts[tbl] = cursor.fetchone()[0]
        except Exception as e:
            counts[tbl] = f"Error: {e}"
    return counts


def perform_backup(source_path: Path, destination_path: Path) -> dict:
    """Performs an atomic SQLite online backup and validates the destination."""
    if not source_path.exists():
        raise FileNotFoundError(f"Source database file not found: {source_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to source database: {source_path}")
    src_conn = sqlite3.connect(str(source_path))

    # 1. Pre-backup integrity check
    src_ok, src_msg = check_integrity(src_conn)
    if not src_ok:
        src_conn.close()
        raise RuntimeError(f"Source database integrity check failed: {src_msg}")
    print("  ✓ Source database PRAGMA integrity_check: PASSED")

    src_counts = inspect_table_counts(src_conn)

    # 2. Perform online atomic backup
    print(f"Backing up to: {destination_path} ...")
    dst_conn = sqlite3.connect(str(destination_path))
    try:
        src_conn.backup(dst_conn, pages=100)
        dst_conn.commit()
    finally:
        src_conn.close()

    # 3. Post-backup integrity check on destination
    dst_ok, dst_msg = check_integrity(dst_conn)
    if not dst_ok:
        dst_conn.close()
        raise RuntimeError(f"Backup file integrity check failed: {dst_msg}")
    print("  ✓ Target backup PRAGMA integrity_check: PASSED")

    dst_counts = inspect_table_counts(dst_conn)
    dst_conn.close()

    size_bytes = destination_path.stat().st_size
    print(f"  ✓ Backup file successfully verified ({size_bytes} bytes)")

    return {
        "status": "SUCCESS",
        "source": str(source_path),
        "destination": str(destination_path),
        "size_bytes": size_bytes,
        "source_integrity": src_msg,
        "backup_integrity": dst_msg,
        "table_counts": dst_counts,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="404 FOUNDERS Database Backup Engine")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to source SQLite database (defaults to data/memory.db)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "backups",
        help="Directory to store backup files (defaults to backups/)",
    )
    args = parser.parse_args()

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_file = args.output_dir / f"memory_backup_{timestamp_str}.db"

    print("=" * 70)
    print("404 FOUNDERS — DATABASE BACKUP & INTEGRITY VERIFICATION")
    print("=" * 70)

    try:
        summary = perform_backup(args.source, dest_file)
        print("\nBackup Summary:")
        print(f"  Timestamp:   {summary['timestamp_utc']}")
        print(f"  Destination: {summary['destination']}")
        print(f"  Size:        {summary['size_bytes']} bytes")
        print("  Table Counts:")
        for tbl, cnt in summary["table_counts"].items():
            print(f"    - {tbl:<30}: {cnt}")
        print("=" * 70)
        print("✓ Database backup completed cleanly.")
        return 0
    except Exception as e:
        print(f"\n❌ Backup failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
