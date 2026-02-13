"""
Transaction-to-Close (TTC) — Phased Code Generator
Runs locally via Ollama + Qwen2.5-14B (or qwen2.5-coder:14b).
Generates project code phase-by-phase, writes files to disk, commits to git,
and runs Chain of Verification after each phase.

Usage:
    python phases.py                    # Run all phases sequentially
    python phases.py --phase 1          # Run only Phase 1
    python phases.py --phase 1 --step 2 # Run Phase 1, starting from step 2
    python phases.py --model qwen2.5-coder:14b  # Use coder model
    python phases.py --dry-run          # Preview phases without executing
    python phases.py --no-git           # Skip git commits
    python phases.py --no-cov           # Skip Chain of Verification
"""

import os
import re
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# ─── Configuration ───────────────────────────────────────────────────────────

PROJECT_DIR = Path("/Users/pettismini/Desktop/mini-coding-projects/Armistead-RE")
LOG_DIR = PROJECT_DIR / "build_logs"
DEFAULT_MODEL = "qwen2.5-coder:7b"
OLLAMA_URL = "http://localhost:11434"

# Keep context manageable for 16GB RAM
MAX_CONTEXT = 8192
TEMPERATURE = 0.2  # Low for consistent code output

# ─── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior full-stack developer building Transaction-to-Close (TTC),
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

Project structure:
```
Armistead-RE/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   ├── api/                 # Route handlers
│   │   ├── services/            # Business logic
│   │   ├── agents/              # AI agent wrappers (Claude API)
│   │   └── tasks/               # Celery background tasks
│   ├── alembic/                 # Database migrations
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/                 # API client, utilities
│   │   ├── stores/              # Zustand stores
│   │   └── types/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── docs/                        # Existing phase docs (PRD, etc.)
```

CRITICAL OUTPUT FORMAT:
You MUST output code using file markers so the system can automatically create files.
For EVERY file, use this exact format:

===FILE: path/to/file.py===
(file contents here)
===END FILE===

Example:
===FILE: backend/app/config.py===
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost/ttc"
===END FILE===

RULES:
1. Output ONLY code wrapped in file markers. No explanations outside of code comments.
2. Use type hints everywhere in Python.
3. Use async/await for all database and API operations.
4. Follow the exact project structure above.
5. Include proper error handling and logging.
6. Each file should be complete and runnable — no placeholders or TODOs.
7. Use environment variables for all secrets and config.
8. Write production-quality code, not prototypes.
9. EVERY file MUST be wrapped in ===FILE: ...=== and ===END FILE=== markers."""

# ─── Chain of Verification Prompts ───────────────────────────────────────────

COV_PROMPTS = {
    1: """You are a senior code reviewer performing a Chain of Verification (CoV) on Phase 1: Foundation & Contract Parsing.

Review the code that was just generated and answer these verification questions:

**Q1:** Does the database schema match the PRD exactly? Are all tables, columns, types, and relationships correct?
**Q2:** Does the contract parser handle scanned PDFs (vision fallback when text < 100 chars)?
**Q3:** Does the parser detect cash transactions, multi-party contracts, and non-standard contracts?
**Q4:** Does the Claude API wrapper include retry logic with exponential backoff and 429 handling?
**Q5:** Are all API endpoints protected with auth middleware?
**Q6:** Does the frontend include confidence score display and low-confidence field highlighting?
**Q7:** Is the file upload limited to 25MB with PDF/image validation?

For each question, answer:
- PASS: requirement is met (cite the specific code)
- FAIL: requirement is missing or incorrect (explain what needs fixing)
- PARTIAL: partially implemented (explain what's missing)

Then output any fix files using the same ===FILE: ...=== format.

End with an overall confidence score (0-100%) and list of any remaining gaps.""",

    2: """You are a senior code reviewer performing a Chain of Verification (CoV) on Phase 2: Communications Engine.

Review the code and answer these verification questions:

**Q1:** Does the email composer generate the correct emails per representation side (buyer: 4, seller: 4, dual: 3-4)?
**Q2:** Are cash transactions handled (no lender email generated)?
**Q3:** Is multi-party naming handled correctly ("Dear John and Jane Smith")?
**Q4:** Does idempotency prevent double-sends within 60 seconds?
**Q5:** Are Resend webhooks handled (delivery, open, bounce status updates)?
**Q6:** Is Reply-To set to the agent's email (not a no-reply address)?
**Q7:** Does the UI enforce agent preview/approval before ANY email is sent?
**Q8:** Are parties with missing email addresses skipped with a warning (not an error)?

For each: PASS / FAIL / PARTIAL with explanation.
Output fix files using ===FILE: ...=== format if needed.
End with confidence score and remaining gaps.""",

    3: """You are a senior code reviewer performing a Chain of Verification (CoV) on Phase 3: Milestone Tracking.

Review the code and answer these verification questions:

**Q1:** Are milestones auto-generated from contract dates when a transaction is confirmed?
**Q2:** Are appraisal and financing milestones SKIPPED for cash transactions?
**Q3:** Does closing date extension cascade to all downstream milestones?
**Q4:** Are all timestamps stored in UTC?
**Q5:** Is Celery configured with Redis AOF for job reliability?
**Q6:** Are reminder emails configurable (days before deadline)?
**Q7:** Is milestone completion idempotent (completing twice doesn't send duplicate follow-ups)?
**Q8:** Does the follow-up email schedule match the PRD (earnest money → all, inspection → buyer, etc.)?

For each: PASS / FAIL / PARTIAL with explanation.
Output fix files using ===FILE: ...=== format if needed.
End with confidence score and remaining gaps.""",

    4: """You are a senior code reviewer performing a Chain of Verification (CoV) on Phase 4: Inspection Analysis.

Review the code and answer these verification questions:

**Q1:** Does the analyzer classify findings into exactly 5 severity levels (critical/major/moderate/minor/cosmetic)?
**Q2:** Are cost estimates framed as "estimated ranges" with disclaimers (not professional quotes)?
**Q3:** Is there a mandatory safety category review even when no critical issues are found?
**Q4:** Does the executive summary include: overall risk level, top 5 priorities, total cost range, and recommendation?
**Q5:** Does it handle scanned inspection reports (vision fallback)?
**Q6:** Are recommendation categories correct: proceed as-is, request repairs, request credit, further evaluation, consider walking away?
**Q7:** Does repair status tracking support all states: identified → requested → countered → agreed → denied → completed?

For each: PASS / FAIL / PARTIAL with explanation.
Output fix files using ===FILE: ...=== format if needed.
End with confidence score and remaining gaps.""",

    5: """You are a senior code reviewer performing a Chain of Verification (CoV) on Phase 5: Polish & Launch.

Review the code and answer these verification questions:

**Q1:** Does the full integration work: confirm → milestones + emails auto-generated?
**Q2:** Does milestone completion → trigger follow-up emails?
**Q3:** Does inspection upload → update inspection milestone status?
**Q4:** Does closing date change → cascade milestones → notify parties?
**Q5:** Are all error paths returning structured JSON with clear messages?
**Q6:** Is auth isolation verified (Agent A cannot access Agent B's data)?
**Q7:** Does the onboarding flow guide a new agent from signup to first transaction in < 10 minutes?
**Q8:** Are all pages mobile-responsive with proper loading/empty/error states?

For each: PASS / FAIL / PARTIAL with explanation.
Output fix files using ===FILE: ...=== format if needed.
End with confidence score and remaining gaps.""",
}

# ─── Phase Definitions ───────────────────────────────────────────────────────

PHASES = {
    1: {
        "name": "Foundation & Contract Parsing",
        "steps": [
            {
                "id": "1.1",
                "title": "Project scaffolding & Docker Compose",
                "prompt": """Create the project scaffolding for TTC:

1. docker-compose.yml with services: backend (FastAPI), frontend (React), postgres, redis, minio (S3-compatible)
2. backend/requirements.txt with all dependencies
3. backend/app/__init__.py (empty)
4. backend/app/config.py using pydantic-settings for environment config
5. backend/app/main.py with FastAPI app, CORS, and health check endpoint
6. backend/Dockerfile (Python 3.11, uvicorn)
7. .env.example with all required environment variables
8. .gitignore (Python + Node + Docker + .env)

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "1.2",
                "title": "Database models & migrations",
                "prompt": """Create the SQLAlchemy 2.0 async database models for TTC:

Tables needed (from the PRD):
- users (id UUID, clerk_id, email, name, phone, brokerage_name, license_number, state, email_signature, settings JSONB)
- transactions (id UUID, agent_id FK, status, representation_side, financing_type, property_address/city/state/zip, purchase_price, earnest_money_amount, closing_date, contract_document_url, special_stipulations, ai_extraction_confidence JSONB)
- parties (id UUID, transaction_id FK, role, name, email, phone, company, is_primary bool, notes)
- milestones (id UUID, transaction_id FK, type, title, due_date, status, responsible_party_role, notes, completed_at, reminder_days_before, last_reminder_sent_at, sort_order)
- communications (id UUID, transaction_id FK, milestone_id FK nullable, recipient_party_id FK nullable, type, recipient_email, subject, body, attachments JSONB, status, resend_message_id, sent_at, opened_at, clicked_at, template_used)
- inspection_analyses (id UUID, transaction_id FK, report_document_url, executive_summary, total_estimated_cost_low/high, overall_risk_level)
- inspection_items (id UUID, analysis_id FK, description, location, severity, estimated_cost_low/high, risk_assessment, recommendation, repair_status, sort_order)
- amendments (id UUID, transaction_id FK, field_changed, old_value, new_value, reason, changed_by FK, notification_sent bool)
- email_templates (id UUID, agent_id FK nullable, name, type, representation_side nullable, recipient_role, subject_template, body_template, is_active bool)

Create:
1. backend/app/database.py — async engine, session factory, Base
2. backend/app/models/__init__.py — import all models
3. backend/app/models/user.py
4. backend/app/models/transaction.py
5. backend/app/models/party.py
6. backend/app/models/milestone.py
7. backend/app/models/communication.py
8. backend/app/models/inspection.py
9. backend/app/models/amendment.py
10. backend/app/models/email_template.py
11. Alembic setup: alembic.ini and alembic/env.py configured for async

Use UUID primary keys, created_at/updated_at timestamps, and proper relationships/cascades.
Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "1.3",
                "title": "Pydantic schemas & API endpoints (transactions, parties)",
                "prompt": """Create the Pydantic schemas and FastAPI route handlers for transactions and parties.

Schemas (backend/app/schemas/):
- transaction.py: TransactionCreate, TransactionUpdate, TransactionResponse, TransactionList (with pagination)
- party.py: PartyCreate, PartyUpdate, PartyResponse
- common.py: PaginationParams, APIResponse wrapper

API Routes (backend/app/api/):
- __init__.py: unified router
- transactions.py:
  - POST /api/transactions — create transaction with file upload
  - GET /api/transactions — list with pagination, filtering by status
  - GET /api/transactions/{id} — full detail with parties
  - PATCH /api/transactions/{id} — update fields (log amendments)
  - DELETE /api/transactions/{id} — soft delete
  - POST /api/transactions/{id}/parse — trigger AI contract parsing
  - POST /api/transactions/{id}/confirm — confirm and activate
- parties.py (nested under transaction):
  - POST /api/transactions/{id}/parties
  - PATCH /api/transactions/{id}/parties/{party_id}
  - DELETE /api/transactions/{id}/parties/{party_id}

Services (backend/app/services/):
- transaction_service.py — CRUD + business logic
- party_service.py — CRUD

Include proper auth middleware placeholder (Clerk JWT validation), error handling, and request validation.
Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "1.4",
                "title": "S3 file upload & Claude API contract parser",
                "prompt": """Create the file upload infrastructure and AI contract parsing agent.

1. backend/app/services/storage_service.py
   - Upload file to S3/MinIO
   - Generate pre-signed download URLs (15-min expiry)
   - Support PDF and image files (max 25MB)

2. backend/app/agents/__init__.py
3. backend/app/agents/contract_parser.py
   - Claude API integration for contract parsing
   - PDF text extraction via PyMuPDF (fitz) — if text < 100 chars, fall back to vision
   - System prompt from Phase 1 spec (extract property, financial, parties, dates, etc.)
   - Returns structured JSON matching the extraction schema
   - Confidence scores per field
   - Detects: financing type, representation side, cash transactions, multi-party, non-standard contracts
   - Retry logic with exponential backoff (3 retries)
   - Handle 429 rate limits

4. backend/app/services/parsing_service.py
   - Orchestrates: upload file → extract text → call parser agent → validate response → save to DB
   - Creates transaction + parties from parsed data

5. backend/app/schemas/contract_parsing.py
   - ContractExtractionSchema (the full JSON schema from the PRD)
   - ParseResponse with status and extracted data

Use anthropic Python SDK. All config via environment variables (ANTHROPIC_API_KEY, etc.).
Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "1.5",
                "title": "Frontend scaffolding & dashboard",
                "prompt": """Create the React + TypeScript frontend scaffolding and dashboard.

1. frontend/package.json with dependencies: react, react-dom, react-router-dom, typescript, tailwindcss, @tanstack/react-query, zustand, axios, @clerk/clerk-react, lucide-react
2. frontend/tsconfig.json
3. frontend/tailwind.config.js
4. frontend/src/main.tsx — app entry with React Query + Clerk providers
5. frontend/src/App.tsx — router setup with auth guard
6. frontend/src/lib/api.ts — axios client with auth interceptor and base URL config
7. frontend/src/types/transaction.ts — TypeScript interfaces matching backend schemas
8. frontend/src/types/party.ts
9. frontend/src/stores/transactionStore.ts — Zustand store for active transaction state
10. frontend/src/pages/Dashboard.tsx — transaction list with status badges, search, and "New Transaction" button
11. frontend/src/pages/NewTransaction.tsx — file upload with drag-and-drop, parsing progress indicator
12. frontend/src/pages/TransactionDetail.tsx — full detail view with all extracted data, party list, edit capability
13. frontend/src/components/FileUpload.tsx — drag-and-drop PDF upload component
14. frontend/src/components/PartyCard.tsx — display/edit a party
15. frontend/src/components/ConfidenceBadge.tsx — shows confidence score with color coding
16. frontend/src/components/Layout.tsx — app shell with sidebar nav

Use Tailwind for all styling. Clean, professional design suitable for real estate agents.
Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
        ],
    },
    2: {
        "name": "Communications Engine",
        "steps": [
            {
                "id": "2.1",
                "title": "Email Composer AI Agent",
                "prompt": """Create the Email Composer AI agent and email generation service.

1. backend/app/agents/email_composer.py
   - Claude API integration for email generation
   - System prompt: professional real estate email composer (from Phase 2 spec)
   - Generates role-specific emails based on representation side:
     * Buyer-side: buyer welcome, lender contract delivery, attorney contract delivery, listing agent confirmation
     * Seller-side: seller welcome, attorney delivery, lender appraisal coordination, buyer agent confirmation
     * Dual-agency: buyer welcome, seller welcome, lender delivery, attorney delivery
   - Handles: cash transactions (skip lender), multi-party naming, agent signature injection
   - Returns JSON: { subject, body, recipient_role, attachments_needed }

2. backend/app/services/email_generation_service.py
   - Assembles full transaction context for the AI prompt
   - Calls EmailComposer for each recipient
   - Validates: skip parties without email addresses, show warnings
   - Returns list of draft emails ready for preview

3. backend/app/schemas/email.py
   - EmailDraft, EmailPreview, EmailSendRequest, EmailResponse
   - CommunicationLogResponse

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "2.2",
                "title": "Resend integration & email delivery",
                "prompt": """Create the Resend email delivery service and webhook handling.

1. backend/app/services/email_service.py
   - Resend SDK integration (pip: resend)
   - Send email with HTML body and optional PDF attachments
   - Configure From: notifications@yourdomain.com, Reply-To: agent's email
   - Track resend_message_id per communication
   - Idempotency: reject duplicate sends within 60-second window using idempotency keys
   - Retry logic: 3 retries over 15 minutes via Celery

2. backend/app/tasks/email_tasks.py
   - Celery task: send_email_task (async, with retry policy)
   - Celery task: process_email_batch (send multiple emails for a transaction)

3. backend/app/api/webhooks.py
   - POST /api/webhooks/resend — receive delivery/open/bounce events
   - Update communication status in DB (delivered, opened, bounced, failed)
   - Verify webhook signatures

4. backend/app/api/emails.py
   - POST /api/transactions/{id}/emails/generate — trigger AI generation
   - GET /api/transactions/{id}/emails/preview — return drafts
   - PATCH /api/transactions/{id}/emails/{email_id} — edit before send
   - POST /api/transactions/{id}/emails/send — send approved emails (all or selected)
   - GET /api/transactions/{id}/communications — list all sent emails with status

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "2.3",
                "title": "Email preview & send UI",
                "prompt": """Create the frontend email preview, editing, and sending interface.

1. frontend/src/pages/EmailPreview.tsx
   - Shows cards for each generated email: recipient, role badge, subject, body preview
   - Checkbox per email for selective sending
   - "Send All" and "Send Selected" buttons
   - Attachment indicator on lender/attorney emails
   - Warning for parties with missing email addresses
   - Loading state during generation

2. frontend/src/components/EmailEditor.tsx
   - Inline editing of subject and body (rich text or textarea)
   - Save edits via PATCH endpoint
   - Preview mode vs edit mode toggle

3. frontend/src/components/CommunicationLog.tsx
   - Timeline of all sent communications for a transaction
   - Status badges: draft, sent, delivered, opened, bounced, failed
   - Timestamps and recipient info

4. frontend/src/pages/Settings.tsx
   - Agent email signature configuration (name, title, brokerage, license, phone, email)
   - Save via PATCH /api/users/{id}/settings

5. Update frontend/src/pages/TransactionDetail.tsx to include:
   - "Generate Emails" button (appears after transaction is confirmed)
   - Communication log section
   - Flow: confirm → generate → preview → send

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
        ],
    },
    3: {
        "name": "Milestone Tracking & Follow-Ups",
        "steps": [
            {
                "id": "3.1",
                "title": "Milestone engine & auto-generation",
                "prompt": """Create the milestone tracking engine.

1. backend/app/services/milestone_service.py
   - Auto-generate milestones from contract dates when transaction is confirmed
   - Standard milestones: earnest money, inspection, wood infestation, inspection response, repair negotiation, appraisal ordered/complete, financing contingency, title search, survey, final walkthrough, closing
   - Conditional: skip appraisal + financing milestones for cash transactions
   - Calculate due dates relative to contract date and closing date
   - CRUD operations: create, update, mark complete/waived, delete
   - Handle closing date extensions: cascade all downstream milestone dates
   - Overdue detection

2. backend/app/api/milestones.py
   - GET /api/transactions/{id}/milestones — list all milestones
   - POST /api/transactions/{id}/milestones — add custom milestone
   - PATCH /api/transactions/{id}/milestones/{mid} — update (edit, complete, waive, reschedule)
   - DELETE /api/transactions/{id}/milestones/{mid}

3. backend/app/schemas/milestone.py
   - MilestoneCreate, MilestoneUpdate, MilestoneResponse, MilestoneTimeline

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "3.2",
                "title": "Celery jobs: reminders & follow-ups",
                "prompt": """Create the Celery background job system for automated reminders and follow-up emails.

1. backend/app/tasks/__init__.py — Celery app configuration with Redis broker
2. backend/app/tasks/reminder_tasks.py
   - check_upcoming_milestones: runs every hour, finds milestones due within reminder_days_before
   - send_milestone_reminder: generates and queues reminder email to responsible party
   - check_overdue_milestones: marks overdue, alerts agent

3. backend/app/tasks/followup_tasks.py
   - trigger_milestone_followup: when milestone marked complete, generate follow-up emails to all relevant parties
   - Uses EmailComposer agent to generate contextual follow-up (what happened, what's next)
   - Follow-up schedule from PRD: earnest money received → all parties, inspection complete → buyer, repairs agreed → all, financing cleared → all, closing prep (7 days) → all, etc.

4. backend/app/services/notification_service.py
   - In-app notification creation for upcoming/overdue milestones
   - Notification read/dismiss endpoints

5. Celery beat schedule config for periodic tasks
6. Update docker-compose.yml to add celery worker and celery beat services

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "3.3",
                "title": "Milestone timeline UI",
                "prompt": """Create the frontend milestone tracking interface.

1. frontend/src/components/MilestoneTimeline.tsx
2. frontend/src/components/MilestoneCard.tsx
3. frontend/src/components/AddMilestone.tsx
4. frontend/src/components/NotificationBell.tsx
5. Update TransactionDetail.tsx to include MilestoneTimeline section
6. Update Dashboard.tsx to show upcoming milestone counts per transaction

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
        ],
    },
    4: {
        "name": "Inspection Report Analysis",
        "steps": [
            {
                "id": "4.1",
                "title": "Inspection Analyzer AI Agent",
                "prompt": """Create the inspection report analysis system.

1. backend/app/agents/inspection_analyzer.py
   - Claude API integration for inspection report analysis
   - PDF text extraction (PyMuPDF), with vision fallback for scanned reports
   - Severity classification: critical, major, moderate, minor, cosmetic
   - Estimated repair cost ranges, risk-based ranking
   - Mandatory safety review even when no critical issues found
   - Executive summary with recommendation

2. backend/app/services/inspection_service.py
3. backend/app/api/inspections.py
4. backend/app/schemas/inspection.py

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "4.2",
                "title": "Inspection analysis UI",
                "prompt": """Create the frontend inspection analysis interface.

1. frontend/src/pages/InspectionAnalysis.tsx
2. frontend/src/components/InspectionSummary.tsx
3. frontend/src/components/FindingCard.tsx
4. frontend/src/components/SeverityBadge.tsx
5. Update TransactionDetail.tsx to include inspection section

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
        ],
    },
    5: {
        "name": "Polish, Integration & Launch Prep",
        "steps": [
            {
                "id": "5.1",
                "title": "End-to-end integration & error handling",
                "prompt": """Create integration glue and hardened error handling across the full app.

1. backend/app/api/__init__.py — unified router with all sub-routers mounted
2. backend/app/middleware/error_handler.py — global exception handler
3. backend/app/middleware/auth.py — Clerk JWT validation middleware
4. backend/app/middleware/rate_limit.py — basic rate limiting per user
5. Integration wiring (confirm → milestones + emails, milestone complete → follow-ups, etc.)
6. backend/tests/conftest.py — pytest fixtures
7. backend/tests/test_transactions.py
8. backend/tests/test_emails.py
9. backend/tests/test_milestones.py

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
            {
                "id": "5.2",
                "title": "UI polish & onboarding",
                "prompt": """Add UI polish, loading/empty/error states, and agent onboarding.

1. frontend/src/components/LoadingSpinner.tsx
2. frontend/src/components/EmptyState.tsx
3. frontend/src/components/ErrorBoundary.tsx
4. frontend/src/components/Toast.tsx
5. frontend/src/pages/Onboarding.tsx — guided first-use flow
6. frontend/src/components/TransactionStatusBadge.tsx
7. Update Dashboard and all pages with proper states

Remember: wrap EVERY file in ===FILE: path=== and ===END FILE=== markers.""",
            },
        ],
    },
}

# ─── File Parser ─────────────────────────────────────────────────────────────

FILE_PATTERN = re.compile(
    r"===FILE:\s*(.+?)===\s*\n(.*?)===END FILE===",
    re.DOTALL,
)


def extract_files(output: str) -> list[tuple[str, str]]:
    """Parse ===FILE: path=== ... ===END FILE=== blocks from LLM output."""
    files = FILE_PATTERN.findall(output)
    return [(path.strip(), content.strip()) for path, content in files]


def write_files(files: list[tuple[str, str]], base_dir: Path) -> list[str]:
    """Write extracted files to disk. Returns list of written file paths."""
    written = []
    for rel_path, content in files:
        # Clean up path (remove leading slashes, etc.)
        rel_path = rel_path.lstrip("/").lstrip("./")
        full_path = base_dir / rel_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content + "\n")
        written.append(rel_path)
        print(f"    ✓ {rel_path}")

    return written


# ─── Git Integration ─────────────────────────────────────────────────────────


def git_commit(message: str, base_dir: Path) -> bool:
    """Stage all changes and commit."""
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=base_dir, capture_output=True, check=True,
        )
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=base_dir, capture_output=True, text=True, check=True,
        )
        if not result.stdout.strip():
            print("    (no changes to commit)")
            return False

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=base_dir, capture_output=True, check=True,
        )
        print(f"    ✓ Committed: {message}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Git error: {e.stderr.decode() if e.stderr else e}")
        return False


def git_push(base_dir: Path) -> bool:
    """Push to remote."""
    try:
        subprocess.run(
            ["git", "push"],
            cwd=base_dir, capture_output=True, check=True,
        )
        print("    ✓ Pushed to remote")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Push failed: {e.stderr.decode() if e.stderr else e}")
        return False


# ─── Runner ──────────────────────────────────────────────────────────────────


def setup_llm(model: str) -> OllamaLLM:
    """Initialize the Ollama LLM connection."""
    return OllamaLLM(
        model=model,
        base_url=OLLAMA_URL,
        temperature=TEMPERATURE,
        num_ctx=MAX_CONTEXT,
    )


def build_chain(llm: OllamaLLM):
    """Build the LangChain prompt → LLM chain."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Previous work context:\n{previous}\n\nCurrent task:\n{task}"),
    ])
    return prompt | llm


def build_cov_chain(llm: OllamaLLM):
    """Build a separate chain for Chain of Verification reviews."""
    cov_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a meticulous code reviewer specializing in real estate software and full-stack applications. You verify code against product requirements with precision."),
        ("human", "Code generated so far:\n{code_context}\n\n{cov_prompt}"),
    ])
    return cov_prompt | llm


def save_log(phase_id: int, step_id: str, title: str, output: str):
    """Save each step's output to a log file for reference."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"phase{phase_id}_step{step_id}_{timestamp}.md"
    log_path = LOG_DIR / filename

    content = f"# Phase {phase_id} — Step {step_id}: {title}\n"
    content += f"**Generated:** {datetime.now().isoformat()}\n\n"
    content += output + "\n"

    log_path.write_text(content)
    print(f"    Log: {log_path.name}")


def truncate_context(text: str, max_chars: int = 3000) -> str:
    """Keep context within manageable limits."""
    if len(text) > max_chars:
        return f"[Earlier output truncated]\n...{text[-max_chars:]}"
    return text


def run_cov(
    llm: OllamaLLM,
    phase_id: int,
    code_context: str,
    use_git: bool = True,
):
    """Run Chain of Verification for a completed phase."""
    if phase_id not in COV_PROMPTS:
        print("    No CoV defined for this phase, skipping.")
        return

    print(f"\n  {'─'*50}")
    print(f"  CHAIN OF VERIFICATION — Phase {phase_id}")
    print(f"  {'─'*50}\n")

    cov_chain = build_cov_chain(llm)

    try:
        result = cov_chain.invoke({
            "code_context": truncate_context(code_context, max_chars=4000),
            "cov_prompt": COV_PROMPTS[phase_id],
        })

        print(result)

        # Save CoV log
        save_log(phase_id, "cov", f"Chain of Verification — Phase {phase_id}", result)

        # If CoV produced fix files, write them
        fix_files = extract_files(result)
        if fix_files:
            print(f"\n  CoV produced {len(fix_files)} fix files:")
            written = write_files(fix_files, PROJECT_DIR)
            if written and use_git:
                git_commit(f"Phase {phase_id} CoV fixes", PROJECT_DIR)

    except Exception as e:
        print(f"  CoV ERROR: {e}")


def run_phases(
    llm: OllamaLLM,
    phase_filter=None,
    start_step: int = 1,
    dry_run: bool = False,
    use_git: bool = True,
    use_cov: bool = True,
):
    """Execute phases sequentially, write files, commit, and verify."""
    chain = build_chain(llm)
    previous_context = "(Starting fresh — no previous output)"

    phases_to_run = {phase_filter: PHASES[phase_filter]} if phase_filter else PHASES

    for phase_id, phase in phases_to_run.items():
        print(f"\n{'='*70}")
        print(f"  PHASE {phase_id}: {phase['name']}")
        print(f"{'='*70}")

        phase_code_context = ""

        for i, step in enumerate(phase["steps"], 1):
            if phase_filter and i < start_step:
                print(f"\n  Skipping step {step['id']}: {step['title']}")
                continue

            print(f"\n  --- Step {step['id']}: {step['title']} ---\n")

            if dry_run:
                print(f"  [DRY RUN] Would execute: {step['title']}")
                print(f"  Prompt preview: {step['prompt'][:200]}...")
                continue

            try:
                # Generate code
                result = chain.invoke({
                    "previous": previous_context,
                    "task": step["prompt"],
                })

                # Save raw log
                save_log(phase_id, step["id"], step["title"], result)

                # Extract and write files
                files = extract_files(result)
                if files:
                    print(f"\n  Writing {len(files)} files:")
                    written = write_files(files, PROJECT_DIR)

                    # Git commit this step
                    if use_git and written:
                        git_commit(
                            f"Phase {phase_id} Step {step['id']}: {step['title']}",
                            PROJECT_DIR,
                        )
                else:
                    print("  ⚠ No file markers found in output. Check build_logs for raw output.")
                    print("    (The model may not have used ===FILE: ...=== format)")

                # Update context for next step
                phase_code_context += f"\n\n--- Step {step['id']} ---\n{result}"
                previous_context = truncate_context(result)

            except Exception as e:
                print(f"\n  ERROR in step {step['id']}: {e}")
                print("  Continuing to next step...\n")
                continue

        # Run Chain of Verification after phase completes
        if not dry_run and use_cov:
            run_cov(llm, phase_id, phase_code_context, use_git)

        # Push after each phase
        if not dry_run and use_git:
            print(f"\n  Pushing Phase {phase_id} to remote...")
            git_push(PROJECT_DIR)

        print(f"\n  Phase {phase_id} complete.")


def main():
    parser = argparse.ArgumentParser(description="TTC Phased Code Generator")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4, 5],
                        help="Run only this phase (default: all)")
    parser.add_argument("--step", type=int, default=1,
                        help="Start from this step within the phase")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                        help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview phases without executing")
    parser.add_argument("--no-git", action="store_true",
                        help="Skip git commits and pushes")
    parser.add_argument("--no-cov", action="store_true",
                        help="Skip Chain of Verification")
    args = parser.parse_args()

    print(f"\n  TTC Phased Code Generator")
    print(f"  Model:   {args.model}")
    print(f"  Project: {PROJECT_DIR}")
    print(f"  Phase:   {'All' if not args.phase else args.phase}")
    print(f"  Git:     {'OFF' if args.no_git else 'ON'}")
    print(f"  CoV:     {'OFF' if args.no_cov else 'ON'}")
    if args.dry_run:
        print(f"  Mode:    DRY RUN")
    print()

    if args.phase and args.phase not in PHASES:
        print(f"  Error: Phase {args.phase} not found.")
        sys.exit(1)

    llm = setup_llm(args.model)
    run_phases(
        llm,
        phase_filter=args.phase,
        start_step=args.step,
        dry_run=args.dry_run,
        use_git=not args.no_git,
        use_cov=not args.no_cov,
    )

    print(f"\n{'='*70}")
    print(f"  All done. Check {LOG_DIR} for output logs.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
