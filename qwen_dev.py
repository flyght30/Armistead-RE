"""
Qwen Dev Assistant — General-Purpose Local AI Developer Tool
Runs via Ollama + Qwen2.5 on Apple Silicon.

Features:
- File generation: writes code directly to project folders
- Git integration: auto-commit per step, push per phase
- GitHub tools: clone, branch, PR creation, issue reading
- Internet search: DuckDuckGo for docs/APIs/references
- Chain of Verification: mandatory after every phase (non-negotiable)
- Multi-project: point at any folder, any project

Usage:
    python qwen_dev.py init /path/to/project          # Initialize a new project config
    python qwen_dev.py run /path/to/project            # Run all phases
    python qwen_dev.py run /path/to/project --phase 1  # Run single phase
    python qwen_dev.py run /path/to/project --dry-run  # Preview without executing
    python qwen_dev.py search "FastAPI async SQLAlchemy tutorial"  # Quick web search
    python qwen_dev.py ask "How do I set up Resend webhooks?"     # Quick question

Requirements:
    pip install langchain-ollama langchain-core langchain-community duckduckgo-search
"""

import os
import re
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun

# ─── Configuration ───────────────────────────────────────────────────────────

DEFAULT_MODEL = "qwen2.5-coder:7b"
OLLAMA_URL = "http://localhost:11434"
MAX_CONTEXT = 8192
TEMPERATURE = 0.2
CONFIG_FILE = "qwen_dev.json"

# ─── File Parsing ────────────────────────────────────────────────────────────

FILE_PATTERN = re.compile(
    r"===FILE:\s*(.+?)===\s*\n(.*?)===END FILE===",
    re.DOTALL,
)


def extract_files(output: str) -> list[tuple[str, str]]:
    """Parse ===FILE: path=== ... ===END FILE=== blocks from LLM output."""
    files = FILE_PATTERN.findall(output)
    return [(path.strip(), content.strip()) for path, content in files]


def write_files(files: list[tuple[str, str]], base_dir: Path) -> list[str]:
    """Write extracted files to disk."""
    written = []
    for rel_path, content in files:
        rel_path = rel_path.lstrip("/").lstrip("./")
        full_path = base_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content + "\n")
        written.append(rel_path)
        print(f"    ✓ {rel_path}")
    return written


# ─── Internet Search ─────────────────────────────────────────────────────────


class WebSearch:
    """DuckDuckGo web search for docs, APIs, and references."""

    def __init__(self):
        self.tool = DuckDuckGoSearchRun()

    def search(self, query: str, max_results: int = 5) -> str:
        """Search the web and return results."""
        try:
            results = self.tool.invoke(query)
            return results
        except Exception as e:
            return f"Search failed: {e}"


# ─── Git / GitHub Tools ─────────────────────────────────────────────────────


class GitTools:
    """Git and GitHub operations."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def _run(self, cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        """Run a command in the project directory."""
        return subprocess.run(
            cmd,
            cwd=self.project_dir,
            capture_output=True,
            text=True,
            **kwargs,
        )

    # ── Git ──

    def init(self) -> str:
        """Initialize git repo if not already initialized."""
        git_dir = self.project_dir / ".git"
        if git_dir.exists():
            return "Git repo already initialized."
        result = self._run(["git", "init"])
        return result.stdout or result.stderr

    def add_all(self) -> str:
        result = self._run(["git", "add", "-A"])
        return result.stdout or result.stderr

    def commit(self, message: str) -> bool:
        """Stage and commit all changes."""
        self._run(["git", "add", "-A"])
        status = self._run(["git", "status", "--porcelain"])
        if not status.stdout.strip():
            print("    (no changes to commit)")
            return False
        result = self._run(["git", "commit", "-m", message])
        if result.returncode == 0:
            print(f"    ✓ Committed: {message}")
            return True
        print(f"    ✗ Commit failed: {result.stderr}")
        return False

    def push(self, branch: str = "") -> bool:
        """Push to remote."""
        cmd = ["git", "push"]
        if branch:
            cmd.extend(["-u", "origin", branch])
        result = self._run(cmd)
        if result.returncode == 0:
            print("    ✓ Pushed to remote")
            return True
        print(f"    ✗ Push failed: {result.stderr}")
        return False

    def create_branch(self, branch_name: str) -> str:
        """Create and checkout a new branch."""
        result = self._run(["git", "checkout", "-b", branch_name])
        return result.stdout or result.stderr

    def current_branch(self) -> str:
        result = self._run(["git", "branch", "--show-current"])
        return result.stdout.strip()

    def status(self) -> str:
        result = self._run(["git", "status", "--short"])
        return result.stdout

    def log(self, n: int = 10) -> str:
        result = self._run(["git", "log", f"--oneline", f"-{n}"])
        return result.stdout

    def diff(self) -> str:
        result = self._run(["git", "diff", "--stat"])
        return result.stdout

    # ── GitHub (via gh CLI) ──

    def gh_clone(self, repo_url: str, target_dir: Optional[str] = None) -> str:
        """Clone a GitHub repo."""
        cmd = ["gh", "repo", "clone", repo_url]
        if target_dir:
            cmd.append(target_dir)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout or result.stderr

    def gh_create_repo(self, name: str, public: bool = True) -> str:
        """Create a new GitHub repo from current directory."""
        visibility = "--public" if public else "--private"
        result = self._run([
            "gh", "repo", "create", name,
            visibility, "--source=.", "--push",
        ])
        return result.stdout or result.stderr

    def gh_create_pr(self, title: str, body: str, base: str = "main") -> str:
        """Create a pull request."""
        result = self._run([
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", base,
        ])
        return result.stdout or result.stderr

    def gh_list_issues(self, state: str = "open") -> str:
        """List GitHub issues."""
        result = self._run(["gh", "issue", "list", "--state", state])
        return result.stdout or result.stderr

    def gh_view_issue(self, number: int) -> str:
        """View a specific issue."""
        result = self._run(["gh", "issue", "view", str(number)])
        return result.stdout or result.stderr

    def gh_create_issue(self, title: str, body: str) -> str:
        """Create a new issue."""
        result = self._run([
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
        ])
        return result.stdout or result.stderr


# ─── Project Config ──────────────────────────────────────────────────────────


def load_config(project_dir: Path) -> dict:
    """Load project config from qwen_dev.json."""
    config_path = project_dir / CONFIG_FILE
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text())


def save_config(project_dir: Path, config: dict):
    """Save project config."""
    config_path = project_dir / CONFIG_FILE
    config_path.write_text(json.dumps(config, indent=2))


def init_project(project_dir: Path):
    """Initialize a new project with qwen_dev config."""
    project_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "project_name": project_dir.name,
        "created": datetime.now().isoformat(),
        "model": DEFAULT_MODEL,
        "system_prompt": "",
        "phases": {},
        "cov_history": [],
    }
    save_config(project_dir, config)
    print(f"  ✓ Initialized qwen_dev project at {project_dir}")
    print(f"  Edit {project_dir / CONFIG_FILE} to configure phases and system prompt.")


# ─── LLM Setup ──────────────────────────────────────────────────────────────


def setup_llm(model: str) -> OllamaLLM:
    return OllamaLLM(
        model=model,
        base_url=OLLAMA_URL,
        temperature=TEMPERATURE,
        num_ctx=MAX_CONTEXT,
    )


# ─── System Prompt Builder ──────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are a senior full-stack developer working on a software project.

CRITICAL OUTPUT FORMAT:
You MUST output code using file markers so the system can automatically create files.
For EVERY file, use this exact format:

===FILE: path/to/file.py===
(file contents here)
===END FILE===

RULES:
1. Output ONLY code wrapped in file markers. No explanations outside of code comments.
2. Use type hints everywhere in Python.
3. Include proper error handling and logging.
4. Each file should be complete and runnable — no placeholders or TODOs.
5. Use environment variables for all secrets and config.
6. Write production-quality code, not prototypes.
7. EVERY file MUST be wrapped in ===FILE: ...=== and ===END FILE=== markers."""

COV_SYSTEM_PROMPT = """You are a meticulous code reviewer. You verify generated code against
product requirements using a Chain of Verification (CoV) process.

For each verification question:
- PASS: requirement is fully met (cite specific code)
- FAIL: requirement is missing or incorrect (explain what needs fixing)
- PARTIAL: partially implemented (explain what's missing)

If you find issues, output fix files using ===FILE: path=== / ===END FILE=== markers.
End with an overall confidence score (0-100%) and remaining gaps.
CoV is MANDATORY — every phase must pass verification before proceeding."""


# ─── Chain of Verification ───────────────────────────────────────────────────


def generate_cov_questions(
    llm: OllamaLLM,
    phase_name: str,
    phase_prompt: str,
    code_output: str,
) -> str:
    """Auto-generate CoV questions based on the phase requirements, then verify."""
    cov_prompt = ChatPromptTemplate.from_messages([
        ("system", COV_SYSTEM_PROMPT),
        ("human", """Phase: {phase_name}

Phase requirements:
{phase_prompt}

Code generated:
{code_output}

Perform a Chain of Verification:
1. Generate 5-8 verification questions based on the phase requirements above
2. Answer each question by reviewing the generated code (PASS / FAIL / PARTIAL)
3. Output fix files for any FAIL or PARTIAL items using ===FILE: ...=== markers
4. End with overall confidence score (0-100%) and list of remaining gaps

This verification is MANDATORY. Be thorough and precise."""),
    ])

    chain = cov_prompt | llm
    result = chain.invoke({
        "phase_name": phase_name,
        "phase_prompt": phase_prompt[:2000],  # Keep within context limits
        "code_output": code_output[-3000:],  # Use recent output
    })
    return result


# ─── Phase Runner ────────────────────────────────────────────────────────────


def run_step(
    llm: OllamaLLM,
    system_prompt: str,
    step_prompt: str,
    previous_context: str,
    search: Optional[WebSearch] = None,
    search_queries: Optional[list[str]] = None,
) -> str:
    """Run a single step, optionally with web search context."""

    # If search queries are provided, gather context first
    search_context = ""
    if search and search_queries:
        print("    Searching web for context...")
        for query in search_queries:
            print(f"      🔍 {query}")
            result = search.search(query)
            search_context += f"\n[Search: {query}]\n{result}\n"

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Previous work:\n{previous}\n\n{search_context}\nCurrent task:\n{task}"),
    ])

    chain = prompt | llm
    result = chain.invoke({
        "previous": previous_context,
        "search_context": search_context if search_context else "(no search context)",
        "task": step_prompt,
    })
    return result


def truncate_context(text: str, max_chars: int = 3000) -> str:
    if len(text) > max_chars:
        return f"[Earlier output truncated]\n...{text[-max_chars:]}"
    return text


def save_log(log_dir: Path, phase_id: str, step_id: str, title: str, output: str):
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"phase{phase_id}_step{step_id}_{timestamp}.md"
    log_path = log_dir / filename
    content = f"# Phase {phase_id} — Step {step_id}: {title}\n"
    content += f"**Generated:** {datetime.now().isoformat()}\n\n"
    content += output + "\n"
    log_path.write_text(content)
    print(f"    Log: {log_path.name}")


def run_phases(
    project_dir: Path,
    config: dict,
    model: str = DEFAULT_MODEL,
    phase_filter: Optional[str] = None,
    start_step: int = 1,
    dry_run: bool = False,
):
    """Run phases from config with file writing, git, search, and CoV."""

    llm = setup_llm(model)
    git = GitTools(project_dir)
    search = WebSearch()
    log_dir = project_dir / "build_logs"

    system_prompt = config.get("system_prompt", "") or BASE_SYSTEM_PROMPT
    phases = config.get("phases", {})

    if not phases:
        print("  No phases defined in config. Edit qwen_dev.json to add phases.")
        return

    if phase_filter:
        if phase_filter not in phases:
            print(f"  Phase '{phase_filter}' not found. Available: {list(phases.keys())}")
            return
        phases = {phase_filter: phases[phase_filter]}

    previous_context = "(Starting fresh — no previous output)"

    for phase_id, phase in phases.items():
        phase_name = phase.get("name", f"Phase {phase_id}")
        steps = phase.get("steps", [])

        print(f"\n{'='*70}")
        print(f"  PHASE {phase_id}: {phase_name}")
        print(f"{'='*70}")

        phase_code_context = ""
        phase_prompts = ""

        for i, step in enumerate(steps, 1):
            step_id = step.get("id", str(i))
            title = step.get("title", f"Step {i}")
            prompt = step.get("prompt", "")
            search_queries = step.get("search", [])  # Optional web searches

            if i < start_step:
                print(f"\n  Skipping step {step_id}: {title}")
                continue

            print(f"\n  --- Step {step_id}: {title} ---\n")

            if dry_run:
                print(f"  [DRY RUN] Would execute: {title}")
                if search_queries:
                    print(f"  Would search: {search_queries}")
                print(f"  Prompt: {prompt[:200]}...")
                continue

            try:
                result = run_step(
                    llm=llm,
                    system_prompt=system_prompt,
                    step_prompt=prompt,
                    previous_context=previous_context,
                    search=search if search_queries else None,
                    search_queries=search_queries if search_queries else None,
                )

                save_log(log_dir, phase_id, step_id, title, result)

                files = extract_files(result)
                if files:
                    print(f"\n  Writing {len(files)} files:")
                    written = write_files(files, project_dir)
                    if written:
                        git.commit(f"Phase {phase_id} Step {step_id}: {title}")
                else:
                    print("  ⚠ No file markers found. Check build_logs for raw output.")

                phase_code_context += f"\n\n--- Step {step_id} ---\n{result}"
                phase_prompts += f"\n{prompt}"
                previous_context = truncate_context(result)

            except Exception as e:
                print(f"\n  ERROR in step {step_id}: {e}")
                continue

        # ── MANDATORY Chain of Verification ──
        if not dry_run and phase_code_context:
            print(f"\n  {'─'*50}")
            print(f"  CHAIN OF VERIFICATION — Phase {phase_id} (MANDATORY)")
            print(f"  {'─'*50}\n")

            try:
                cov_result = generate_cov_questions(
                    llm=llm,
                    phase_name=phase_name,
                    phase_prompt=phase_prompts,
                    code_output=phase_code_context,
                )

                print(cov_result)
                save_log(log_dir, phase_id, "cov", f"CoV — {phase_name}", cov_result)

                # Apply any fix files from CoV
                fix_files = extract_files(cov_result)
                if fix_files:
                    print(f"\n  CoV produced {len(fix_files)} fixes:")
                    written = write_files(fix_files, project_dir)
                    if written:
                        git.commit(f"Phase {phase_id} CoV fixes")

                # Log CoV to config
                cov_entry = {
                    "phase": phase_id,
                    "timestamp": datetime.now().isoformat(),
                    "fixes_applied": len(fix_files),
                }
                config.setdefault("cov_history", []).append(cov_entry)
                save_config(project_dir, config)

            except Exception as e:
                print(f"  CoV ERROR: {e}")
                print("  ⚠ CoV is mandatory — review this phase manually before proceeding.")

        # Push after each phase
        if not dry_run:
            print(f"\n  Pushing Phase {phase_id} to remote...")
            git.push()

        print(f"\n  Phase {phase_id} complete.")


# ─── Quick Commands ──────────────────────────────────────────────────────────


def quick_search(query: str, model: str = DEFAULT_MODEL):
    """Search the web and get AI-summarized answer."""
    llm = setup_llm(model)
    search = WebSearch()

    print(f"\n  🔍 Searching: {query}\n")
    results = search.search(query)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Summarize the search results concisely. Focus on actionable information, code examples, and direct answers."),
        ("human", "Search query: {query}\n\nResults:\n{results}\n\nProvide a clear, concise summary with any relevant code examples."),
    ])
    chain = prompt | llm
    answer = chain.invoke({"query": query, "results": results})
    print(answer)


def quick_ask(question: str, model: str = DEFAULT_MODEL):
    """Ask Qwen a question directly."""
    llm = setup_llm(model)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a senior developer. Give concise, practical answers with code examples when relevant."),
        ("human", "{question}"),
    ])
    chain = prompt | llm
    answer = chain.invoke({"question": question})
    print(f"\n{answer}")


# ─── TTC Project Config Generator ───────────────────────────────────────────


def generate_ttc_config(project_dir: Path):
    """Generate the TTC-specific config file for Armistead-RE."""
    config = {
        "project_name": "Transaction-to-Close (TTC)",
        "created": datetime.now().isoformat(),
        "model": DEFAULT_MODEL,
        "system_prompt": """You are a senior full-stack developer building Transaction-to-Close (TTC),
an AI-powered real estate transaction coordinator.

Tech stack:
- Frontend: React 18+ / TypeScript / Tailwind CSS / Zustand
- Backend: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / Alembic
- Database: PostgreSQL 16+ / Redis 7+
- Storage: AWS S3 (MinIO for local dev)
- Email: Resend (REST API, React Email templates)
- Auth: Clerk
- Jobs: Celery + Redis
- AI: Claude API (Anthropic) for contract parsing, email composition, inspection analysis
- Containerization: Docker + Docker Compose

CRITICAL OUTPUT FORMAT:
You MUST output code using file markers:
===FILE: path/to/file.py===
(contents)
===END FILE===

RULES:
1. Output ONLY code wrapped in file markers.
2. Type hints everywhere in Python. async/await for all DB and API operations.
3. Production-quality — no placeholders, no TODOs.
4. Environment variables for all secrets.""",
        "phases": {
            "1": {
                "name": "Foundation & Contract Parsing",
                "steps": [
                    {
                        "id": "1.1",
                        "title": "Project scaffolding & Docker Compose",
                        "search": ["FastAPI Docker Compose PostgreSQL Redis MinIO 2025 setup"],
                        "prompt": "Create project scaffolding: docker-compose.yml (backend, frontend, postgres, redis, minio), backend/requirements.txt, backend/app/config.py (pydantic-settings), backend/app/main.py (FastAPI + CORS + health check), backend/Dockerfile, .env.example, .gitignore. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "1.2",
                        "title": "Database models & migrations",
                        "search": ["SQLAlchemy 2.0 async UUID models PostgreSQL 2025"],
                        "prompt": "Create SQLAlchemy 2.0 async models: users, transactions, parties, milestones, communications, inspection_analyses, inspection_items, amendments, email_templates. Include database.py (async engine), all model files, Alembic setup. UUID PKs, timestamps, proper FKs/cascades. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "1.3",
                        "title": "Pydantic schemas & API endpoints",
                        "prompt": "Create Pydantic schemas (transaction, party, common) and FastAPI routes: transactions CRUD + parse + confirm, parties CRUD. Include service layer. Auth middleware placeholder. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "1.4",
                        "title": "S3 upload & Claude contract parser",
                        "search": ["Anthropic Claude API Python SDK structured output 2025", "PyMuPDF PDF text extraction Python"],
                        "prompt": "Create S3/MinIO storage service, Claude API contract parser agent (with PDF text extraction via PyMuPDF, vision fallback for scanned PDFs, confidence scores, retry/backoff, 429 handling), parsing orchestration service, extraction schemas. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "1.5",
                        "title": "Frontend scaffolding & dashboard",
                        "search": ["React 18 TypeScript Tailwind Clerk auth setup 2025"],
                        "prompt": "Create React + TypeScript frontend: package.json, tsconfig, tailwind config, main.tsx (providers), App.tsx (router), API client, TypeScript types, Zustand store, Dashboard page, NewTransaction page, TransactionDetail page, FileUpload/PartyCard/ConfidenceBadge/Layout components. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                ],
            },
            "2": {
                "name": "Communications Engine",
                "steps": [
                    {
                        "id": "2.1",
                        "title": "Email Composer AI Agent",
                        "prompt": "Create EmailComposer agent (Claude API, role-specific emails by representation side, cash/multi-party/dual handling), email generation service, email schemas. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "2.2",
                        "title": "Resend integration & delivery",
                        "search": ["Resend Python SDK email sending webhooks 2025"],
                        "prompt": "Create Resend email service (send with attachments, Reply-To agent email, idempotency keys, retry via Celery), email Celery tasks, webhook handler, email API routes. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "2.3",
                        "title": "Email preview & send UI",
                        "prompt": "Create EmailPreview page, EmailEditor component, CommunicationLog component, Settings page (signature config). Update TransactionDetail with Generate Emails flow. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                ],
            },
            "3": {
                "name": "Milestone Tracking & Follow-Ups",
                "steps": [
                    {
                        "id": "3.1",
                        "title": "Milestone engine",
                        "prompt": "Create milestone service (auto-generate from contract dates, conditional for cash, closing date cascade, overdue detection), milestone API routes, milestone schemas. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "3.2",
                        "title": "Celery reminders & follow-ups",
                        "search": ["Celery beat periodic tasks Redis broker Python 2025"],
                        "prompt": "Create Celery app config, reminder tasks (check upcoming/overdue milestones), follow-up tasks (milestone completion triggers emails), notification service, beat schedule. Update docker-compose for workers. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "3.3",
                        "title": "Milestone timeline UI",
                        "prompt": "Create MilestoneTimeline, MilestoneCard, AddMilestone, NotificationBell components. Update TransactionDetail and Dashboard. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                ],
            },
            "4": {
                "name": "Inspection Report Analysis",
                "steps": [
                    {
                        "id": "4.1",
                        "title": "Inspection Analyzer AI Agent",
                        "prompt": "Create InspectionAnalyzer agent (severity classification, cost estimates, safety review, executive summary, recommendations), inspection service, API routes, schemas. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "4.2",
                        "title": "Inspection analysis UI",
                        "prompt": "Create InspectionAnalysis page, InspectionSummary, FindingCard, SeverityBadge components. Update TransactionDetail. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                ],
            },
            "5": {
                "name": "Polish, Integration & Launch Prep",
                "steps": [
                    {
                        "id": "5.1",
                        "title": "Integration & error handling",
                        "prompt": "Create unified router, error handler middleware, Clerk auth middleware, rate limiter. Wire integrations (confirm → milestones + emails, milestone complete → follow-ups, etc.). Create test fixtures and test files. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                    {
                        "id": "5.2",
                        "title": "UI polish & onboarding",
                        "prompt": "Create LoadingSpinner, EmptyState, ErrorBoundary, Toast, Onboarding page, TransactionStatusBadge. Add proper loading/empty/error states to all pages. Wrap EVERY file in ===FILE: path=== / ===END FILE=== markers.",
                    },
                ],
            },
        },
        "cov_history": [],
    }

    save_config(project_dir, config)
    print(f"  ✓ Generated TTC config at {project_dir / CONFIG_FILE}")


# ─── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Qwen Dev Assistant — Local AI Developer Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qwen_dev.py init ~/projects/my-app
  python qwen_dev.py init-ttc ~/coding_projects/Armistead-RE
  python qwen_dev.py run ~/projects/my-app --phase 1
  python qwen_dev.py run ~/projects/my-app --dry-run
  python qwen_dev.py search "how to set up Resend webhooks in Python"
  python qwen_dev.py ask "What's the best way to handle JWT refresh tokens?"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    init_parser = subparsers.add_parser("init", help="Initialize a new project config")
    init_parser.add_argument("project_dir", type=Path)

    # init-ttc (generate TTC-specific config)
    ttc_parser = subparsers.add_parser("init-ttc", help="Generate TTC project config")
    ttc_parser.add_argument("project_dir", type=Path)

    # run
    run_parser = subparsers.add_parser("run", help="Run phases for a project")
    run_parser.add_argument("project_dir", type=Path)
    run_parser.add_argument("--phase", type=str, help="Run only this phase")
    run_parser.add_argument("--step", type=int, default=1, help="Start from this step")
    run_parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
    run_parser.add_argument("--dry-run", action="store_true")

    # search
    search_parser = subparsers.add_parser("search", help="Search the web with AI summary")
    search_parser.add_argument("query", type=str)
    search_parser.add_argument("--model", type=str, default=DEFAULT_MODEL)

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask Qwen a question")
    ask_parser.add_argument("question", type=str)
    ask_parser.add_argument("--model", type=str, default=DEFAULT_MODEL)

    # git helpers
    git_parser = subparsers.add_parser("git", help="Git/GitHub operations")
    git_parser.add_argument("project_dir", type=Path)
    git_parser.add_argument("action", choices=[
        "status", "log", "push", "branch", "create-repo", "create-pr", "issues",
    ])
    git_parser.add_argument("--name", type=str, help="Branch/repo/PR name")
    git_parser.add_argument("--body", type=str, default="", help="PR/issue body")
    git_parser.add_argument("--public", action="store_true", default=True)

    args = parser.parse_args()

    if args.command == "init":
        init_project(args.project_dir)

    elif args.command == "init-ttc":
        generate_ttc_config(args.project_dir)

    elif args.command == "run":
        config = load_config(args.project_dir)
        if not config:
            print(f"  No config found at {args.project_dir / CONFIG_FILE}")
            print(f"  Run: python qwen_dev.py init {args.project_dir}")
            sys.exit(1)

        print(f"\n  Qwen Dev Assistant")
        print(f"  Project: {config.get('project_name', args.project_dir.name)}")
        print(f"  Model:   {args.model}")
        print(f"  Phase:   {args.phase or 'All'}")
        print(f"  CoV:     ALWAYS ON (mandatory)")
        if args.dry_run:
            print(f"  Mode:    DRY RUN")
        print()

        run_phases(
            project_dir=args.project_dir,
            config=config,
            model=args.model,
            phase_filter=args.phase,
            start_step=args.step,
            dry_run=args.dry_run,
        )

        print(f"\n{'='*70}")
        print(f"  Done. Logs: {args.project_dir / 'build_logs'}")
        print(f"{'='*70}\n")

    elif args.command == "search":
        quick_search(args.query, model=args.model)

    elif args.command == "ask":
        quick_ask(args.question, model=args.model)

    elif args.command == "git":
        git = GitTools(args.project_dir)
        if args.action == "status":
            print(git.status())
        elif args.action == "log":
            print(git.log())
        elif args.action == "push":
            git.push()
        elif args.action == "branch":
            if args.name:
                print(git.create_branch(args.name))
            else:
                print(f"Current branch: {git.current_branch()}")
        elif args.action == "create-repo":
            name = args.name or args.project_dir.name
            print(git.gh_create_repo(name, public=args.public))
        elif args.action == "create-pr":
            if not args.name:
                print("  --name required for PR title")
                sys.exit(1)
            print(git.gh_create_pr(args.name, args.body))
        elif args.action == "issues":
            print(git.gh_list_issues())


if __name__ == "__main__":
    main()
