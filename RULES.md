# Architectural Rules & Constraints

## 1. Safety and Security
- NEVER expose API keys, database credentials, or plain-text secrets during code rewrites.
- Flag any external dependency versions that introduce known CVE vulnerabilities.

## 2. Prompt Engineering Standards
- All system prompts must clearly separate instructions from input context utilizing structural Markdown elements or XML tags.
- Minimize token overhead by stripping out verbose conversational framing or fluff.

## 3. The Self-Healing Directive
- If an audited code block or system prompt fails an execution or validation check, you are strictly forbidden from simply reporting it. You MUST invoke the self-healing pipeline to generate a clean patch.
- Never commit a self-healed patch unless it passes a local structural simulation check.
