"""
404 FOUNDERS — Cybersecurity Intelligence Engine
Provides defensive cybersecurity inspection, suspicious artifact scanning, log pattern analysis,
network event triage, CVSS 3.1 risk scoring, and defensive hardening recommendations.
Strictly prohibits exploit generation, credential harvesting, persistence, and destructive actions.
"""

from dataclasses import dataclass, field
import math
import re
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ThreatClassification:
    """Categorization of a detected security indicator."""
    category: str  # "INJECTION", "AUTHENTICATION", "RECONNAISSANCE", "MALWARE_ARTIFACT", "ANOMALY"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"
    matched_pattern: str
    description: str
    remediation_advice: str


@dataclass
class CVSSScoreResult:
    """Calculated CVSS 3.1 Base Score and severity rating."""
    base_score: float
    severity_rating: str  # "NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    vector_string: str
    metrics: Dict[str, str]


@dataclass
class SuspiciousFileReport:
    """Analysis of suspicious file content or scripts."""
    filename: str
    entropy: float
    high_entropy_detected: bool
    suspicious_patterns_found: List[str]
    threat_level: str
    defensive_recommendation: str


@dataclass
class LogAnalysisReport:
    """Summary of analyzed defensive system or web server logs."""
    total_lines_analyzed: int
    detected_threats: List[ThreatClassification]
    brute_force_indicators: int
    injection_indicators: int
    path_traversal_indicators: int
    overall_risk_level: str


@dataclass
class SecurityAuditResult:
    """Complete defensive cybersecurity audit report."""
    target_type: str  # "LOGS", "FILE", "NETWORK_EVENT", "VULNERABILITY"
    threats_identified: List[ThreatClassification]
    cvss_score: Optional[CVSSScoreResult]
    file_report: Optional[SuspiciousFileReport]
    log_report: Optional[LogAnalysisReport]
    hardening_recommendations: List[str]
    is_defensive_compliant: bool = True
    notice: str = (
        "DEFENSIVE POLICY NOTICE: 404 FOUNDERS operates strictly for authorized defensive security, "
        "incident response, and vulnerability triage. Automated exploit generation, payload delivery, "
        "and unauthorized testing are rejected."
    )


class CybersecurityIntelligenceEngine:
    """
    Defensive cybersecurity intelligence engine.
    Scans logs, inspects script artifacts, evaluates network anomalies,
    computes CVSS metrics, and produces mitigation guidelines.
    """

    PROHIBITED_INTENTS = [
        r"\bgenerate\s+(exploit|payload|malware|ransomware|keylogger|backdoor)\b",
        r"\bharvest\s+(credentials|passwords|tokens)\b",
        r"\bcreate\s+reverse\s+shell\b",
        r"\bbypass\s+firewall\s+stealth\b",
    ]

    LOG_THREAT_PATTERNS = [
        (re.compile(r"('|\%27)\s*or\s*('|\%27)?\d+=\d+", re.IGNORECASE), "INJECTION", "CRITICAL", "SQL Injection pattern detected (OR 1=1)"),
        (re.compile(r"(<script|javascript:|onerror=)", re.IGNORECASE), "INJECTION", "HIGH", "Cross-Site Scripting (XSS) payload marker detected"),
        (re.compile(r"(\.\./|\.\.\\|\%2e\%2e\%2f)", re.IGNORECASE), "RECONNAISSANCE", "HIGH", "Directory traversal attempt (../) detected"),
        (re.compile(r"(failed\s+password|authentication\s+failure|invalid\s+user)", re.IGNORECASE), "AUTHENTICATION", "MEDIUM", "Failed authentication attempt logged"),
        (re.compile(r"(union\s+select|select\s+@@version)", re.IGNORECASE), "INJECTION", "CRITICAL", "SQL Union/Enumeration injection pattern detected"),
        (re.compile(r"(nmap|sqlmap|nikto|dirbuster|gobuster)", re.IGNORECASE), "RECONNAISSANCE", "MEDIUM", "Automated vulnerability scanner user-agent or artifact"),
    ]

    SUSPICIOUS_SCRIPT_PATTERNS = [
        re.compile(r"eval\s*\(\s*base64_decode", re.IGNORECASE),
        re.compile(r"exec\s*\(\s*base64\.b64decode", re.IGNORECASE),
        re.compile(r"/bin/(ba)?sh\s+-i", re.IGNORECASE),
        re.compile(r"nc\s+-[e|c]\s+/bin", re.IGNORECASE),
        re.compile(r"powershell\s+-(nop|enc|encodedcommand)", re.IGNORECASE),
    ]

    def check_prohibited_intent(self, query: str) -> None:
        """Enforce strict defensive boundaries; raise PermissionError on unauthorized offensive intents."""
        lower_q = query.lower()
        for pat in self.PROHIBITED_INTENTS:
            if re.search(pat, lower_q):
                raise PermissionError(
                    "Security Policy Rejection: 404 FOUNDERS operates exclusively for defensive analysis. "
                    "Requests for weaponized exploit generation or credential harvesting are strictly prohibited."
                )

    def calculate_shannon_entropy(self, data: str) -> float:
        """Calculate Shannon entropy to identify obfuscated or packed binary content."""
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        char_counts: Dict[str, int] = {}
        for c in data:
            char_counts[c] = char_counts.get(c, 0) + 1
        for count in char_counts.values():
            p_x = count / length
            entropy -= p_x * math.log2(p_x)
        return round(entropy, 3)

    def analyze_suspicious_file(self, filename: str, content: str) -> SuspiciousFileReport:
        """Analyze suspicious file contents for high entropy and dangerous signatures."""
        entropy = self.calculate_shannon_entropy(content)
        high_entropy = entropy > 6.8  # Typically indicates encryption, packed code, or heavy obfuscation

        matched: List[str] = []
        for pat in self.SUSPICIOUS_SCRIPT_PATTERNS:
            if pat.search(content):
                matched.append(pat.pattern)

        if matched or (high_entropy and len(content) > 500):
            threat_level = "HIGH" if matched else "MEDIUM"
            recommendation = "Isolate artifact in offline sandbox; inspect decoded payloads; restrict process execution privileges."
        else:
            threat_level = "LOW"
            recommendation = "No known malicious invocation patterns identified in sample."

        return SuspiciousFileReport(
            filename=filename,
            entropy=entropy,
            high_entropy_detected=high_entropy,
            suspicious_patterns_found=matched,
            threat_level=threat_level,
            defensive_recommendation=recommendation,
        )

    def analyze_logs(self, log_lines: List[str]) -> LogAnalysisReport:
        """Inspect server and system logs to identify attack patterns and brute force activity."""
        threats: List[ThreatClassification] = []
        brute_force_count = 0
        injection_count = 0
        traversal_count = 0

        for line in log_lines:
            for pattern, cat, sev, desc in self.LOG_THREAT_PATTERNS:
                if pattern.search(line):
                    threats.append(ThreatClassification(
                        category=cat,
                        severity=sev,
                        matched_pattern=pattern.pattern,
                        description=desc,
                        remediation_advice="Review origin IP, update WAF rules, and inspect affected endpoint.",
                    ))
                    if cat == "AUTHENTICATION":
                        brute_force_count += 1
                    elif cat == "INJECTION":
                        injection_count += 1
                    elif cat == "RECONNAISSANCE":
                        traversal_count += 1

        overall_risk = "LOW"
        if injection_count > 0 or brute_force_count > 10:
            overall_risk = "HIGH"
        elif brute_force_count > 3 or traversal_count > 2:
            overall_risk = "MEDIUM"

        return LogAnalysisReport(
            total_lines_analyzed=len(log_lines),
            detected_threats=threats,
            brute_force_indicators=brute_force_count,
            injection_indicators=injection_count,
            path_traversal_indicators=traversal_count,
            overall_risk_level=overall_risk,
        )

    def calculate_cvss_v31(
        self,
        attack_vector: str = "NETWORK",         # NETWORK (0.85), ADJACENT (0.62), LOCAL (0.55), PHYSICAL (0.2)
        attack_complexity: str = "LOW",          # LOW (0.77), HIGH (0.44)
        privileges_required: str = "NONE",       # NONE (0.85), LOW (0.62), HIGH (0.27) (unchanged scope)
        user_interaction: str = "NONE",          # NONE (0.85), REQUIRED (0.62)
        scope: str = "UNCHANGED",                # UNCHANGED, CHANGED
        confidentiality: str = "HIGH",           # NONE (0.0), LOW (0.22), HIGH (0.56)
        integrity: str = "HIGH",                 # NONE (0.0), LOW (0.22), HIGH (0.56)
        availability: str = "HIGH",              # NONE (0.0), LOW (0.22), HIGH (0.56)
    ) -> CVSSScoreResult:
        """Compute CVSS 3.1 Base Score deterministically per FIRST specification."""
        av_map = {"NETWORK": 0.85, "ADJACENT": 0.62, "LOCAL": 0.55, "PHYSICAL": 0.20}
        ac_map = {"LOW": 0.77, "HIGH": 0.44}
        pr_map_unchanged = {"NONE": 0.85, "LOW": 0.62, "HIGH": 0.27}
        pr_map_changed = {"NONE": 0.85, "LOW": 0.68, "HIGH": 0.50}
        ui_map = {"NONE": 0.85, "REQUIRED": 0.62}
        cia_map = {"NONE": 0.0, "LOW": 0.22, "HIGH": 0.56}

        av = av_map.get(attack_vector.upper(), 0.85)
        ac = ac_map.get(attack_complexity.upper(), 0.77)
        is_changed = scope.upper() == "CHANGED"
        pr = (pr_map_changed if is_changed else pr_map_unchanged).get(privileges_required.upper(), 0.85)
        ui = ui_map.get(user_interaction.upper(), 0.85)

        c = cia_map.get(confidentiality.upper(), 0.56)
        i = cia_map.get(integrity.upper(), 0.56)
        a = cia_map.get(availability.upper(), 0.56)

        # Impact Sub Score
        iss = 1.0 - ((1.0 - c) * (1.0 - i) * (1.0 - a))
        if is_changed:
            impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02)**15)
        else:
            impact = 6.42 * iss

        # Exploitability Sub Score
        exploitability = 8.22 * av * ac * pr * ui

        if impact <= 0:
            base_score = 0.0
        else:
            if not is_changed:
                base_score = min(10.0, math.ceil((min(impact + exploitability, 10.0)) * 10) / 10.0)
            else:
                base_score = min(10.0, math.ceil((min(1.08 * (impact + exploitability), 10.0)) * 10) / 10.0)

        # Severity rating
        if base_score == 0.0:
            rating = "NONE"
        elif base_score < 4.0:
            rating = "LOW"
        elif base_score < 7.0:
            rating = "MEDIUM"
        elif base_score < 9.0:
            rating = "HIGH"
        else:
            rating = "CRITICAL"

        vector_str = (
            f"CVSS:3.1/AV:{attack_vector[0]}/AC:{attack_complexity[0]}/PR:{privileges_required[0]}/"
            f"UI:{user_interaction[0]}/S:{'C' if is_changed else 'U'}/C:{confidentiality[0]}/I:{integrity[0]}/A:{availability[0]}"
        )

        metrics = {
            "Attack Vector": attack_vector,
            "Attack Complexity": attack_complexity,
            "Privileges Required": privileges_required,
            "User Interaction": user_interaction,
            "Scope": scope,
            "Confidentiality": confidentiality,
            "Integrity": integrity,
            "Availability": availability,
        }

        return CVSSScoreResult(
            base_score=base_score,
            severity_rating=rating,
            vector_string=vector_str,
            metrics=metrics,
        )

    def audit(
        self,
        query: str,
        logs: Optional[List[str]] = None,
        file_sample: Optional[Tuple[str, str]] = None,
    ) -> SecurityAuditResult:
        """Run defensive security audit over query, logs, or file sample."""
        self.check_prohibited_intent(query)

        file_report: Optional[SuspiciousFileReport] = None
        log_report: Optional[LogAnalysisReport] = None
        threats: List[ThreatClassification] = []
        recommendations: List[str] = [
            "Apply principle of least privilege to running processes and database connections.",
            "Enforce strict input validation and parameterized queries to mitigate injection risks.",
            "Ensure regular security patch management across OS and dependencies.",
        ]

        if file_sample:
            fname, fcontent = file_sample
            file_report = self.analyze_suspicious_file(fname, fcontent)
            recommendations.append(file_report.defensive_recommendation)

        if logs:
            log_report = self.analyze_logs(logs)
            threats.extend(log_report.detected_threats)
            if log_report.brute_force_indicators > 0:
                recommendations.append("Implement account lockout policies and rate limiting on authentication routes.")
            if log_report.injection_indicators > 0:
                recommendations.append("Audit all SQL queries for parameterized binding and enable Web Application Firewall.")

        target = "LOGS" if logs else ("FILE" if file_sample else "GENERAL_SECURITY")

        return SecurityAuditResult(
            target_type=target,
            threats_identified=threats,
            cvss_score=None,
            file_report=file_report,
            log_report=log_report,
            hardening_recommendations=recommendations,
            is_defensive_compliant=True,
        )
