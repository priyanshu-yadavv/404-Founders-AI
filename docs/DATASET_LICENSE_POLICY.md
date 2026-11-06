# 404 FOUNDERS — Dataset License & Copyright Policy

> **Document ID:** `DOC-DATA-003`  
> **Phase:** 04 — Custom BPE Tokenizer & Data Pipeline  
> **Target Audience:** Legal Counsel, Data Procurement, ML Research Leadership  
> **Status:** Verified Implementation

---

## 1. Foundation Model Licensing Mandate

To guarantee that the **404 FOUNDERS** foundation model and its associated derivative weights can be deployed across commercial, enterprise, sovereign, and research environments without legal encumbrance, all training datasets must satisfy strict licensing criteria prior to ingestion.

---

## 2. Approved License Whitelist

The following licenses are approved for inclusion in 404 FOUNDERS pretraining corpora:

| License | Description | Commercial Use Allowed | Derivative Weights Allowed |
|---|---|---|---|
| **Apache-2.0** | Permissive open-source license with explicit patent grant | **Yes** | **Yes** |
| **MIT** | Highly permissive standard open-source license | **Yes** | **Yes** |
| **BSD-2-Clause / BSD-3-Clause** | Permissive software license with attribution | **Yes** | **Yes** |
| **CC-BY-4.0** | Creative Commons Attribution license | **Yes** | **Yes** |
| **CC0-1.0** | Creative Commons Public Domain Dedication | **Yes** | **Yes** |
| **OpenData (ODbL / CDLA)** | Open Data Commons permissive license | **Yes** | **Yes** |
| **Public-Domain** | Dedicated public domain material | **Yes** | **Yes** |
| **Synthetic-Internal** | Model-generated or internally curated synthetic datasets | **Yes** | **Yes** |

---

## 3. Disapproved / Restrictive License Registry

The following license types are strictly prohibited in the pretraining pipeline:

| License | Category | Reason for Prohibition |
|---|---|---|
| **GPL-2.0 / GPL-3.0** | Strong Copyleft | Risk of viral copyleft claims over derivative neural weights. |
| **AGPL-3.0** | Network Copyleft | Viral copyleft triggering upon hosted cloud API execution. |
| **CC-BY-NC-4.0** | Non-Commercial | Restricts commercial enterprise deployment of trained models. |
| **CC-BY-ND-4.0** | No Derivatives | Explicitly prohibits creating derivative representations/models. |
| **All-Rights-Reserved** | Proprietary | Copyrighted data without explicit training grant. |
| **Proprietary-Unknown** | Unspecified | Unknown origin or terms of service prohibiting AI ingestion. |

---

## 4. Enforcement and Audit Procedure

1. **Automated License Inspection:** `DataGovernanceEngine.validate_license(license_name)` executes on every dataset candidate. If a license is not in `APPROVED_LICENSES`, ingestion halts immediately with a non-zero exit code.
2. **Provenance Record Keeping:** The dataset manifest records the exact license identifier alongside the cryptographic SHA-256 hash of every dataset file.
3. **Audit Trail:** In the event of licensing disputes, `DatasetManifest.verify(base_dir)` provides an immutable chain of custody establishing that only verified open-source and internal synthetic data was trained.
