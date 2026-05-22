#!/usr/bin/env python3
"""GitAgent tool — Architect-only heal step. Reads JSON on stdin, returns JSON on stdout."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        json.dump({"error": f"invalid JSON on stdin: {e}"}, sys.stdout)
        return 2

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, os.path.abspath(os.path.join(here, "..", "backend")))
    from agents import AgentEvent, architect, simulate  # noqa: WPS433

    events: list[AgentEvent] = []
    healed = architect(
        payload["file_path"],
        payload["diff_content"],
        payload["findings"],
        events,
    )
    sim = simulate(payload["file_path"], healed, events)
    json.dump(
        {
            "healed_content": healed if sim["passed"] else None,
            "simulation": sim,
            "transcript": [asdict(e) for e in events],
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
