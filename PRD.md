# Transaction-to-Close (TTC) — Product Requirements Document

**Version:** 2.0  
**Date:** February 12, 2026  
**Author:** Tyler Pettis  
**Status:** Draft  
**CoV Status:** Verified (see memory/COV_00_project_scope.md)

---

## 1. Product Vision

Transaction-to-Close (TTC) is an AI-powered real estate transaction coordinator that manages every step from executed contract to closing day. It eliminates the manual overhead of transaction coordination by using AI agents to parse contracts, generate communications, track milestones, analyze inspection reports, and keep all parties informed — automatically.

**One-Line Pitch:** Upload your executed contract. TTC handles the rest.

---

## 2. Problem Statement

Real estate agents spend 8-15 hours per transaction on coordination tasks: manually reading contracts, typing emails to 4-6 parties, tracking deadlines on spreadsheets, following up when milestones are missed, and scrambling before closing. This administrative burden limits the number of transactions an agent can manage simultaneously, leads to missed deadlines, and creates communication gaps between parties.

**Current Pain Points:**
- Manually extracting party info and dates from contracts
- Writing 4-6 individualized emails per transaction at intake
- Tracking 10+ milestones across multiple transactions simultaneously
- Remembering to send follow-up emails at each phase transition
- Reading 40+ page inspection reports and summarizing findings
- Coordinating between buyer, seller, lender, attorney, and agents
- Different workflows depending on buyer vs. seller representation

---

## 3. Target Users

### 3.1 Primary User: Real Estate Agent
- Manages 5-30+ active transactions at any time
- Currently uses spreadsheets, CRMs, or manual methods to track transactions
- Wants to spend more time on client relationships and less on admin
- Tech-comfortable but not a developer

### 3.2 Secondary User: Team Lead / Broker
- Oversees multiple agents
- Needs visibility into all active transactions
- Wants compliance assurance (required communications sent, deadlines met)

### 3.3 Tertiary User (Future): Clients
- Buyers and sellers who want visibility into their transaction status
- Would access a read-only portal (Phase 6+ / post-launch)

---

## 4. Scope

### 4.1 In Scope (V1)
- Residential purchase agreement parsing (standard state contracts)
- Buyer-side, seller-side, and dual-agency workflows
- Automated email generation and delivery to all parties
- Milestone tracking with automated reminders
- Home inspection report analysis with severity/cost ranking
- Follow-up email orchestration through closing
- Single-agent use (one agent per account)
- Initial state support: Alabama (expand post-launch)

### 4.2 Out of Scope (V1)
- Client-facing portal
- Commercial or non-standard contract types (lease-option, land contract, new construction)
- MLS integration
- DocuSign/Dotloop auto-ingestion
- SMS notifications
- Mobile app
- Multi-agent brokerage dashboard
- Post-closing follow-up campaigns

---

## 5. Functional Requirements

### FR-1: Contract Upload & Parsing

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | System accepts PDF and image uploads of executed purchase agreements | P0 |
| FR-1.2 | AI agent extracts: property address, purchase price, earnest money amount, financing type, all party names/contacts, all contingency dates, special stipulations | P0 |
| FR-1.3 | AI provides confidence scores (0-1) per extracted field | P0 |
| FR-1.4 | Agent can review, edit, and confirm all extracted data before proceeding | P0 |
| FR-1.5 | System detects representation side (buyer/seller/dual) or prompts agent to select | P0 |
| FR-1.6 | System handles multiple buyers or sellers (e.g., married couple, trust) | P0 |
| FR-1.7 | System identifies cash transactions and adjusts workflows (no lender, no appraisal) | P0 |
| FR-1.8 | System flags non-standard or unrecognizable contracts for manual entry | P1 |
| FR-1.9 | System stores original document in secure cloud storage | P0 |

### FR-2: Email Orchestration

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | System generates role-specific emails for all parties based on representation side | P0 |
| FR-2.2 | Agent previews all emails before sending | P0 |
| FR-2.3 | Agent can edit AI-generated emails before sending | P0 |
| FR-2.4 | System attaches executed contract to lender and attorney emails | P0 |
| FR-2.5 | Emails include proper brokerage disclaimers and agent contact info | P0 |
| FR-2.6 | System tracks email delivery, opens, and clicks | P1 |
| FR-2.7 | Emails handle multi-party naming correctly (e.g., "Dear John and Jane Smith") | P0 |
| FR-2.8 | Dual agency workflow sends appropriate combined communications | P0 |
| FR-2.9 | Cash transaction workflow skips lender communications | P0 |

### FR-3: Milestone Tracking & Scheduling

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | System auto-generates milestones from contract dates | P0 |
| FR-3.2 | Milestones conditional on financing type (no appraisal for cash) | P0 |
| FR-3.3 | System sends reminder emails to relevant parties before milestone deadlines | P0 |
| FR-3.4 | Agent can manually add, edit, or remove milestones | P0 |
| FR-3.5 | Agent can mark milestones as completed, waived, or rescheduled | P0 |
| FR-3.6 | System sends follow-up emails when milestones are completed, updating all parties on next steps | P0 |
| FR-3.7 | Dashboard shows timeline view of all milestones per transaction | P1 |
| FR-3.8 | System handles closing date extensions (update all downstream milestones) | P1 |
| FR-3.9 | Agent receives in-app notifications for upcoming milestones | P1 |

### FR-4: Inspection Report Analysis

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | System accepts PDF upload of home inspection reports | P0 |
| FR-4.2 | AI extracts all findings and categorizes by severity (critical, major, moderate, minor, cosmetic) | P0 |
| FR-4.3 | Each finding includes estimated repair cost range | P0 |
| FR-4.4 | Findings ranked from most to least important from a risk standpoint | P0 |
| FR-4.5 | System generates executive summary with total cost range and top concerns | P0 |
| FR-4.6 | Agent can share formatted analysis with client | P1 |
| FR-4.7 | System tracks repair request status (requested, countered, agreed, denied) | P1 |

### FR-5: Transaction Amendments

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | Agent can update key transaction fields (price, closing date, parties) | P0 |
| FR-5.2 | System logs all changes with timestamps | P0 |
| FR-5.3 | When key fields change, system triggers update emails to relevant parties | P1 |
| FR-5.4 | Amendment history visible on transaction detail view | P1 |

---

## 6. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-1 | Contract parsing completes in under 30 seconds | P0 |
| NFR-2 | Email generation (all parties) completes in under 15 seconds | P0 |
| NFR-3 | Inspection analysis completes in under 60 seconds | P0 |
| NFR-4 | System uptime 99.5%+ | P0 |
| NFR-5 | All data encrypted at rest (AES-256) and in transit (TLS 1.3) | P0 |
| NFR-6 | PII field-level encryption in database | P0 |
| NFR-7 | Role-based access control | P0 |
| NFR-8 | Concurrent support for 100+ active transactions per agent | P1 |
| NFR-9 | Page load times under 2 seconds | P1 |
| NFR-10 | Mobile-responsive design | P1 |

---

## 7. Technical Architecture

### 7.1 System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + TypeScript)             │
│                                                              │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐   │
│  │Dashboard │ │Transaction│ │ Email    │ │  Inspection  │   │
│  │  (list)  │ │  Detail   │ │ Preview  │ │   Analysis   │   │
│  └──────────┘ └───────────┘ └──────────┘ └──────────────┘   │
└──────────────────────────┬───────────────────────────────────┘
                           │ REST API + WebSocket (live updates)
┌──────────────────────────▼───────────────────────────────────┐
│                   BACKEND (Python / FastAPI)                   │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    API Layer (FastAPI)                   │  │
│  │  Auth Middleware │ Rate Limiting │ Request Validation    │  │
│  └─────────────────────────┬───────────────────────────────┘  │
│                            │                                  │
│  ┌─────────────┐ ┌────────▼────────┐ ┌────────────────────┐  │
│  │ Transaction  │ │  Communication  │ │    Milestone       │  │
│  │   Service    │ │    Service      │ │    Service         │  │
│  └──────┬──────┘ └────────┬────────┘ └────────┬───────────┘  │
│         │                 │                    │              │
│  ┌──────▼──────┐ ┌────────▼────────┐ ┌────────▼───────────┐  │
│  │ Inspection  │ │   Amendment     │ │   Notification     │  │
│  │  Service    │ │   Service       │ │   Service          │  │
│  └──────┬──────┘ └─────────────────┘ └────────────────────┘  │
│         │                                                     │
│  ┌──────▼──────────────────────────────────────────────────┐  │
│  │              AI Agent Layer (Claude API)                 │  │
│  │                                                         │  │
│  │  ContractParser │ EmailComposer │ InspectionAnalyzer    │  │
│  │  FollowUpCoordinator │ AmendmentNotifier               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │            Background Jobs (Celery + Redis)             │  │
│  │  ScheduledReminders │ EmailDelivery │ StatusChecks      │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                       DATA LAYER                              │
│                                                               │
│  ┌──────────────┐  ┌──────────┐  ┌─────────────────────┐     │
│  │ PostgreSQL   │  │  Redis   │  │  S3 / MinIO         │     │
│  │ (structured  │  │  (cache, │  │  (documents,        │     │
│  │  data, PII)  │  │  queues) │  │  contracts, reports)│     │
│  └──────────────┘  └──────────┘  └─────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Tech Stack Detail

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Frontend Framework | React | 18+ | Component-based, large ecosystem |
| Frontend Language | TypeScript | 5+ | Type safety for complex data models |
| Frontend Styling | Tailwind CSS | 3+ | Rapid, consistent styling |
| Frontend State | Zustand or React Query | Latest | Lightweight state management |
| Backend Framework | FastAPI | 0.100+ | Async-first, auto-docs, Pydantic validation |
| Backend Language | Python | 3.11+ | AI library ecosystem, document processing |
| Database | PostgreSQL | 16+ | Relational integrity, JSON support, encryption |
| ORM | SQLAlchemy | 2.0+ | Async support, migration tooling |
| Migrations | Alembic | Latest | Database schema versioning |
| Job Queue | Celery | 5+ | Distributed task scheduling |
| Message Broker | Redis | 7+ | Queue backend + caching |
| AI Engine | Claude API (Anthropic) | Sonnet 4.5 / Haiku 4.5 | Document understanding, structured output |
| Document Storage | AWS S3 | - | Scalable, encrypted object storage |
| Email Delivery | SendGrid | v3 API | Deliverability, tracking, templates |
| Authentication | Clerk or Auth0 | Latest | Managed auth with RBAC |
| PDF Processing | PyMuPDF (fitz) | Latest | Fast PDF text/image extraction |
| Containerization | Docker + Docker Compose | Latest | Consistent dev/prod environments |
| CI/CD | GitHub Actions | - | Automated testing and deployment |

### 7.3 Data Model (Complete)

```sql
-- Core transaction record
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES users(id),
    status VARCHAR(50) NOT NULL DEFAULT 'intake',
        -- intake, review, active, pending_inspection, pending_appraisal,
        -- pending_closing, closed, cancelled
    representation_side VARCHAR(10) NOT NULL,
        -- buyer, seller, dual
    financing_type VARCHAR(20) NOT NULL,
        -- conventional, fha, va, usda, cash, owner_financing
    property_address TEXT NOT NULL,
    property_city VARCHAR(100),
    property_state VARCHAR(2),
    property_zip VARCHAR(10),
    purchase_price DECIMAL(12,2),
    earnest_money_amount DECIMAL(10,2),
    closing_date DATE,
    contract_document_url TEXT,
    special_stipulations TEXT,
    ai_extraction_confidence JSONB,  -- per-field confidence scores
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- All people involved in the transaction
CREATE TABLE parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL,
        -- buyer, seller, buyer_agent, seller_agent, listing_agent,
        -- lender, lender_processor, attorney, title_company,
        -- inspector, appraiser
    name VARCHAR(200) NOT NULL,
    email VARCHAR(200),
    phone VARCHAR(20),
    company VARCHAR(200),
    is_primary BOOLEAN DEFAULT true,  -- for multi-party (first buyer vs second buyer)
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transaction milestones and deadlines
CREATE TABLE milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
        -- earnest_money, inspection, wood_infestation, repair_request,
        -- repair_response, appraisal_ordered, appraisal_complete,
        -- financing_contingency, title_search, survey,
        -- final_walkthrough, closing_prep, closing
    title VARCHAR(200) NOT NULL,
    due_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming',
        -- upcoming, scheduled, in_progress, completed, waived, overdue
    responsible_party_role VARCHAR(30),  -- which party role is responsible
    notes TEXT,
    completed_at TIMESTAMPTZ,
    reminder_days_before INTEGER DEFAULT 2,
    last_reminder_sent_at TIMESTAMPTZ,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- All emails sent through the system
CREATE TABLE communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    milestone_id UUID REFERENCES milestones(id),
    recipient_party_id UUID REFERENCES parties(id),
    type VARCHAR(30) NOT NULL,
        -- welcome, contract_delivery, next_steps, reminder,
        -- milestone_update, follow_up, amendment_notice,
        -- closing_prep, congratulations
    recipient_email VARCHAR(200) NOT NULL,
    subject VARCHAR(500),
    body TEXT,
    attachments JSONB,  -- [{filename, s3_url}]
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
        -- draft, approved, queued, sent, delivered, opened, bounced, failed
    sendgrid_message_id VARCHAR(200),
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    template_used VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Inspection analysis results
CREATE TABLE inspection_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    report_document_url TEXT NOT NULL,
    executive_summary TEXT,
    total_estimated_cost_low DECIMAL(10,2),
    total_estimated_cost_high DECIMAL(10,2),
    overall_risk_level VARCHAR(20),  -- low, moderate, high, critical
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual inspection findings
CREATE TABLE inspection_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES inspection_analyses(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    location VARCHAR(200),  -- e.g., "Master bathroom", "Roof", "Foundation"
    severity VARCHAR(20) NOT NULL,
        -- critical, major, moderate, minor, cosmetic
    estimated_cost_low DECIMAL(10,2),
    estimated_cost_high DECIMAL(10,2),
    risk_assessment TEXT,
    recommendation TEXT,
    repair_status VARCHAR(20) DEFAULT 'identified',
        -- identified, requested, countered, agreed, denied, completed
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transaction change log
CREATE TABLE amendments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    field_changed VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    changed_by UUID REFERENCES users(id),
    notification_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User accounts
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id VARCHAR(200) UNIQUE NOT NULL,
    email VARCHAR(200) NOT NULL,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    brokerage_name VARCHAR(200),
    license_number VARCHAR(50),
    state VARCHAR(2),
    email_signature TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email templates (customizable per agent)
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES users(id),  -- NULL = system default
    name VARCHAR(100) NOT NULL,
    type VARCHAR(30) NOT NULL,
    representation_side VARCHAR(10),  -- buyer, seller, dual, or NULL for universal
    recipient_role VARCHAR(30),
    subject_template TEXT,
    body_template TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Email Communication Matrix

### 8.1 Initial Outreach — Buyer Representation

| Recipient | Email Type | Attachments | Key Content |
|-----------|-----------|-------------|-------------|
| Buyer (client) | Welcome + Next Steps | None | Congratulations, earnest money instructions, inspection timeline, key dates, what to expect |
| Mortgage Lender | Contract Delivery | Executed contract | Property details, purchase price, closing date, buyer info, request to begin processing |
| Attorney/Title | Contract Delivery | Executed contract | All party contacts, property details, earnest money details, financing type, request to open file |
| Listing Agent | Confirmation | None | Contract confirmation, buyer agent contact info, lender info, communication preferences |

### 8.2 Initial Outreach — Seller Representation

| Recipient | Email Type | Attachments | Key Content |
|-----------|-----------|-------------|-------------|
| Seller (client) | Welcome + Next Steps | None | Contract confirmation, inspection prep, property access scheduling, key dates |
| Attorney/Title | Contract Delivery | Executed contract | All party contacts, property details, payoff info request, closing date |
| Mortgage Lender | Contract Delivery | Executed contract | Property details, access coordination for appraisal |
| Buyer's Agent | Confirmation | None | Contract confirmation, seller agent contact, property access instructions |

### 8.3 Initial Outreach — Dual Agency

| Recipient | Email Type | Attachments | Key Content |
|-----------|-----------|-------------|-------------|
| Buyer (client) | Welcome + Next Steps | None | Same as buyer-side, with dual agency disclosure noted |
| Seller (client) | Welcome + Next Steps | None | Same as seller-side, with dual agency disclosure noted |
| Mortgage Lender | Contract Delivery | Executed contract | Standard lender package |
| Attorney/Title | Contract Delivery | Executed contract | Standard attorney package, note dual representation |

### 8.4 Follow-Up Communication Schedule

| Trigger | Recipients | Content |
|---------|-----------|---------|
| Earnest money due (2 days before) | Buyer, Attorney | Reminder to deliver earnest money |
| Earnest money received | All parties | Confirmation |
| Inspection scheduled | Buyer, Seller (or seller's agent), Inspector | Date, time, access instructions |
| Inspection complete | Buyer (client) | Summary + analysis link |
| Repair request submitted | Seller (or seller's agent), Attorney | Repair request details |
| Repairs agreed | All parties | What was agreed, next steps |
| Appraisal ordered | Seller (or seller's agent) | Date, access needed |
| Appraisal complete | Buyer, Lender | Results summary, next steps |
| Financing cleared | All parties | Financing confirmed, proceed to closing |
| Closing date - 7 days | All parties | Pre-closing checklist, documents needed |
| Closing date - 3 days | Buyer, Seller | Final walkthrough scheduling |
| Closing date - 1 day | All parties | Final reminder: time, location, what to bring |
| Closing complete | All parties | Congratulations, next steps (keys, utilities, etc.) |

---

## 9. Milestone Definitions

### 9.1 Standard Milestones (Financing Transaction)

| # | Milestone | Default Timeline | Conditional On | Responsible Party |
|---|-----------|-----------------|----------------|-------------------|
| 1 | Earnest money delivery | Contract + 2-3 days | Always | Buyer |
| 2 | Home inspection | Contract + 7-10 days | Always | Buyer (schedules) |
| 3 | Wood infestation report | Contract + 7-14 days | State/contract | Buyer or Seller |
| 4 | Inspection response deadline | Inspection + 3-5 days | Inspection done | Buyer (submits) |
| 5 | Repair negotiation deadline | Response + 3-5 days | Repairs requested | Seller (responds) |
| 6 | Appraisal ordered | Contract + 7-14 days | Financing | Lender |
| 7 | Appraisal complete | Ordered + 7-14 days | Financing | Appraiser |
| 8 | Financing contingency deadline | Per contract | Financing | Lender |
| 9 | Title search complete | Contract + 14-21 days | Always | Attorney/Title |
| 10 | Survey complete | Contract + 14-21 days | If required | Surveyor |
| 11 | Final walkthrough | Closing - 1-3 days | Always | Buyer |
| 12 | Closing | Per contract | All clear | All parties |

### 9.2 Cash Transaction Milestones (Reduced Set)

Milestones 6, 7, and 8 (appraisal and financing) are REMOVED for cash transactions. All other milestones apply.

---

## 10. Inspection Analysis Specification

### 10.1 Severity Classification

| Level | Definition | Examples | Typical Cost |
|-------|-----------|----------|-------------|
| **Critical** | Immediate safety hazard or structural compromise | Foundation cracks, active gas leak, no smoke detectors, electrical fire risk, major structural damage | $2,000 - $25,000+ |
| **Major** | Significant system failure or replacement needed | Roof replacement, HVAC failure, main plumbing line issues, panel replacement | $500 - $10,000 |
| **Moderate** | Functional issue requiring professional repair | Water heater nearing end of life, minor roof leaks, bathroom exhaust not vented, deck railing loose | $200 - $2,000 |
| **Minor** | Small repairs, typically handyman-level | Dripping faucets, missing caulk, sticking doors, minor grading issues | $50 - $500 |
| **Cosmetic** | Appearance only, no functional impact | Paint touch-ups, nail pops, minor drywall cracks, cosmetic trim damage | $0 - $200 |

### 10.2 Risk Assessment Output

The AI generates a risk assessment that includes:
- **Overall property risk level** (low / moderate / high / critical)
- **Top 5 priority items** with reasoning
- **Total estimated repair cost range** (low-high)
- **Recommendation** (proceed as-is, request repairs, request credit, further evaluation needed, consider walking away)
- **Items requiring licensed professional evaluation** (structural engineer, electrician, plumber, etc.)

---

## 11. Security & Compliance

### 11.1 Data Security

| Requirement | Implementation |
|-------------|---------------|
| Encryption at rest | AES-256 for all stored data |
| Encryption in transit | TLS 1.3 for all API communication |
| PII protection | Field-level encryption for names, emails, phones, financial data |
| Document security | Private S3 buckets, signed URLs with 15-minute expiry |
| Authentication | Clerk/Auth0 with MFA support |
| Authorization | Role-based access — agents see only their transactions |
| Audit logging | All data access and modifications logged |
| Session management | JWT tokens with 24-hour expiry, refresh tokens |

### 11.2 Compliance

| Regulation | Approach |
|-----------|----------|
| RESPA | No referral fee implications in automated communications |
| CAN-SPAM | Unsubscribe links in all automated emails, proper sender identification |
| State licensing | Agent license number and brokerage included in all outgoing emails |
| Data retention | Configurable retention policies; default 7 years post-closing |
| CCPA/privacy | Data export and deletion capabilities for all stored PII |

### 11.3 State-Specific Configuration

| Configuration | Description |
|--------------|-------------|
| Attorney vs. Title state | Controls terminology and workflows |
| Default contingency periods | Pre-populated milestone dates |
| Required disclosures | Auto-included in email footers |
| Dual agency legality | Enables/disables dual agency workflow |
| License display requirements | Format of agent/brokerage info in emails |

**Launch state:** Alabama  
**Expansion targets:** Georgia, Florida, Mississippi, Louisiana, Texas

---

## 12. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Contract-to-first-email time | < 10 minutes | Timestamp delta |
| AI extraction accuracy | > 90% of fields correct without edit | Agent confirmation data |
| Email open rate | > 80% | SendGrid tracking |
| Milestone reminders sent on time | 100% | System logs |
| Transactions per agent (capacity) | 20+ concurrent without stress | User surveys |
| Agent time saved per transaction | 6+ hours | Before/after comparison |
| Agent satisfaction | 4.5+ / 5.0 | NPS surveys |
| System uptime | 99.5%+ | Monitoring |
| Zero missed closing deadlines | 0 missed due to system failure | Incident tracking |

---

## 13. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| AI misparses critical contract data | High | Medium | Mandatory human review before any action; confidence scores flag low-confidence fields |
| Email sent with incorrect information | High | Low | Preview + approval step before all sends; no fully autonomous emails in V1 |
| Milestone dates calculated incorrectly | Medium | Medium | Agent confirms all dates; system shows source (contract clause) for each date |
| AI cost overruns at scale | Medium | Low | Use Haiku for routine tasks, Sonnet only for complex analysis; monitor per-transaction costs |
| SendGrid deliverability issues | Medium | Low | SPF/DKIM/DMARC configuration; dedicated IP at scale; fallback provider |
| State-specific compliance gaps | High | Medium | Legal review of templates per state; configurable compliance rules |

---

*End of PRD — See Phase documents for implementation details.*
