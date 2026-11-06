# 404 FOUNDERS — Data Governance & Security Policy

> **Document ID:** `DOC-DATA-002`  
> **Phase:** 04 — Custom BPE Tokenizer & Data Pipeline  
> **Target Audience:** Compliance Officers, Security Engineers, Data Curators  
> **Status:** Verified Implementation

---

## 1. Governance Principles

The 404 FOUNDERS foundation model adheres to strict sovereign data governance principles:

1. **No Automated Unauthorized Scraping:** No web scraping, automated spidering, or bulk data ingestion is conducted without documented authorization and legal rights.
2. **Deterministic Provenance:** Every training record traces directly to an identified origin, curator, ingest timestamp, and SHA-256 content hash.
3. **Zero Secrets in Training Data:** API keys, access tokens, private keys, passwords, and sensitive credentials are automatically intercepted and redacted.
4. **Zero Personally Identifiable Information (PII):** Social Security Numbers, credit cards, private IP addresses, and personal email addresses are filtered or anonymized prior to tokenization.

---

## 2. Sensitive Data & PII Detection Registry

The `DataGovernanceEngine` continuously scans all dataset streams against high-confidence regular expression signatures:

| Category | Signature Target | Redaction Replacement |
|---|---|---|
| **AWS Credentials** | AWS Access Key IDs (`AKIA[0-9A-Z]{16}`) | `[REDACTED_AWS_KEY]` |
| **GitHub Tokens** | Personal Access Tokens (`ghp_*`, `github_pat_*`) | `[REDACTED_GITHUB_TOKEN]` |
| **OpenAI / API Keys**| Secret API Keys (`sk-[a-zA-Z0-9]{20,}`) | `[REDACTED_OPENAI_KEY]` |
| **Cryptographic Keys** | PEM Private Keys (`-----BEGIN * PRIVATE KEY-----`) | `[REDACTED_PRIVATE_KEY]` |
| **Private Networks** | IPv4 RFC 1918 Private Addresses (`10.*`, `192.168.*`, `172.16-31.*`) | `[REDACTED_PRIVATE_IP]` |
| **Email Addresses** | RFC 5322 Email Addresses | `[REDACTED_EMAIL]` |
| **Government IDs** | US Social Security Numbers (`\d{3}-\d{2}-\d{4}`) | `[REDACTED_SSN]` |
| **Payment Cards** | Major Credit Card Numbers (16-digit formatted) | `[REDACTED_CREDIT_CARD]` |

### Redaction vs. Rejection Workflow
- **Redaction Mode (`redact_pii = True`):** Replaces detected secret signatures with canonical redaction markers while preserving surrounding contextual prose. The record is flagged with `metadata["pii_redacted"] = True`.
- **Audit / Strict Mode (`redact_pii = False`):** Completely discards any record containing sensitive findings, recording the rejection reason in audit logs.

---

## 3. Data Provenance Metadata Schema

Every record verified by the governance engine carries an immutable provenance dictionary in its metadata:

```json
{
  "provenance": {
    "source_uri": "https://approved-data-repo.internal/math/v1.jsonl",
    "license": "Apache-2.0",
    "license_approved": true,
    "license_status": "License 'Apache-2.0' is approved for commercial/research training",
    "curator": "404_Founders_Pipeline",
    "governance_verified_at": "2026-11-06T20:55:00+00:00"
  }
}
```

---

## 4. Workstation & Storage Security

1. **Restricted Dataset Directories:** Datasets reside strictly within `data/raw/` and `data/processed/`. Directory traversal outside project root is strictly prevented.
2. **Access Control:** All dataset generation scripts enforce standard Linux read/write permissions (`0640` for files, `0750` for directories).
3. **No Network Downloads During Ingestion:** Ingestion components process local verified files only; no outbound HTTP/HTTPS requests are initiated.
