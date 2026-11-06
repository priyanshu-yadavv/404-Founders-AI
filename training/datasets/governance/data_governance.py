"""
404 FOUNDERS — Data Governance & Security
Enforces dataset provenance tracking, licensing compliance, consent verification,
and PII/secret detection and redaction.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from training.datasets.ingestion.dataset_ingestor import DataRecord


# Approved and Restrictive License Registries
APPROVED_LICENSES: Set[str] = {
    "Apache-2.0",
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC-BY-4.0",
    "CC0-1.0",
    "OpenData",
    "Synthetic-Internal",
    "Public-Domain",
}

RESTRICTIVE_LICENSES: Set[str] = {
    "GPL-3.0",
    "AGPL-3.0",
    "CC-BY-NC-4.0",
    "CC-BY-ND-4.0",
    "All-Rights-Reserved",
    "Proprietary-Unknown",
}


@dataclass
class PIIDetectionResult:
    """Findings from scanning a text for sensitive data or credentials."""

    has_pii: bool
    findings_count: int
    pii_types: List[str] = field(default_factory=list)
    redacted_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataGovernanceEngine:
    """Governance and compliance engine managing dataset security and provenance."""

    # Pre-compiled regex patterns for sensitive credentials and PII
    PATTERNS = {
        "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "github_token": re.compile(r"\b(?:ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"),
        "openai_key": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
        "private_ip": re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3})\b"
        ),
    }

    def __init__(
        self,
        approved_licenses: Optional[Set[str]] = None,
        redact_pii: bool = True,
    ) -> None:
        self.approved_licenses = approved_licenses or APPROVED_LICENSES
        self.redact_pii = redact_pii

    def validate_license(self, license_name: str) -> Tuple[bool, str]:
        """Check whether a dataset license is approved for foundation model training."""
        if not license_name:
            return False, "Missing license specification"
        if license_name in self.approved_licenses:
            return True, f"License '{license_name}' is approved for commercial/research training"
        if license_name in RESTRICTIVE_LICENSES:
            return False, f"License '{license_name}' is restrictive (copyleft or non-commercial)"
        return False, f"License '{license_name}' is not in the approved license registry"

    def scan_and_redact_pii(self, text: str) -> PIIDetectionResult:
        """Scan text for PII and secrets, optionally applying redaction."""
        if not text:
            return PIIDetectionResult(has_pii=False, findings_count=0)

        found_types: List[str] = []
        total_findings = 0
        working_text = text

        for pii_type, pattern in self.PATTERNS.items():
            matches = list(pattern.finditer(working_text))
            if matches:
                found_types.append(pii_type)
                total_findings += len(matches)
                if self.redact_pii:
                    working_text = pattern.sub(f"[REDACTED_{pii_type.upper()}]", working_text)

        return PIIDetectionResult(
            has_pii=total_findings > 0,
            findings_count=total_findings,
            pii_types=found_types,
            redacted_text=working_text if self.redact_pii else None,
        )

    def attach_provenance(
        self,
        record: DataRecord,
        source_uri: str,
        license_name: str,
        curator: str = "404_Founders_Pipeline",
    ) -> DataRecord:
        """Attach verified provenance metadata to a record."""
        is_lic_valid, lic_msg = self.validate_license(license_name)

        record.metadata["provenance"] = {
            "source_uri": source_uri,
            "license": license_name,
            "license_approved": is_lic_valid,
            "license_status": lic_msg,
            "curator": curator,
            "governance_verified_at": datetime.now(timezone.utc).isoformat(),
        }
        return record

    def govern_record(
        self,
        record: DataRecord,
        source_uri: str,
        license_name: str,
    ) -> Tuple[bool, DataRecord, str]:
        """Apply complete governance checks: license, PII scanning/redaction, and provenance.

        Returns:
            Tuple of (passes_governance: bool, updated_record: DataRecord, status_message: str).
        """
        is_lic_valid, lic_msg = self.validate_license(license_name)
        if not is_lic_valid:
            return False, record, f"Rejected by governance: {lic_msg}"

        pii_res = self.scan_and_redact_pii(record.content)
        if pii_res.has_pii:
            if self.redact_pii and pii_res.redacted_text is not None:
                record.content = pii_res.redacted_text
                record.metadata["pii_redacted"] = True
                record.metadata["pii_types_detected"] = pii_res.pii_types
            else:
                return False, record, f"Rejected: Contains unredacted PII/secrets: {pii_res.pii_types}"

        self.attach_provenance(record, source_uri=source_uri, license_name=license_name)
        return True, record, "Governance verified"
