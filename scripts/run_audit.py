#!/usr/bin/env python3
"""GitAgent (gitclaw) tool — runs the self-healing audit pipeline.

Reads a JSON payload on stdin, returns a JSON result on stdout. This is the
script gitclaw invokes when the agent calls the `run-audit` tool. See
`tools/run-audit.yaml`.

Two modes:
  - HTTP (default): POSTs to $GIT_SENSE_BACKEND_URL/api/agent/audit.
    Use this when the FastAPI server is already running (fast, shared cache).
  - Inline (GIT_SENSE_INLINE=1): imports the pipeline directly.
    Use this for fully standalone gitclaw runs without a server.

Input schema (stdin):
    {"repo_url": str, "branch": str, "file_path": str, "diff_content": str}

Output schema (stdout):
    PipelineResult as JSON.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import asdict

BACKEND = os.environ.get("GIT_SENSE_BACKEND_URL", "http://localhost:8000")


def _run_inline(payload: dict) -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "backend")))
    from agents import run_self_heal  # noqa: WPS433 (intentional lazy import)
    result = run_self_heal(**payload)
    return asdict(result)


def _run_http(payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BACKEND}/api/agent/audit",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        json.dump({"error": f"invalid JSON on stdin: {e}"}, sys.stdout)
        return 2

    try:
        if os.environ.get("GIT_SENSE_INLINE") == "1":
            result = _run_inline(payload)
        else:
            result = _run_http(payload)
    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        return 1

    json.dump(result, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
