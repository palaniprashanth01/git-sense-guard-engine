"""Runtime loader for the git-native agent definition.

Reads SOUL.md, RULES.md, DUTIES.md, and agent.yaml from the repo root and
exposes role-specific system prompts. The conflict matrix from DUTIES.md
is enforced programmatically so the Auditor cannot patch its own findings.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name: str) -> str:
    with open(os.path.join(ROOT, name), "r", encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=1)
def load_soul() -> str:
    return _read("SOUL.md")


@lru_cache(maxsize=1)
def load_rules() -> str:
    return _read("RULES.md")


@lru_cache(maxsize=1)
def load_duties() -> str:
    return _read("DUTIES.md")


@lru_cache(maxsize=1)
def conflict_matrix() -> dict[str, set[str]]:
    """Parse the conflict matrix block from DUTIES.md.

    Lines of the form `- [Auditor, Architect]` declare that the first role
    cannot act on output produced by the second.
    """
    text = load_duties()
    matrix: dict[str, set[str]] = {}
    for line in text.splitlines():
        m = re.match(r"\s*-\s*\[(.+?)\]", line)
        if not m:
            continue
        parts = [p.strip() for p in m.group(1).split(",")]
        if len(parts) == 2:
            matrix.setdefault(parts[0], set()).add(parts[1])
    return matrix


def assert_role_allowed(role: str, action: str, target_role: str | None = None) -> None:
    """Block role/action combinations forbidden by the conflict matrix.

    Currently enforces: Auditor cannot perform `patch` actions (only
    Architect can produce patches).
    """
    if role == "Auditor" and action == "patch":
        raise PermissionError(
            "Conflict matrix violation: Auditor is not authorized to patch findings. "
            "Hand off to Architect."
        )
    if target_role and target_role in conflict_matrix().get(role, set()) and action == "patch":
        raise PermissionError(
            f"Conflict matrix violation: {role} cannot patch outputs from {target_role}."
        )


def build_system_prompt(role: str, extra: Iterable[str] | None = None) -> str:
    """Compose a role-scoped system prompt from the on-disk agent definition.

    Structural Markdown / XML tags are used per RULES.md §2.
    """
    sections = [
        "<agent_soul>", load_soul().strip(), "</agent_soul>",
        "<architectural_rules>", load_rules().strip(), "</architectural_rules>",
        "<compliance>", load_duties().strip(), "</compliance>",
        f"<active_role>{role}</active_role>",
    ]
    if extra:
        sections.extend(extra)
    return "\n".join(sections)
