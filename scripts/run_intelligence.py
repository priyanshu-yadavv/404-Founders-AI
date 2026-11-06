#!/usr/bin/env python3
"""
404 FOUNDERS — Developer Intelligence CLI Utility
Interactive and automated command-line driver for the 12 specialized intelligence engines
and the Central Intelligence Router.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.intelligence.central_router import CentralIntelligenceRouter


def print_banner() -> None:
    print("=" * 72)
    print("  404 FOUNDERS — Phase 07 Modular Intelligence System")
    print("  Tagline: Intelligence Without Boundaries.")
    print("=" * 72)


def list_modules(router: CentralIntelligenceRouter) -> None:
    print("\n[ACTIVE INTELLIGENCE ENGINES — 12 MODULES]")
    for idx, (name, engine) in enumerate(router.engines.items(), start=1):
        doc = (engine.__doc__ or "").strip().split("\n")[0]
        print(f"  {idx:2d}. {name:<20} | {doc}")
    print("\nCentral Coordinator: CentralIntelligenceRouter (hybrid rule & neural dynamic gating)")
    print("Security Policy: Defensive only; sandbox execution barrier; zero pretrained weights.\n")


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="404 FOUNDERS Modular Intelligence CLI Driver")
    parser.add_argument("--query", "-q", type=str, help="Natural language query to route dynamically")
    parser.add_argument("--engine", "-e", type=str, choices=[
        "logical", "mathematical", "scientific", "coding", "cybersecurity",
        "critical_thinking", "creative", "research", "planning", "self_evaluation",
        "language", "knowledge"
    ], help="Target specific intelligence engine directly")
    parser.add_argument("--code", type=str, help="Code snippet for coding intelligence analysis")
    parser.add_argument("--expression", type=str, help="Math expression to compute")
    parser.add_argument("--objective", type=str, help="Goal or objective for the planning engine")
    parser.add_argument("--logs", nargs="+", help="Log lines for cybersecurity inspection")
    parser.add_argument("--list-modules", action="store_true", help="List all 12 modules and responsibilities")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")

    args = parser.parse_args()

    router = CentralIntelligenceRouter()

    if args.list_modules or len(sys.argv) == 1:
        print_banner()
        list_modules(router)
        if len(sys.argv) == 1:
            print("Use --help to view interactive query flags.")
        return

    # Direct or routed query handling
    query_text = args.query or args.expression or args.code or args.objective or (args.logs[0] if args.logs else "")
    if not query_text:
        print("Error: Provide --query, --code, --expression, --objective, or --logs.", file=sys.stderr)
        sys.exit(1)

    hints: Dict[str, Any] = {}
    if args.engine:
        hints["force_engine"] = args.engine
    if args.code:
        hints["code"] = args.code
    if args.expression:
        hints["expression"] = args.expression
    if args.logs:
        hints["logs"] = args.logs

    res = router.dispatch(query=query_text, context_hints=hints)

    if args.json:
        out_dict = {
            "query": res.query,
            "primary_engine": res.dispatch_plan.primary_engine,
            "secondary_engines": res.dispatch_plan.secondary_engines,
            "intent_confidence": res.dispatch_plan.intent_confidence,
            "combined_summary": res.combined_summary,
            "conflicts": res.conflicts_detected,
            "outputs": {k: str(v.data) for k, v in res.engine_outputs.items()},
        }
        print(json.dumps(out_dict, indent=2))
    else:
        print_banner()
        print(f"\n[QUERY]: {res.query}")
        print(f"[DISPATCH]: Primary -> {res.dispatch_plan.primary_engine.upper()} (Confidence: {res.dispatch_plan.intent_confidence*100:.1f}%)")
        if res.dispatch_plan.secondary_engines:
            print(f"[SECONDARY]: {', '.join(s.upper() for s in res.dispatch_plan.secondary_engines)}")
        print(f"\n[SUMMARY]:\n{res.combined_summary}")
        if res.conflicts_detected:
            print(f"\n[CONFLICTS DETECTED]:")
            for c in res.conflicts_detected:
                print(f"  ⚠️  {c}")
        print("\n" + "=" * 72)


if __name__ == "__main__":
    run_cli()
