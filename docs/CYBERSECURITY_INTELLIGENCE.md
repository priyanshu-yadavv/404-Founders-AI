# 404 FOUNDERS — Cybersecurity Intelligence Engine Specification

**Tagline:** Intelligence Without Boundaries.  
**Module:** `personal_ai.cybersecurity.cyber_engine` (`CybersecurityIntelligenceEngine`)  
**Phase:** Phase 07 — Intelligence Modules  
**Status:** Implemented & Verified  

---

## 1. Architectural Scope & Objectives

The Cybersecurity Intelligence Engine provides defensive security operations, server and system log triage, suspicious artifact inspection, CVSS 3.1 base score computation, and structured hardening recommendations.

### Defensive Compliance Policy
The engine operates strictly under an authorized defensive mandate:
- **Zero Offensive Exploitation:** Automated exploit generation, weaponized payload delivery, reverse shells, and persistence scripts are blocked with immediate policy rejection (`PermissionError`).
- **Zero Credential Harvesting:** Requests to harvest passwords, private keys, or session tokens are rejected.
- **Untrusted Input Invariant:** All uploaded files, scripts, and logs are treated as untrusted and isolated.

---

## 2. Core Capabilities

### 2.1 Suspicious File & Artifact Analysis
- **Shannon Entropy Calculation:** Measures bit distribution entropy:
  $$H(X) = -\sum_{i=1}^n P(x_i) \log_2 P(x_i)$$
  Values exceeding $6.8$ indicate encrypted, packed, or heavily obfuscated payloads.
- **Malicious Invocation Scanning:** Detects obfuscated `eval(base64)`, `/bin/sh -i` shells, `powershell -enc`, and netcat reverse shells.

### 2.2 Defensive Log Triage
Scans web server and system access logs for attack indicators:
- **SQL Injection:** Detects `OR 1=1`, `UNION SELECT`, and hex encodings.
- **Cross-Site Scripting (XSS):** Identifies `<script>`, `javascript:`, and onerror handlers.
- **Path Traversal:** Identifies `../`, `..\\`, and URL-encoded `%2e%2e%2f`.
- **Brute-Force Attacks:** Aggregates repeated failed authentication attempts.
- **Automated Scanners:** Flags user agents from vulnerability scanners (Nikto, SQLMap, Gobuster).

### 2.3 CVSS 3.1 Base Score Calculator
Computes exact Common Vulnerability Scoring System (CVSS v3.1) metrics according to the FIRST specification:
- Exploitability Sub-Score from Attack Vector (AV), Attack Complexity (AC), Privileges Required (PR), and User Interaction (UI).
- Impact Sub-Score (ISS) from Confidentiality (C), Integrity (I), and Availability (A).
- Scope change handling ($S:U$ vs $S:C$).
- Formats standard vector string: `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`.

---

## 3. Data Contracts & Schema

```python
@dataclass
class ThreatClassification:
    category: str
    severity: str
    matched_pattern: str
    description: str
    remediation_advice: str

@dataclass
class CVSSScoreResult:
    base_score: float
    severity_rating: str
    vector_string: str
    metrics: Dict[str, str]

@dataclass
class SecurityAuditResult:
    target_type: str
    threats_identified: List[ThreatClassification]
    cvss_score: Optional[CVSSScoreResult]
    file_report: Optional[SuspiciousFileReport]
    log_report: Optional[LogAnalysisReport]
    hardening_recommendations: List[str]
    is_defensive_compliant: bool
    notice: str
```
