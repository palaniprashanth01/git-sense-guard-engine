# Git-Sense — Architecture

## TL;DR
A **GitAgent (gitclaw)-native** multi-agent system that intercepts proposed
patches, runs a **self-healing audit pipeline** (Auditor → Architect →
Simulator), and either certifies the change as clean or returns a structurally
validated heal. The agent's identity, rules, and tools live as files in this
repo, so `gitclaw --dir .` runs it natively.

## The agent IS the repo

```
agent.yaml             ← model + tools + skills + hooks (gitclaw spec)
SOUL.md                ← identity & purpose
RULES.md               ← architectural constraints (Six Sigma, no secrets, self-heal mandate)
DUTIES.md              ← conflict matrix (Auditor ⊥ Architect)
tools/
  run-audit.yaml       ← gitclaw tool definition → scripts/run_audit.py
  self-heal.yaml       ← Architect-only patch generation
skills/
  self-heal/SKILL.md   ← composable skill the agent can mount
hooks/
  hooks.yaml           ← tool:before / tool:after lifecycle hooks
  log_invocation.sh    ← writes memory/invocations.log
  log_outcome.sh       ← writes memory/outcomes.log
memory/                ← git-committed invocation + outcome logs
scripts/
  run_audit.py         ← tool entry point (stdin JSON → stdout JSON)
  run_heal.py
backend/               ← FastAPI HTTP runtime (also drives the web UI)
frontend/              ← React+TS console for human-in-the-loop runs
```

## The pipeline

```
   ┌─────────────────────────────────────────────────────────────┐
   │  POST /api/agent/audit   OR   gitclaw run-audit ...         │
   └──────────────────────┬──────────────────────────────────────┘
                          │
                          ▼
        ┌────────── agent_runtime ────────────┐
        │  loads SOUL.md / RULES.md / DUTIES  │
        │  builds role-scoped system prompts  │
        │  enforces conflict matrix           │
        └─────┬────────────────────┬──────────┘
              │                    │
              ▼                    │
     ┌────────────────┐            │
     │   AUDITOR      │ ── Groq    │
     │ severity scan  │  llama-3.1 │
     └────────┬───────┘            │
              │                    │
              ▼                    │
       no critical findings?       │
              │ yes                │
              ▼                    │
         outcome=Clean             │
                                   │
       critical findings?          │
              │ yes                │
              ▼                    │
     ┌────────────────┐            │
     │  ARCHITECT     │ ── Groq    │
     │  generates     │            │
     │  healed file   │            │
     └────────┬───────┘            │
              │                    │
              ▼                    │
     ┌────────────────┐            │
     │  SIMULATOR     │ no LLM —   │
     │  AST / JSON /  │ deterministic
     │  YAML / brace  │ structural │
     │  + secret scan │ check      │
     └────────┬───────┘            │
              │                    │
       passed?├── no → Heal-Failed │
              │ yes                │
              ▼                    │
        outcome=Self-Healed        │
        + healed_content           │
        + simulation.checks[]      │
                                   │
              ▼ in all cases       │
   ┌──────────────────────────────────────────────────────────────┐
   │  Return PipelineResult { outcome, summary, findings,         │
   │                          healed_content, simulation,         │
   │                          transcript[AgentEvent] }            │
   └──────────────────────────────────────────────────────────────┘
```

## Why three agents and a deterministic simulator

| Role | LLM? | Why it exists |
|---|---|---|
| **Auditor** | yes | Adversarial review. Wrong incentive structure to *also* fix things — would rationalize its own fixes. |
| **Architect** | yes | Single responsibility: turn findings into a corrected file. Conflict matrix in DUTIES.md blocks the Auditor from this seat. |
| **Simulator** | **no** | LLMs cannot self-attest structural validity. AST + JSON/YAML parse + brace balance + regex secret scan close the loop and prevent broken or secret-leaking heals from being labeled "Self-Healed". |

This is the cheapest possible separation of powers that still produces real
guarantees — a single-agent loop would silently approve its own slop.

## Two entry points, one pipeline

The same `agents.run_self_heal(...)` is called by:
1. **HTTP** — `POST /api/agent/audit` from the React console.
2. **Gitclaw tool** — `scripts/run_audit.py`, declared in `tools/run-audit.yaml`,
   which by default POSTs to the running backend, or runs inline with
   `GIT_SENSE_INLINE=1` for fully standalone gitclaw runs.

That means a human pressing **Trigger Guard Loop** in the UI and a gitclaw
agent calling `run-audit` go through the same code, with the same conflict
matrix enforcement, the same simulator, and the same audit-log hooks.

## Conflict matrix enforcement

`DUTIES.md` declares `- [Auditor, Architect]`. `agent_runtime.assert_role_allowed`
parses that block and raises `PermissionError` if the Auditor ever calls
`architect(...)`. The FastAPI handler maps the error to HTTP 403, so a
misbehaving caller (or LLM trying to route around the matrix) gets a hard
refusal, not a silent bypass.

## What the demo shows
1. Paste a diff containing a hardcoded `sk-...` key + an XSS sink.
2. Trigger the guard loop.
3. Auditor surfaces both findings (severity: high/critical).
4. Architect rewrites the file removing the secret and escaping output.
5. Simulator runs Python AST + secret scan → passes.
6. UI shows the full transcript, findings, healed content, and validation matrix.
7. (Optional) Click **Push to Git** to commit the healed file via `/push`.

## What's *not* in scope
- We don't fork the gitclaw runtime — we conform to its file layout so it
  drives our agent. The HTTP path exists for the human UI and CI hooks.
- Memory is on-disk append-only logs (`memory/invocations.log`,
  `memory/outcomes.log`). Embeddings live in `backend/chroma_db/` for the
  separate repo-analysis flow, not for agent memory.
