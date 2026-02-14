# Armistead RE — Product Roadmap

**Version:** 3.0
**Date:** February 13, 2026
**Vision:** The AI-powered transaction coordinator that prevents deals from falling apart.

---

## The Shift: From Filing Cabinet to Deal Protector

The original TTC vision was correct about the *what* — agents waste 8-15 hours per transaction on coordination. But the product was designed around **data storage** (upload contract, track milestones, log emails). That's a digital filing cabinet.

The reimagined Armistead RE is designed around **deal protection** — the single question every agent asks every morning:

> "What could go wrong today, and how do I prevent it?"

Everything in this roadmap flows from that question.

---

## Architecture Principles

1. **Proactive over passive.** The system tells you what to do, not the other way around.
2. **Multi-party by default.** Every feature considers all 8-12 parties on a transaction.
3. **AI as advisor, not just parser.** The AI doesn't just extract data — it watches for risk.
4. **Revenue-aware.** Agents think in dollars. The system speaks their language.
5. **Zero-friction adoption.** Party portals require no accounts. Templates eliminate setup time.

---

## Phase Overview

| Phase | Name | Focus | Timeline | Revenue Impact |
|-------|------|-------|----------|----------------|
| **1** | Today View | Smart dashboard + milestone templates | Weeks 1-3 | Makes agents open the app daily |
| **2** | Nudge Engine | Automated reminders + real email delivery | Weeks 4-6 | Prevents missed deadlines |
| **3** | Party Portal | Multi-party transparency + unique links | Weeks 7-9 | Eliminates "where are we?" emails |
| **4** | AI Advisor | Contextual AI recommendations + risk alerts | Weeks 10-12 | The "magic" that sells the product |
| **5** | Money | Commission tracking + pipeline forecasting | Weeks 13-14 | Agents check the app for revenue visibility |
| **6** | Doc Generation | Templates, repair letters, amendment forms | Weeks 15-17 | Saves 2+ hours per transaction |
| **7** | Brokerage Platform | Multi-agent teams, broker dashboard, compliance | Weeks 18-22 | 10x revenue: sell to offices, not individuals |

---

## Phase 1: Today View (Weeks 1-3)

**Goal:** Replace the stats-card dashboard with an intelligent daily action list that makes agents open the app every morning.

### What Changes

**Kill:** Dashboard with stat cards showing totals by status. No agent cares about "3 confirmed, 2 draft."

**Build:**
- **Today View** — a prioritized daily action list pulled from all active transactions
- **Milestone Templates** — auto-generate 12-20 milestones when a transaction is created, based on state + financing type + representation side
- **Smart Action Items** — system-generated tasks derived from milestone status, overdue items, and upcoming deadlines
- **Transaction Health Score** — red/yellow/green per transaction based on overdue milestones, missing parties, and missing documents

### New Backend

**Models:**
- `MilestoneTemplate` — state, financing_type, representation_side, milestone definitions with relative day offsets
- `ActionItem` — auto-generated or manual tasks linked to transactions, with priority, due_date, assigned_party_role
- Transaction gets `health_score` (computed), `days_to_close` (computed)

**Endpoints:**
- `GET /api/today` — returns prioritized action items across all transactions for the agent
- `GET /api/templates/milestones` — list available milestone templates
- `POST /api/transactions/{id}/apply-template` — apply a milestone template (auto-creates milestones with computed dates)
- `GET /api/transactions/{id}/health` — returns health score breakdown

**Services:**
- `TodayService` — aggregates overdue milestones, upcoming deadlines, missing documents, unsigned items across all transactions
- `TemplateService` — manages milestone templates, computes dates from contract execution date + closing date
- `HealthScoreService` — calculates per-transaction health based on: overdue milestones (heavy penalty), missing key parties, days to close vs milestones remaining

### New Frontend

- **TodayDashboard** replaces current Dashboard as the `/` route
  - Sections: 🔴 Overdue, 🟡 Due Today, 🟢 Coming Up (3 days), 📋 This Week
  - Each item links to the relevant transaction + tab
  - Quick-action buttons: "Mark Complete", "Send Reminder", "View Transaction"
- **Pipeline sidebar** — compact list of all active transactions with health indicators
- **Template picker** in NewTransaction flow — after creating transaction, choose template (e.g., "Georgia / Conventional / Buyer Side")

### Seed Data
- 3 milestone templates: GA Conventional Buyer, GA Conventional Seller, GA Cash Buyer
- Each template has 12-18 milestone definitions with day offsets
- Updated transactions with health-relevant data (some overdue, some on track)

---

## Phase 2: Nudge Engine (Weeks 4-6)

**Goal:** Wire up real email delivery and build an automated reminder system that keeps deals on track without the agent having to remember anything.

### What Changes

**Kill:** Stubbed `email_sender.py` that just logs. Communications table entries that go nowhere.

**Build:**
- **Real email delivery** via Resend (or SendGrid) with tracking (delivered, opened, clicked, bounced)
- **Automated milestone reminders** — Celery beat jobs that check upcoming deadlines and send reminders to responsible parties
- **Escalation chains** — if a milestone is overdue and no response, escalate to the agent, then to the broker
- **Email composer** — AI-generated emails with agent preview/approval before first-of-type sends
- **Notification preferences** — per-transaction and per-party email frequency controls

### New Backend

**Models:**
- `NotificationRule` — transaction_id, milestone_type, days_before, recipient_roles[], escalation_days, template_id
- `NotificationLog` — tracks every notification attempt, delivery status, escalation level
- `EmailDraft` — AI-generated email awaiting agent approval, linked to milestone + party

**Endpoints:**
- `POST /api/transactions/{id}/communications/send` — send an approved email
- `POST /api/transactions/{id}/communications/draft` — AI generates email draft for milestone
- `GET /api/notifications/pending` — list all pending notification drafts awaiting approval
- `PATCH /api/notifications/{id}/approve` — approve and send a notification
- `POST /api/webhooks/email` — receive delivery/open/click webhooks from email provider

**Services:**
- `EmailDeliveryService` — wraps Resend/SendGrid API, handles retries, tracks delivery
- `ReminderService` — Celery beat task that runs every hour, checks milestone deadlines, creates notification drafts or auto-sends based on rules
- `EscalationService` — checks overdue milestones with no action, escalates notification chain
- `EmailComposerAgent` — Claude-powered email draft generation with transaction context

**Celery Tasks:**
- `check_milestone_reminders` — runs hourly, scans all active transactions for upcoming/overdue milestones
- `send_pending_emails` — processes email queue with rate limiting
- `process_email_webhook` — handles delivery status updates

### New Frontend

- **Notification center** — bell icon in sidebar with pending count
- **Email preview/approve flow** — modal showing AI-generated email, agent can edit, approve, or reject
- **Milestone detail view** — shows all communications sent for that milestone
- **Settings: Notification preferences** — toggle email frequency, escalation rules per transaction

---

## Phase 3: Party Portal (Weeks 7-9)

**Goal:** Give every party on the transaction a read-only view of what's relevant to them — eliminating 70% of "where are we?" emails.

### What Changes

**Kill:** The paradigm where only the agent can see transaction status.

**Build:**
- **Unique portal links** — each party gets a unique, unguessable URL (no account required, like Calendly)
- **Role-based views** — each party sees only what's relevant to their role
- **Status updates** — parties can see milestone progress, upcoming deadlines, and their action items
- **Document access** — parties can view (not download) documents relevant to their role
- **Action buttons** — parties can mark their own tasks complete, upload requested documents
- **Real-time sync** — when a party uploads a document or marks something complete, the agent sees it immediately

### New Backend

**Models:**
- `PortalToken` — party_id, token (UUID), expires_at, is_active, last_accessed_at
- `PortalActivity` — party_id, action (viewed, uploaded, completed_task), metadata, created_at
- `PartyActionItem` — action items specifically assigned to external parties via portal

**Endpoints:**
- `POST /api/transactions/{id}/parties/{party_id}/portal` — generate portal link
- `GET /api/portal/{token}` — public endpoint, returns role-filtered transaction view
- `POST /api/portal/{token}/upload` — party uploads a document through portal
- `PATCH /api/portal/{token}/tasks/{task_id}` — party marks a task complete
- `GET /api/portal/{token}/activity` — activity log for the portal session

**Frontend:**
- **New route:** `/portal/:token` — standalone page (no sidebar, no auth required)
- **Portal view components** — simplified, branded view showing:
  - Transaction progress bar
  - "Your Action Items" section
  - Upcoming milestones relevant to their role
  - Documents they can view
  - Upload area for requested documents
- **Agent-side:** "Share Portal Link" button per party, copy-to-clipboard, send via email
- **Portal activity feed** on transaction detail — shows when parties view their portal or take actions

---

## Phase 4: AI Advisor (Weeks 10-12)

**Goal:** Evolve the AI from a one-time contract parser to an ongoing transaction advisor that watches for risk and suggests actions.

### What Changes

**Kill:** AI that runs once on contract upload and then goes silent.

**Build:**
- **Transaction Risk Monitor** — AI analyzes the state of each transaction daily and flags concerns
- **Contextual Suggestions** — when an agent views a transaction, AI provides relevant advice based on current state
- **Predictive Alerts** — "Based on current timeline, your financing contingency is at risk. The lender hasn't updated status in 8 days."
- **Smart Email Drafts** — AI writes contextually appropriate emails based on what's happening in the deal
- **Inspection Negotiation Assistant** — AI generates repair request letters from inspection findings
- **Closing Readiness Check** — AI audits all requirements and flags what's missing before closing

### New Backend

**Models:**
- `AIInsight` — transaction_id, type (risk_alert, suggestion, prediction), severity, message, context, dismissed_at
- `AIConversation` — transaction_id, messages[], model_used, created_at (for ongoing advisory context)

**Endpoints:**
- `GET /api/transactions/{id}/insights` — AI-generated insights for a transaction
- `POST /api/transactions/{id}/ask` — ask the AI advisor a question about the transaction
- `POST /api/transactions/{id}/closing-readiness` — run closing readiness audit
- `POST /api/transactions/{id}/generate-letter` — generate repair request or other letter from transaction data

**Agents:**
- `TransactionAdvisor` — daily Celery job that reviews all active transactions and generates insights
- `ClosingReadinessChecker` — audits: all milestones complete, all documents present, all parties confirmed, no overdue items
- `RepairLetterGenerator` — generates repair request letter from inspection items
- `SmartEmailComposer` — writes emails with full transaction context (not just templates)

### New Frontend

- **AI Insights panel** on transaction detail — shows active alerts and suggestions
- **"Ask AI" button** — opens chat-like interface for transaction-specific questions
- **Closing readiness dashboard** — checklist view showing what's done vs. what's needed
- **Letter generation UI** — select inspection items → generate repair letter → preview → send

---

## Phase 5: Money (Weeks 13-14)

**Goal:** Make agents open the app for revenue visibility, not just transaction management.

### What Changes

**Build:**
- **Commission tracking** per transaction — expected commission based on price and split
- **Pipeline dashboard** — total pipeline value, expected close this month/quarter, at-risk revenue
- **Commission forecasting** — projected monthly/quarterly income based on closing dates
- **Split management** — handle broker splits, referral fees, team splits
- **Revenue at risk** — flag deals with overdue milestones and their associated commission value

### New Backend

**Models:**
- `CommissionConfig` — agent_id, default_rate, broker_split, team_split
- `TransactionCommission` — transaction_id, gross_commission, agent_split, broker_split, referral_fee, net_commission, status (projected, pending, paid)

**Endpoints:**
- `GET /api/pipeline` — pipeline value, monthly forecast, at-risk revenue
- `GET /api/commissions` — list all commission records
- `PATCH /api/transactions/{id}/commission` — set/update commission details

### New Frontend

- **Pipeline page** — replaces or augments the old dashboard stats
- **Commission column** on transaction table
- **Revenue forecast chart** — bar chart showing projected closes by month
- **At-risk revenue widget** — transactions with overdue milestones and their $ value

---

## Phase 6: Document Generation (Weeks 15-17)

**Goal:** Generate documents from transaction data, not just store them.

### What Changes

**Build:**
- **Template engine** — Jinja2 or similar for generating PDFs from transaction data
- **Repair request letter** — auto-generated from inspection items (buyer selects which items)
- **Amendment forms** — pre-filled from transaction data when price or date changes
- **Status update emails** — auto-generated milestone summary emails to all parties
- **Closing prep checklist** — generated document listing everything needed for closing
- **Post-closing summary** — complete transaction summary for agent records

### New Backend

**Models:**
- `DocumentTemplate` — name, type, template_content (Jinja2), state, representation_side
- `GeneratedDocument` — transaction_id, template_id, content, pdf_url, created_at

**Services:**
- `DocumentGenerator` — renders templates with transaction data, converts to PDF
- `RepairLetterService` — selects inspection items, generates formatted letter
- `ClosingPrepService` — audits transaction, generates closing checklist

---

## Phase 7: Brokerage Platform (Weeks 18-22)

**Goal:** 10x revenue by selling to brokerages instead of individual agents.

### What Changes

**Build:**
- **Multi-agent support** — broker invites agents, agents see only their transactions
- **Broker dashboard** — overview of all agents' transactions, compliance status, revenue
- **Compliance monitoring** — are required communications being sent? Are deadlines being met?
- **Agent performance metrics** — average days-to-close, deals closed, revenue generated
- **Team management** — assign transactions to agents, transfer between agents
- **Brokerage branding** — custom logo, colors, email templates per brokerage
- **Role-based access** — broker, managing broker, agent, assistant, transaction coordinator

### New Backend

**Models:**
- `Brokerage` — name, logo_url, primary_color, settings
- `BrokerageAgent` — brokerage_id, user_id, role (broker, agent, tc, assistant), is_active
- `ComplianceRule` — brokerage_id, rule_type, description, check_function
- `ComplianceCheck` — transaction_id, rule_id, status (pass, fail, warning), checked_at

**Endpoints:**
- `GET /api/brokerage/dashboard` — broker-level stats across all agents
- `GET /api/brokerage/agents` — list agents with performance metrics
- `GET /api/brokerage/compliance` — compliance report across all transactions
- `POST /api/brokerage/agents/invite` — invite agent to brokerage

---

## Data Model Evolution

### New Tables (Cumulative)

```
Phase 1:
  milestone_templates        — state/financing/side → milestone definitions
  milestone_template_items   — individual milestone definitions with day offsets
  action_items              — auto-generated + manual tasks per transaction

Phase 2:
  notification_rules        — when/who to notify per milestone type
  notification_log          — delivery tracking per notification
  email_drafts              — AI-generated emails awaiting approval

Phase 3:
  portal_tokens             — unique access tokens for party portals
  portal_activity           — audit log of portal access and actions
  party_action_items        — tasks assigned to external parties

Phase 4:
  ai_insights               — AI-generated risk alerts and suggestions
  ai_conversations          — advisory chat history per transaction

Phase 5:
  commission_configs        — agent commission rate + split settings
  transaction_commissions   — per-deal commission tracking

Phase 6:
  document_templates        — Jinja2 templates for doc generation
  generated_documents       — rendered documents with PDF storage

Phase 7:
  brokerages               — brokerage company records
  brokerage_agents         — agent-brokerage membership + roles
  compliance_rules         — brokerage-specific compliance rules
  compliance_checks        — per-transaction compliance audit results
```

### Existing Table Modifications

```
transactions:
  + health_score          FLOAT          — computed 0-100 score
  + contract_execution_date  TIMESTAMP   — when contract was signed (for milestone date calc)
  + days_to_close         INTEGER        — computed from closing_date
  + state_code            VARCHAR(2)     — state for template selection (rename property_state)

users:
  + brokerage_id          UUID FK        — Phase 7
  + default_commission_rate DECIMAL      — Phase 5
  + notification_preferences JSONB       — Phase 2
  + ai_preferences        JSONB          — Phase 4

milestones:
  + template_item_id      UUID FK        — link back to template that created it
  + reminder_sent_count   INTEGER        — how many reminders sent
  + escalation_level      INTEGER        — current escalation level

parties:
  + portal_token_id       UUID FK        — active portal token
  + last_portal_access    TIMESTAMP      — when they last viewed portal
  + notification_preference VARCHAR      — email frequency preference
```

---

## Frontend Route Evolution

```
Current:
  /                        → Dashboard (stats cards)
  /new                     → NewTransaction
  /transaction/:id         → TransactionDetail (7 tabs)
  /parties                 → Global party list
  /settings                → Settings (stub)

Phase 1:
  /                        → TodayView (action items)
  /pipeline                → Pipeline (moved from /)
  /new                     → NewTransaction + template picker

Phase 2:
  /notifications           → Notification center
  /settings/notifications  → Notification preferences

Phase 3:
  /portal/:token           → Public party portal (no auth)

Phase 4:
  (adds AI panels to existing transaction detail)

Phase 5:
  /pipeline                → Enhanced with commission data
  /commissions             → Commission tracking page

Phase 7:
  /brokerage               → Broker dashboard
  /brokerage/agents        → Agent management
  /brokerage/compliance    → Compliance monitoring
```

---

## Success Metrics (Reimagined)

| Metric | Current | Phase 1 Target | Phase 7 Target |
|--------|---------|---------------|----------------|
| Agent daily opens | 0 (no users yet) | 1x/day (Today View) | 3x/day |
| "Where are we?" emails | N/A | -30% (Today View) | -70% (Party Portal) |
| Missed deadlines | N/A | -50% (Templates) | -90% (Nudge Engine) |
| Time per transaction | 8-15 hours | 4-6 hours | 1-2 hours |
| Agent NPS | N/A | 40+ | 70+ |
| Revenue per customer | $0 | $39/mo (agent) | $500-2000/mo (brokerage) |
| Deals per agent | 5-10 concurrent | 15-20 concurrent | 25-30 concurrent |

---

*This roadmap is a living document. Each phase has its own detailed specification.*
