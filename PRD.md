# Armistead RE — Product Requirements Document

**Version:** 3.0
**Date:** February 13, 2026
**Author:** Tyler Pettis
**Status:** Active Development
**Roadmap:** See ROADMAP.md for phase-by-phase implementation plan

---

## 1. Product Vision

Armistead RE is an AI-powered real estate transaction platform that **prevents deals from falling apart.** It doesn't just track milestones after the fact — it predicts what could go wrong, nudges the right people at the right time, and gives every party on the transaction exactly the visibility they need.

**One-Line Pitch:** The AI transaction coordinator that keeps your deals alive.

**Core Thesis:** Every deal that falls apart does so because someone missed a deadline, a lender didn't get docs on time, or communication broke down between parties. Armistead RE eliminates those failure points through proactive monitoring, automated nudging, and multi-party transparency.

---

## 2. Problem Statement

Real estate agents spend 8-15 hours per transaction on coordination — not because the tasks are hard, but because **nobody is watching.** Milestones slip because there's no system holding parties accountable. Agents become human reminder systems, sending the same "checking in" emails to lenders and attorneys across 15-30 concurrent transactions.

**The real problems (from 20+ years of brokerage experience):**

| Problem | Impact | Frequency |
|---------|--------|-----------|
| "Where are we?" emails from all parties | 2-3 hours/week wasted | Every transaction |
| Lender goes silent for 7+ days | Closing delayed, deal at risk | 40% of financed deals |
| Attorney sits on title work | Closing delayed | 25% of transactions |
| Inspection report not reviewed fast enough | Contingency deadline missed | 15% of transactions |
| Agent forgets to send follow-up | Communication gap, party frustration | 30% of milestones |
| No visibility into what other parties are doing | Agent is the information bottleneck | Every transaction |
| Tracking 15+ milestones across 20+ deals on spreadsheets | Deadlines slip through cracks | Every agent |

**The insight:** The winning product doesn't store information better — it **prevents failures** by watching all transactions simultaneously and taking action before things go wrong.

---

## 3. Target Users

### 3.1 Primary User: Real Estate Agent (Phase 1-6)
- Manages 5-30+ active transactions simultaneously
- Currently tracks deadlines on spreadsheets, sticky notes, or memory
- Opens their phone 50+ times/day — needs a "what do I do NOW?" answer
- Not technical, but uses smartphone apps fluently
- **Key metric they care about:** How many deals can I close this month without dropping any?

### 3.2 Secondary User: Transaction Parties (Phase 3)
- Buyers, sellers, lenders, attorneys, inspectors, title companies
- Need to see "what's happening with MY deal" without calling the agent
- Will NOT create an account — must work with a simple link
- Most will access from mobile devices
- **Key metric they care about:** What do I need to do, and by when?

### 3.3 Tertiary User: Broker/Team Lead (Phase 7)
- Oversees 5-50+ agents
- Needs visibility into all active transactions across the brokerage
- Cares about compliance (are required disclosures being sent?)
- Cares about revenue (what's our pipeline? what's at risk?)
- **Key metric they care about:** Are my agents compliant and productive?

---

## 4. Scope

### 4.1 Platform Capabilities (Across All Phases)

| Capability | Phase | Description |
|-----------|-------|-------------|
| Contract Upload & AI Parsing | Built | Upload PDF, AI extracts data with confidence scores |
| Transaction CRUD | Built | Create, edit, delete transactions with full party/milestone management |
| Milestone Management | Built | Manual CRUD with timeline visualization |
| Document Storage | Built | Upload/download via MinIO S3-compatible storage |
| Inspection Analysis | Built | AI-parsed inspection reports with severity/cost ranking |
| Amendment Tracking | Built | Full audit trail of all changes |
| **Today View + Smart Actions** | **Phase 1** | Prioritized daily action list across all transactions |
| **Milestone Templates** | **Phase 1** | Auto-generate milestones by state/financing/side |
| **Transaction Health Score** | **Phase 1** | Red/yellow/green scoring per transaction |
| **Automated Nudging** | **Phase 2** | Email reminders with escalation chains |
| **Real Email Delivery** | **Phase 2** | Resend integration with tracking |
| **AI Email Composer** | **Phase 2** | Claude generates contextual emails |
| **Party Portal** | **Phase 3** | Unique links for every party (no account required) |
| **Role-Based Views** | **Phase 3** | Each party sees only what's relevant to them |
| **AI Transaction Advisor** | **Phase 4** | Daily risk monitoring, contextual suggestions, closing readiness |
| **"Ask AI" Chat** | **Phase 4** | Per-transaction AI chat for questions and letter generation |
| **Commission Tracking** | **Phase 5** | Per-transaction commission with splits and forecasting |
| **Pipeline Intelligence** | **Phase 5** | Revenue forecasting, at-risk revenue alerts |
| **Document Generation** | **Phase 6** | Repair letters, amendment forms, closing checklists from templates |
| **Brokerage Dashboard** | **Phase 7** | Multi-agent oversight, compliance monitoring |
| **Team Management** | **Phase 7** | Agent roles, transaction assignment, performance metrics |

### 4.2 Out of Scope (All Versions)
- Commercial real estate transactions
- MLS data integration (future API partnership)
- DocuSign/Dotloop integration (future)
- SMS notifications (future — email first)
- Native mobile app (responsive web first)
- Post-closing follow-up campaigns (future CRM expansion)
- Accounting/bookkeeping integration (future)

---

## 5. Functional Requirements

### FR-1: Contract Upload & Parsing (Built)

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-1.1 | Accept PDF uploads of executed purchase agreements | P0 | ✅ Built |
| FR-1.2 | AI extracts: address, price, earnest money, financing type, parties, dates, stipulations | P0 | ✅ Built |
| FR-1.3 | Confidence scores (0-1) per extracted field | P0 | ✅ Built |
| FR-1.4 | Agent reviews and confirms extracted data | P0 | ✅ Built |
| FR-1.5 | Detect/select representation side (buyer/seller/dual) | P0 | ✅ Built |
| FR-1.6 | Handle multiple buyers/sellers | P0 | ✅ Built |
| FR-1.7 | Cash transactions adjust workflows (no lender, no appraisal) | P0 | ⬜ Phase 1 |
| FR-1.8 | Vision fallback for scanned/image PDFs | P1 | ✅ Built |
| FR-1.9 | Store original document in MinIO | P0 | ✅ Built |

### FR-2: Today View & Smart Actions (Phase 1)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | Prioritized daily action list across all active transactions | P0 |
| FR-2.2 | Sections: Overdue, Due Today, Coming Up (3 days), This Week | P0 |
| FR-2.3 | Quick actions: Mark Complete, Send Reminder, View Transaction | P0 |
| FR-2.4 | Pipeline sidebar showing all active transactions with health dots | P0 |
| FR-2.5 | Filter actions by transaction, milestone type, or priority | P1 |
| FR-2.6 | Snooze and dismiss actions | P1 |

### FR-3: Milestone Templates (Phase 1)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | Auto-generate milestones from template on transaction creation | P0 |
| FR-3.2 | Templates vary by state, financing type, and representation side | P0 |
| FR-3.3 | Cash transactions skip financing/appraisal milestones automatically | P0 |
| FR-3.4 | Day offsets computed from contract execution date or closing date | P0 |
| FR-3.5 | Closing date change cascades to all dependent milestones | P0 |
| FR-3.6 | Agents can customize templates or create their own | P1 |
| FR-3.7 | Ship with 7+ templates covering GA and AL | P0 |

### FR-4: Transaction Health Score (Phase 1)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | 0-100 score per transaction based on milestone status, party completeness, document presence | P0 |
| FR-4.2 | Red (0-40), Yellow (41-70), Green (71-100) color coding | P0 |
| FR-4.3 | Score breakdown visible on transaction detail | P1 |
| FR-4.4 | Score updates when milestones change status | P0 |

### FR-5: Automated Nudging (Phase 2)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Automated reminder emails before milestone deadlines (configurable days) | P0 |
| FR-5.2 | Overdue notifications to responsible party + agent | P0 |
| FR-5.3 | Escalation chain: reminder → follow-up → urgent notice → critical alert | P0 |
| FR-5.4 | Agent approval modes: Preview All, Auto-send Reminders, Full Auto | P0 |
| FR-5.5 | Real email delivery via Resend with delivery/open/click tracking | P0 |
| FR-5.6 | Notification preferences per-agent and per-party | P1 |
| FR-5.7 | AI-composed emails with agent preview/edit | P0 |
| FR-5.8 | CAN-SPAM compliant: unsubscribe links, proper sender ID | P0 |

### FR-6: Party Portal (Phase 3)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-6.1 | Unique UUID portal link per party (no account required) | P0 |
| FR-6.2 | Role-based views: each party sees only what's relevant | P0 |
| FR-6.3 | Transaction progress bar | P0 |
| FR-6.4 | Party-specific action items with mark-complete capability | P0 |
| FR-6.5 | Document upload through portal (requested docs only) | P0 |
| FR-6.6 | Document viewing (not download) for shared documents | P1 |
| FR-6.7 | Agent can regenerate/revoke portal tokens | P0 |
| FR-6.8 | Portal activity feed visible to agent | P0 |
| FR-6.9 | Mobile-first, clean design, no auth required | P0 |

### FR-7: AI Transaction Advisor (Phase 4)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-7.1 | Daily AI analysis of all active transactions for risk alerts | P0 |
| FR-7.2 | Contextual suggestions when agent views a transaction | P0 |
| FR-7.3 | Closing readiness audit (checklist of what's done vs needed) | P0 |
| FR-7.4 | Per-transaction "Ask AI" chat with full context | P0 |
| FR-7.5 | Smart email composition with transaction awareness | P0 |
| FR-7.6 | Repair letter generation from inspection items | P0 |
| FR-7.7 | Insights auto-dismiss when resolved | P1 |
| FR-7.8 | Agent can dismiss/acknowledge insights | P0 |

### FR-8: Commission & Pipeline (Phase 5)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-8.1 | Per-transaction commission tracking (gross, splits, net) | P0 |
| FR-8.2 | Pipeline dashboard with total value and monthly forecast | P0 |
| FR-8.3 | Revenue at risk (overdue deals × commission value) | P0 |
| FR-8.4 | Commission configuration (default rate, broker split, team splits) | P0 |
| FR-8.5 | Projected vs actual commission tracking | P1 |

### FR-9: Document Generation (Phase 6)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-9.1 | Template-based document generation (Jinja2 → PDF) | P0 |
| FR-9.2 | Repair request letter from selected inspection items | P0 |
| FR-9.3 | Transaction status summary for all parties | P0 |
| FR-9.4 | Closing preparation checklist | P0 |
| FR-9.5 | Agent preview and edit before finalizing | P0 |
| FR-9.6 | Generated documents stored alongside uploaded documents | P0 |

### FR-10: Brokerage Platform (Phase 7)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10.1 | Brokerage entity with branding and settings | P0 |
| FR-10.2 | Agent invitation and role management | P0 |
| FR-10.3 | Broker dashboard: all agents, transactions, compliance | P0 |
| FR-10.4 | Compliance rules engine (configurable per brokerage) | P0 |
| FR-10.5 | Agent performance metrics | P1 |
| FR-10.6 | Transaction assignment and transfer between agents | P0 |
| FR-10.7 | Role-based access: broker, agent, TC, assistant | P0 |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target | Phase |
|----|-------------|--------|-------|
| NFR-1 | Contract parsing time | < 30 seconds | Built |
| NFR-2 | Today View load time (30+ transactions) | < 2 seconds | Phase 1 |
| NFR-3 | Health score computation | < 500ms per transaction | Phase 1 |
| NFR-4 | Email delivery time (after approval) | < 5 seconds | Phase 2 |
| NFR-5 | Reminder check frequency | Every hour | Phase 2 |
| NFR-6 | Portal page load time | < 1.5 seconds | Phase 3 |
| NFR-7 | AI insight generation (per transaction) | < 10 seconds | Phase 4 |
| NFR-8 | "Ask AI" response time | < 8 seconds | Phase 4 |
| NFR-9 | System uptime | 99.5%+ | All phases |
| NFR-10 | Concurrent transactions per agent | 100+ | All phases |
| NFR-11 | Mobile-responsive design | All pages | Phase 1+ |
| NFR-12 | Portal works without account | Zero-friction access | Phase 3 |
| NFR-13 | Email delivery rate | 98%+ | Phase 2 |
| NFR-14 | Portal token security | UUID v4, unguessable | Phase 3 |

---

## 7. Technical Architecture

### 7.1 System Diagram (Reimagined)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + TypeScript + Tailwind)          │
│                                                                     │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ Today    │ │Transaction│ │ Pipeline │ │ Portal   │ │Brokerage│  │
│  │  View    │ │  Detail   │ │  + $$$   │ │  (public)│ │Dashboard│  │
│  └──────────┘ └───────────┘ └──────────┘ └──────────┘ └────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────────┐
│                    BACKEND (Python / FastAPI)                        │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    API Layer (FastAPI)                         │  │
│  │  Auth │ Rate Limiting │ Validation │ Portal Auth (token)      │  │
│  └────────────────────────────┬──────────────────────────────────┘  │
│                               │                                     │
│  ┌──────────┐ ┌──────────┐ ┌─▼────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Today    │ │ Template │ │ Nudge    │ │ Portal   │ │ Revenue │  │
│  │ Service  │ │ Service  │ │ Engine   │ │ Service  │ │ Service │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └─────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                AI Agent Layer (Claude API)                     │  │
│  │                                                               │  │
│  │  ContractParser │ TransactionAdvisor │ EmailComposer          │  │
│  │  InspectionAnalyzer │ ClosingReadiness │ ChatAdvisor          │  │
│  │  RepairLetterGenerator │ DocumentGenerator                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │             Background Jobs (Celery + Redis)                  │  │
│  │                                                               │  │
│  │  MilestoneReminders │ EscalationChecker │ HealthScoreUpdater  │  │
│  │  DailyAIAnalysis │ EmailDeliveryQueue │ DigestGenerator       │  │
│  └───────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                         DATA LAYER                                   │
│                                                                      │
│  ┌──────────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ PostgreSQL   │  │  Redis   │  │  MinIO / S3  │  │  Resend     │  │
│  │ (all data,   │  │  (cache, │  │  (documents, │  │  (email     │  │
│  │  templates,  │  │  queues, │  │  contracts,  │  │  delivery,  │  │
│  │  audit logs) │  │  Celery) │  │  generated)  │  │  tracking)  │  │
│  └──────────────┘  └──────────┘  └─────────────┘  └─────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 Tech Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Frontend | React + TypeScript | 18+ / 5+ | Component architecture, type safety |
| Styling | Tailwind CSS | 3+ | Rapid, consistent styling |
| Data Fetching | TanStack React Query | 5+ | Cache, refetch, optimistic updates |
| State | Zustand | 4+ | Lightweight global state |
| Icons | Lucide React | 0.460+ | Comprehensive, tree-shakeable |
| Validation | Zod | 3+ | Runtime type validation |
| Backend | FastAPI (Python) | 0.100+ | Async-first, auto-docs, Pydantic |
| ORM | SQLAlchemy | 2.0+ | Async support, relationships |
| Migrations | Alembic | Latest | Schema versioning |
| Database | PostgreSQL | 16+ | Relational, JSON support |
| Cache/Queue | Redis | 7+ | Celery backend, caching |
| Job Queue | Celery | 5+ | Scheduled tasks, email queue |
| AI | Claude API (Anthropic) | Sonnet 4 | Document parsing, advisory, composition |
| Storage | MinIO (dev) / AWS S3 (prod) | Latest | Object storage for documents |
| Email | Resend | Latest | Modern API, webhooks, tracking |
| Auth | Clerk | 5+ | Managed auth with RBAC |
| PDF Processing | PyMuPDF | Latest | Text + image extraction |
| PDF Generation | WeasyPrint | Latest | HTML → PDF for doc generation |
| Containers | Docker + Compose | Latest | Dev/prod parity |

---

## 8. Data Model

### Core Tables (Built)
- `users` — Agent accounts with brokerage info
- `transactions` — Core transaction records
- `parties` — All people involved in transactions
- `milestones` — Transaction timeline and deadlines
- `communications` — Email tracking
- `amendments` — Change audit trail
- `files` — Uploaded documents
- `inspection_analyses` + `inspection_items` — Inspection report data
- `email_templates` — Customizable email templates

### New Tables (By Phase)

See ROADMAP.md § Data Model Evolution for complete table definitions across all phases.

**Phase 1:** milestone_templates, milestone_template_items, action_items
**Phase 2:** notification_rules, notification_log, email_drafts
**Phase 3:** portal_tokens, portal_activity, party_action_items
**Phase 4:** ai_insights, ai_conversations
**Phase 5:** commission_configs, transaction_commissions
**Phase 6:** document_templates, generated_documents
**Phase 7:** brokerages, brokerage_agents, compliance_rules, compliance_checks

---

## 9. Email Communication Matrix

(Preserved from v2.0 — see sections 8.1-8.4 of previous PRD version for full email matrices)

### Key Principle Change (v3.0)

In v2.0, emails were "fire and forget" — the system sends, the agent hopes they land.

In v3.0, emails are part of the **nudge engine**:
1. System generates contextual email draft
2. Agent previews and approves (or auto-sends based on preferences)
3. Email delivers via Resend with tracking
4. System monitors: delivered? opened? clicked? bounced?
5. If no response after configurable period → escalate
6. All email activity visible to agent AND to relevant parties via portal

---

## 10. Milestone Definitions

(Preserved from v2.0 — see section 9 for full milestone tables)

### Key Principle Change (v3.0)

In v2.0, milestones were manually created by the agent.

In v3.0, milestones are **auto-generated from templates** and **actively monitored**:
1. Agent creates transaction and selects state/financing/side
2. System applies matching template → 12-20 milestones auto-created with computed dates
3. Agent adjusts any dates as needed
4. System monitors all milestones continuously
5. Approaching deadlines trigger automated reminders
6. Overdue milestones trigger escalation chains
7. Completed milestones trigger "next steps" communications

---

## 11. Security & Compliance

(Preserved from v2.0 — see section 11)

### Additional Security (v3.0)

| Requirement | Phase | Implementation |
|-------------|-------|---------------|
| Portal token security | Phase 3 | UUID v4, HTTPS only, no PII in URL |
| Portal access logging | Phase 3 | All portal views logged with IP + timestamp |
| Portal token revocation | Phase 3 | Agent can revoke immediately |
| AI data handling | Phase 4 | PII anonymized before sending to Claude API where possible |
| Brokerage data isolation | Phase 7 | Row-level security in PostgreSQL |
| Audit trail for broker access | Phase 7 | All broker views of agent data logged |

---

## 12. Success Metrics (Reimagined)

| Metric | Target | Phase | Measurement |
|--------|--------|-------|-------------|
| Agent opens app daily | 1x/day minimum | Phase 1 | Analytics |
| "Where are we?" emails reduced | -30% | Phase 1, -70% Phase 3 | Agent survey |
| Missed deadlines reduced | -50% Phase 1, -90% Phase 2 | Phase 1-2 | Overdue milestone tracking |
| Agent time per transaction | 4-6 hours (from 8-15) | Phase 2 | Agent survey |
| AI extraction accuracy | >90% fields correct | Built | Confidence score data |
| Email delivery rate | >98% | Phase 2 | Resend tracking |
| Portal adoption (parties using links) | >60% of parties | Phase 3 | Portal access logs |
| AI insight usefulness | >70% not dismissed | Phase 4 | Dismiss rate tracking |
| Commission forecast accuracy | Within 10% of actual | Phase 5 | Projected vs actual comparison |
| Deals per agent (capacity) | 20-30 concurrent | Phase 2+ | Transaction count |
| Agent NPS | 40+ Phase 1, 70+ Phase 7 | All phases | NPS survey |
| Brokerage revenue per customer | $500-2000/month | Phase 7 | Billing data |

---

## 13. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation | Phase |
|------|--------|-----------|------------|-------|
| AI misparses contract data | High | Medium | Mandatory human review + confidence scores | Built |
| Milestone template dates wrong | Medium | Medium | Agent confirms all dates, can edit any milestone | Phase 1 |
| Notification fatigue | Medium | High | Configurable frequency, digest mode, snooze | Phase 2 |
| Email deliverability issues | Medium | Low | SPF/DKIM/DMARC, Resend reputation, fallback queue | Phase 2 |
| Portal token leaked/shared | Medium | Low | UUID v4 unguessable, revocation capability, access logging | Phase 3 |
| AI advisor gives wrong advice | High | Medium | All AI suggestions are advisory only, agent always decides | Phase 4 |
| AI cost overruns at scale | Medium | Low | Haiku for routine, Sonnet for complex, per-transaction cost tracking | Phase 4 |
| Commission data privacy | Medium | Medium | Agent-only visibility, brokerage isolation in Phase 7 | Phase 5 |
| State-specific compliance gaps | High | Medium | Legal review per state, configurable rules, broker oversight | Phase 7 |
| Agent adoption resistance | Medium | Medium | Today View delivers immediate value, no training required | Phase 1 |

---

## 14. Competitive Landscape

| Competitor | Strength | Weakness | Our Edge |
|-----------|----------|----------|----------|
| Dotloop (Zillow) | Good forms, large market | Weak workflow, no AI | AI advisor, proactive nudging |
| SkySlope | Strong compliance | Dated UI (2008 era) | Modern UX, Today View, party portal |
| Lone Wolf / TransactionDesk | Market leader | Agents hate the UX | 10x better UX, AI-first |
| Brokermint | Commission focus | Light on transaction mgmt | Full lifecycle: transaction + commission |
| Open to Close | Closest competitor | No AI, no party portal | AI contract parsing, AI advisor, party portal |
| Spreadsheets | Free, flexible | No automation, no tracking | Everything automated |

**Our unfair advantages:**
1. **AI-native** — not bolted on, built in from day one
2. **Party portal** — nobody does multi-party transparency well
3. **Proactive nudging** — the system works even when the agent forgets
4. **Modern UX** — agents actually want to open this app

---

*End of PRD — See ROADMAP.md for implementation phases and phase-specific specifications in /phases/ directory.*
