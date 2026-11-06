#!/usr/bin/env python3
"""
404 FOUNDERS — Local Backend Server Runner
Launches the FastAPI ASGI application with Uvicorn on localhost.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch 404 FOUNDERS FastAPI backend server."
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind interface (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code change",
    )
    args = parser.parse_args()

    print("=" * 65)
    print(" 404 FOUNDERS — Localhost API Server Launch")
    print("=" * 65)
    print(f"  Backend URL     : http://{args.host}:{args.port}")
    print(f"  Health Check    : http://{args.host}:{args.port}/health")
    print(f"  API Docs (OAS)  : http://{args.host}:{args.port}/docs")
    print(f"  OpenAPI Schema  : http://{args.host}:{args.port}/openapi.json")
    print(f"  Allowed Origins : http://localhost:5173, http://127.0.0.1:5173")
    print("=" * 65)

    try:
        import uvicorn
        uvicorn.run("api.rest.app:app", host=args.host, port=args.port, reload=args.reload)
        return 0
    except KeyboardInterrupt:
        print("\n[INFO] Backend server stopped by user.")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to start backend server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
