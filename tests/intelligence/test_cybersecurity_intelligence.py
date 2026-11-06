"""
404 FOUNDERS — Cybersecurity Intelligence Engine Unit Tests
"""

import pytest
from personal_ai.cybersecurity.cyber_engine import CybersecurityIntelligenceEngine


@pytest.fixture
def engine() -> CybersecurityIntelligenceEngine:
    return CybersecurityIntelligenceEngine()


def test_offensive_intent_prohibited(engine: CybersecurityIntelligenceEngine) -> None:
    with pytest.raises(PermissionError, match="Security Policy Rejection"):
        engine.check_prohibited_intent("generate exploit payload for remote code execution")

    with pytest.raises(PermissionError, match="Security Policy Rejection"):
        engine.check_prohibited_intent("harvest credentials and tokens from victim server")


def test_shannon_entropy(engine: CybersecurityIntelligenceEngine) -> None:
    low_entropy = "AAAAAAAAAABBBBBBBBBB"
    high_entropy = "q8!v9#Lp@2$kZ^1&mC*5%xY(9)wQ"
    assert engine.calculate_shannon_entropy(low_entropy) < 2.0
    assert engine.calculate_shannon_entropy(high_entropy) > 4.0


def test_suspicious_script_analysis(engine: CybersecurityIntelligenceEngine) -> None:
    malicious_script = "import base64\nexec(base64.b64decode('aW1wb3J0IG9zOyBvcy5zeXN0ZW0oInJtIC1yZiAvIik='))\n"
    report = engine.analyze_suspicious_file("sample.py", malicious_script)
    assert report.threat_level == "HIGH"
    assert len(report.suspicious_patterns_found) > 0


def test_log_analysis(engine: CybersecurityIntelligenceEngine) -> None:
    sample_logs = [
        "192.168.1.100 - - [06/Nov/2026] \"GET /login?user=' OR 1=1 -- HTTP/1.1\" 200 450",
        "192.168.1.105 - - [06/Nov/2026] \"POST /auth/login HTTP/1.1\" 401 120 - Failed password for admin",
        "192.168.1.105 - - [06/Nov/2026] \"POST /auth/login HTTP/1.1\" 401 120 - Failed password for admin",
        "192.168.1.105 - - [06/Nov/2026] \"POST /auth/login HTTP/1.1\" 401 120 - Failed password for admin",
        "192.168.1.105 - - [06/Nov/2026] \"POST /auth/login HTTP/1.1\" 401 120 - Failed password for admin",
        "192.168.1.110 - - [06/Nov/2026] \"GET /static/../../etc/passwd HTTP/1.1\" 404 0",
    ]
    report = engine.analyze_logs(sample_logs)
    assert report.total_lines_analyzed == 6
    assert report.injection_indicators >= 1
    assert report.brute_force_indicators >= 4
    assert report.path_traversal_indicators >= 1
    assert report.overall_risk_level in ["MEDIUM", "HIGH"]


def test_cvss_31_calculation(engine: CybersecurityIntelligenceEngine) -> None:
    # Worst case network critical vulnerability
    crit_res = engine.calculate_cvss_v31(
        attack_vector="NETWORK",
        attack_complexity="LOW",
        privileges_required="NONE",
        user_interaction="NONE",
        scope="UNCHANGED",
        confidentiality="HIGH",
        integrity="HIGH",
        availability="HIGH",
    )
    assert crit_res.base_score >= 9.0
    assert crit_res.severity_rating == "CRITICAL"
    assert "CVSS:3.1" in crit_res.vector_string


def test_defensive_audit_workflow(engine: CybersecurityIntelligenceEngine) -> None:
    res = engine.audit(
        query="Audit web server logs for perimeter violations",
        logs=["GET /search?q=<script>alert(1)</script> HTTP/1.1 200"],
    )
    assert res.is_defensive_compliant is True
    assert len(res.threats_identified) > 0
    assert len(res.hardening_recommendations) >= 3
