"""Git-committed audit memory.

Every /api/agent/audit invocation appends a record to memory/audit_history.jsonl.
Subsequent runs read prior outcomes for the same file_path so the Auditor can
condition its review on history — e.g. raise scrutiny if a previous heal on
the same file failed.

Format: one JSON object per line:
    {"ts": "...", "file_path": "...", "outcome": "...",
     "summary": "...", "simulation_error": "..."|null,
     "finding_categories": ["security","drift",...]}

This is the load-bearing piece of "the agent IS the repo" — the audit log is
versioned with the codebase, so a fork of the agent inherits its scar tissue.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, "memory", "audit_history.jsonl")


def append_outcome(
    file_path: str,
    outcome: str,
    summary: str,
    findings: list[dict],
    simulation: dict,
) -> None:
    """Append one outcome record. Safe if the file doesn't exist yet."""
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_path": file_path,
        "outcome": outcome,
        "summary": (summary or "")[:240],
        "simulation_error": simulation.get("error") if isinstance(simulation, dict) else None,
        "finding_categories": sorted({
            str(f.get("category", "unknown")) for f in (findings or [])
        }),
    }
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def recall_history(file_path: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return up to `limit` most recent records for the given file_path.

    Tolerant of: missing file, partial/corrupt lines (skipped), and
    non-matching entries (filtered).
    """
    if not os.path.exists(HISTORY_PATH):
        return []
    matches: list[dict[str, Any]] = []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("file_path") == file_path:
                    matches.append(rec)
    except OSError:
        return []
    return matches[-limit:]


def format_history_for_prompt(history: list[dict]) -> str:
    """Render prior records as a compact context block for the Auditor."""
    if not history:
        return ""
    lines = ["Prior audits of this file (newest last):"]
    for h in history:
        cat = ", ".join(h.get("finding_categories", []) or ["—"])
        err = h.get("simulation_error")
        err_str = f" — sim error: {err[:80]}" if err else ""
        lines.append(f"  • {h.get('ts','?')}  outcome={h.get('outcome','?')}  categories=[{cat}]{err_str}")
    return "\n".join(lines)
