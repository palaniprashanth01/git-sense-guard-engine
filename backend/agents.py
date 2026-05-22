"""Multi-agent self-healing pipeline.

Pipeline:  Auditor  →  (gate on findings)  →  Architect  →  Simulator

Each agent is an isolated LLM call with a role-scoped system prompt built
from SOUL.md / RULES.md / DUTIES.md by `agent_runtime.build_system_prompt`.
The Auditor / Architect separation is enforced by `assert_role_allowed`,
which reads the conflict matrix declared in DUTIES.md.

The Simulator does NOT call an LLM. It runs deterministic structural
validation (Python AST, JSON/YAML parse, brace balance, secret scan) so
"self-healed" patches cannot ship if they are structurally broken or
re-introduce a secret.
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from agent_runtime import assert_role_allowed, build_system_prompt
from analysis import get_current_api_key, rotate_api_key

CRITICAL_SEVERITIES = {"high", "critical"}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


@dataclass
class AgentEvent:
    role: str
    level: str  # info | warn | error | success
    message: str
    ts: float = field(default_factory=time.time)


@dataclass
class PipelineResult:
    outcome: str  # "Clean" | "Self-Healed" | "Heal-Failed"
    audit_summary: str
    findings: list[dict]
    healed_content: str | None
    simulation: dict
    transcript: list[dict]


def _llm() -> ChatGroq:
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0.1,
        api_key=get_current_api_key(),
    )


def _invoke(role: str, user_prompt: str, retries: int = 2) -> str:
    system = build_system_prompt(role)
    template = ChatPromptTemplate.from_messages(
        [("system", system), ("user", "{q}")]
    )
    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            chain = template | _llm() | StrOutputParser()
            return chain.invoke({"q": user_prompt})
        except Exception as e:  # rate limits, auth, transient
            last_err = e
            rotate_api_key()
    raise last_err if last_err else RuntimeError("LLM invocation failed")


def _extract_json(text: str) -> Any:
    """Best-effort JSON extraction. Returns None if nothing parseable."""
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    m = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z0-9_+\-]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text


def auditor(file_path: str, diff_content: str, events: list[AgentEvent]) -> tuple[str, list[dict]]:
    events.append(AgentEvent("Auditor", "info", f"Scanning proposed patch for {file_path}"))
    q = f"""You are reviewing a proposed change for compliance and safety.

<target_file>{file_path}</target_file>
<proposed_patch>
{diff_content}
</proposed_patch>

Identify: hardcoded secrets, injection vectors (SQL/XSS/command), semantic prompt
drift (instructions leaking into context, role confusion), regressions vs. the
file's purpose, and any RULES.md violations.

Respond with ONLY this JSON (no prose, no fences):
{{
  "summary": "<one paragraph>",
  "findings": [
    {{"severity": "low|medium|high|critical",
      "category": "<security|drift|regression|style>",
      "evidence": "<short code excerpt>",
      "rationale": "<why this is a problem>"}}
  ]
}}
"""
    raw = _invoke("Auditor", q)
    parsed = _extract_json(raw) or {"summary": raw[:400], "findings": []}
    findings = parsed.get("findings", []) or []
    summary = parsed.get("summary", "")
    crit = [f for f in findings if str(f.get("severity", "")).lower() in CRITICAL_SEVERITIES]
    if crit:
        events.append(AgentEvent("Auditor", "warn", f"{len(crit)} high/critical findings — heal required"))
    else:
        events.append(AgentEvent("Auditor", "success", "Baseline clean — no critical findings"))
    return summary, findings


def architect(
    file_path: str,
    diff_content: str,
    findings: list[dict],
    events: list[AgentEvent],
) -> str:
    # Enforce conflict matrix: Auditor cannot reach this function.
    assert_role_allowed("Architect", "patch", target_role="Auditor")
    events.append(AgentEvent("Architect", "info", "Engineering healed patch"))
    q = f"""You are the Architect. Produce the corrected, final content of the file
after applying the proposed change AND remediating every finding below.

<target_file>{file_path}</target_file>
<proposed_patch>
{diff_content}
</proposed_patch>
<auditor_findings>
{json.dumps(findings, indent=2)}
</auditor_findings>

Constraints (RULES.md):
- Never include hardcoded secrets / API keys / private keys.
- Preserve the original intent of the patch.
- Output ONLY the final file content. No prose. No markdown fences.
"""
    raw = _invoke("Architect", q)
    healed = _strip_fences(raw)
    events.append(AgentEvent("Architect", "success", f"Generated {len(healed)} chars of healed content"))
    return healed


def _check_secrets(content: str) -> str | None:
    for pat in SECRET_PATTERNS:
        if pat.search(content):
            return f"Leaked secret matching pattern {pat.pattern!r}"
    return None


def simulate(file_path: str, content: str, events: list[AgentEvent]) -> dict:
    events.append(AgentEvent("Simulator", "info", f"Structural simulation of {file_path}"))
    ext = os.path.splitext(file_path)[1].lower()
    result: dict = {"ext": ext, "passed": False, "checks": []}
    try:
        if ext == ".py":
            ast.parse(content)
            result["checks"].append("python-ast: ok")
        elif ext == ".json":
            json.loads(content)
            result["checks"].append("json-parse: ok")
        elif ext in (".yaml", ".yml"):
            try:
                import yaml  # type: ignore
                yaml.safe_load(content)
                result["checks"].append("yaml-parse: ok")
            except ImportError:
                result["checks"].append("yaml-parse: skipped (pyyaml not installed)")
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            if content.count("{") != content.count("}"):
                raise ValueError("Unbalanced braces")
            if content.count("(") != content.count(")"):
                raise ValueError("Unbalanced parentheses")
            result["checks"].append("brace-balance: ok")
        else:
            if not content.strip():
                raise ValueError("Empty content")
            result["checks"].append("non-empty: ok")

        leaked = _check_secrets(content)
        if leaked:
            raise ValueError(leaked)
        result["checks"].append("secret-scan: ok")
        result["passed"] = True
        events.append(AgentEvent("Simulator", "success", "All structural checks passed"))
    except Exception as e:
        result["error"] = str(e)
        events.append(AgentEvent("Simulator", "error", f"Simulation failed: {e}"))
    return result


def run_self_heal(
    repo_url: str,
    branch: str,
    file_path: str,
    diff_content: str,
) -> PipelineResult:
    events: list[AgentEvent] = []
    events.append(AgentEvent("Runtime", "info", "Loaded SOUL.md / RULES.md / DUTIES.md from disk"))
    events.append(AgentEvent("Runtime", "info", "Conflict matrix active: Auditor ⊥ Architect"))
    events.append(AgentEvent("Runtime", "info", f"Target: {repo_url}@{branch} :: {file_path}"))

    summary, findings = auditor(file_path, diff_content, events)
    critical = [f for f in findings if str(f.get("severity", "")).lower() in CRITICAL_SEVERITIES]

    if not critical:
        events.append(AgentEvent("Runtime", "success", "Pipeline outcome: Clean (no heal needed)"))
        return PipelineResult(
            outcome="Clean",
            audit_summary=summary,
            findings=findings,
            healed_content=None,
            simulation={"skipped": True},
            transcript=[asdict(e) for e in events],
        )

    healed = architect(file_path, diff_content, findings, events)
    sim = simulate(file_path, healed, events)
    outcome = "Self-Healed" if sim["passed"] else "Heal-Failed"
    events.append(AgentEvent(
        "Runtime",
        "success" if sim["passed"] else "error",
        f"Pipeline outcome: {outcome}",
    ))
    return PipelineResult(
        outcome=outcome,
        audit_summary=summary,
        findings=findings,
        healed_content=healed if sim["passed"] else None,
        simulation=sim,
        transcript=[asdict(e) for e in events],
    )
