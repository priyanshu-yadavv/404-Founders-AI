#!/usr/bin/env python3
"""
404 FOUNDERS — Dataset Inspection Script
Validates a dataset file, calculates descriptive statistics, and prints a governance audit.
"""

import argparse
import sys
from pathlib import Path

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training.datasets import (
    DataCleaner,
    DataGovernanceEngine,
    DatasetIngestor,
    DatasetStatistics,
    DataValidator,
    Deduplicator,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect, validate, and report metrics on a 404 FOUNDERS dataset file."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to dataset file (.jsonl, .csv, .txt).",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="general_text",
        help="Domain tag for plain text ingestion.",
    )
    parser.add_argument(
        "--license",
        type=str,
        default="Apache-2.0",
        help="Dataset license to validate against governance rules.",
    )

    args = parser.parse_args()
    path = Path(args.input)
    if not path.is_file():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("404 FOUNDERS — DATASET INSPECTION & GOVERNANCE REPORT")
    print("=" * 60)
    print(f"File: {path}")

    # 1. Validation
    validator = DataValidator()
    val_report = validator.validate_file(path)
    print("\n[1] File Validation:")
    print(f"  Valid: {val_report.is_valid}")
    print(f"  SHA-256 Checksum: {val_report.file_checksum}")
    print(f"  Total Lines/Records: {val_report.total_records}")
    print(f"  Valid Records: {val_report.valid_records}")
    print(f"  Invalid Records: {val_report.invalid_records}")
    if val_report.errors:
        print(f"  Errors encountered: {val_report.errors[:5]}")

    if not val_report.is_valid:
        print("\nDataset validation failed. Halting inspection.", file=sys.stderr)
        sys.exit(1)

    # 2. Ingestion & Governance
    records = []
    if path.suffix == ".jsonl":
        records = list(DatasetIngestor.ingest_jsonl(path, domain=args.domain))
    elif path.suffix == ".csv":
        records = list(DatasetIngestor.ingest_csv(path, domain=args.domain))
    else:
        records = [DatasetIngestor.ingest_plain_text(path, domain=args.domain)]

    # 3. Cleaning & Deduplication
    cleaner = DataCleaner()
    cleaned_records = []
    for r in records:
        c = cleaner.clean_record(r)
        if c is not None:
            cleaned_records.append(c)

    deduplicator = Deduplicator()
    unique_records = list(deduplicator.deduplicate(cleaned_records))

    print("\n[2] Cleaning & Deduplication:")
    print(f"  Raw Ingested: {len(records):,}")
    print(f"  Cleaned (Passed Quality): {len(cleaned_records):,}")
    print(f"  Exact Duplicates Removed: {deduplicator.exact_duplicates_count:,}")
    print(f"  Near Duplicates Removed: {deduplicator.near_duplicates_count:,}")
    print(f"  Final Unique Records: {len(unique_records):,}")

    # 4. Governance & PII Scan
    gov = DataGovernanceEngine()
    pii_count = 0
    for r in unique_records:
        ok, r, _ = gov.govern_record(r, source_uri=str(path), license_name=args.license)
        if r.metadata.get("pii_redacted"):
            pii_count += 1

    print("\n[3] Governance & Privacy:")
    print(f"  License: {args.license}")
    lic_ok, lic_msg = gov.validate_license(args.license)
    print(f"  License Status: {lic_msg}")
    print(f"  Records with PII detected/redacted: {pii_count:,}")

    # 5. Statistics
    stats = DatasetStatistics.compute(unique_records)
    print("\n[4] Summary Statistics:")
    print(DatasetStatistics.to_markdown_table(stats))


if __name__ == "__main__":
    main()
