---
name: self-heal
description: >
  Triage a proposed change against the Git-Sense architectural rules. Run the
  Auditor; if it raises critical findings, hand off to the Architect to produce
  a healed file body, then validate it with the Simulator before committing.
trigger:
  - "audit this patch"
  - "is this diff safe"
  - "self-heal the change"
---

# Self-Heal Skill

## When to invoke
- A patch / diff is proposed against a file the agent is guarding.
- A system prompt was rewritten and we need to verify semantic drift.
- A pre-commit check wants a structural simulation before merging.

## Steps
1. Call **`run-audit`** with `{repo_url, branch, file_path, diff_content}`.
2. If `outcome == "Clean"`, surface the audit summary and stop.
3. If `outcome == "Self-Healed"`, return the `healed_content` and the
   simulation transcript. Offer to push it via the `/push` endpoint.
4. If `outcome == "Heal-Failed"`, surface findings and refuse to commit per
   RULES.md §3.

## Contracts
- Auditor ⊥ Architect (DUTIES.md). Never bypass by asking one role to do the
  other's job.
- Never accept a heal that the Simulator did not pass — see RULES.md §3.
