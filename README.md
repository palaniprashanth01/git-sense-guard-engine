# Git Sense — Multi-Agent Self-Healing Guard Engine

**Git Sense** is a **GitAgent (gitclaw)-native** multi-agent system that
intercepts proposed patches, runs a self-healing audit pipeline
(**Auditor → Architect → Simulator**), and either certifies the change as
clean or returns a structurally-validated heal. The agent's identity, rules,
tools, hooks, and memory live as files in this repo — `gitclaw --dir .` runs
it natively.

> Built for the **open-gitagent / gitagent** challenge.
> Full system design: [ARCHITECTURE.md](./ARCHITECTURE.md).

## What it does
1. You propose a patch (or paste a file body) for a guarded file.
2. The **Auditor** scans for security issues, hardcoded secrets, prompt drift,
   and regressions. Returns severity-graded findings.
3. If any finding is `high` / `critical`, the **Architect** generates a
   healed file body that remediates them. The Auditor cannot reach this
   step — `DUTIES.md` declares a conflict matrix that is enforced in code.
4. The **Simulator** runs **deterministic** structural validation
   (Python AST / JSON / YAML parse, brace balance, regex secret scan).
   No LLM here — a real gate, not a vibes check.
5. You get back a `{outcome, findings, healed_content, simulation, transcript}`
   payload. Outcome is one of `Clean`, `Self-Healed`, `Heal-Failed`.

## GitAgent integration

```
agent.yaml             # gitclaw spec (model, tools, skills, hooks, memory)
SOUL.md / RULES.md / DUTIES.md   # identity, rules, conflict matrix
tools/run-audit.yaml   # gitclaw tool → scripts/run_audit.py
tools/self-heal.yaml   # Architect-only heal step
skills/self-heal/      # composable skill
hooks/hooks.yaml       # tool:before / tool:after lifecycle hooks
memory/                # git-committed invocation + outcome logs
```

Run via the gitclaw CLI:

```bash
# Install gitclaw
bash <(curl -fsSL "https://raw.githubusercontent.com/open-gitagent/gitagent/main/install.sh")

# Start the backend (the tool script POSTs to it by default)
cd backend && uvicorn main:app --reload &

# Drive the agent
gitclaw --dir . "Audit prompts/system.txt against the new diff."
```

Or call the tool script directly (gitclaw-style stdin/stdout):

```bash
echo '{"repo_url":"...","branch":"main","file_path":"app/views.py","diff_content":"..."}' \
  | python scripts/run_audit.py
```

## Project Overview

Git Sense acts as an intelligent layer on top of your Git repositories. It
ingests code, creates vector embeddings for semantic search, and uses
high-performance LLMs (via Groq) to drive the multi-agent audit pipeline.
A FastAPI backend exposes both the repo-analysis surface and the
`/api/agent/audit` self-healing endpoint; a React+TS frontend renders the
validation matrix live.

## Features

- **Automated Repository Analysis**: simply paste a GitHub URL to start.
- **Deep Code Understanding**: RAG-based engine (ChromaDB + LangChain) ensures accurate context.
- **Bug & Security Detection**: Automatically identifies potential security risks and logical errors.
- **Code Quality Suggestions**: Provides actionable refactoring advice to improve maintainability.
- **Structure Analysis**: Visualizes and explains the high-level architecture of the project.
- **Automatic README Generation**: Generates comprehensive documentation for undocumented projects.
- **Push to Git**: Directly commit and push generated artifacts (like READMEs) back to the repository.
- **Persistent Caching**: Caches analysis results for instant load times on subsequent visits.
- **Live Updates**: Real-time progress tracking of the analysis pipeline.

## Installation

### Prerequisites
- Node.js (v18+)
- Python (v3.10+)
- Git installed locally

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create customizable virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure Environment:
   Create a `.env` file in `backend/` and add your Groq API keys:
   ```env
   GROQ_API_KEYS=<your_groq_api_key>
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

## Usage Examples

### 1. Start the Application
**Backend Terminal:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```
**Frontend Terminal:**
```bash
cd frontend
npm run dev
```

### 2. Analyze a Repo
1. Open your browser to `http://localhost:5173`.
2. Enter a public GitHub repository URL (e.g., `https://github.com/fastapi/fastapi`).
3. Click **Analyze**.
4. Explore the tabs: **Bugs**, **Suggestions**, **Structure**, etc.

### 3. Push Generated Content
1. Navigate to the **README** tab after analysis.
2. Review the generated README.
3. Click **Push to Git** to commit the file directly to the analyzed repository (requires local write access).

## Future Plans

- **User Authentication**: Multi-user support with private history.
- **Multi-LLM Support**: Integration with OpenAI and Anthropic models.
- **IDE Extensions**: VS Code plugin for inline analysis.
- **Cloud Deployment**: One-click deploy to Vercel/Render.
- **Custom Rule Engine**: Allow users to define custom linting rules for the AI.

## What Not To Do

- **Do Not Share API Keys**: Never commit your `.env` file containing API keys.
- **Do Not Run on Unverified Large Repos**: Indexing extremely large monorepos locally may consume significant CPU/RAM.
- **Do Not Push Without Review**: Always review the "Push to Git" content; AI can occasionally hallucinate details.
- **Do Not Ignore Security Warnings**: While the AI is good, it is not a replacement for a professional security audit.

---
*Built with ❤️ by Palani Prashanth.*
