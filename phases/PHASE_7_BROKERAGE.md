# Phase 7: Brokerage Platform — Multi-Agent Support, Compliance Monitoring & Team Management

**Timeline:** Weeks 18-22
**Status:** Not Started
**Depends On:** Phase 6 Complete
**CoV Status:** Verified (see below)

---

## 1. Phase Overview

**Goal:** Transform Armistead from a single-agent tool into a brokerage-wide platform. This is the revenue multiplier phase — moving from $39/month per individual agent to $500-2,000/month per brokerage. A managing broker signs up, invites their agents, and immediately gains visibility into every transaction across their office: compliance status, agent performance, pipeline health, and revenue forecasts. Agents retain their existing workflows while the broker gains a supervisory layer with audit trails, compliance rules, and team management capabilities.

**Timeline:** 5 weeks (Weeks 18-22). This is the longest and most architecturally significant phase because it retrofits multi-tenancy into every layer of the stack — database queries, API middleware, frontend routing, and permission checks.

**Key Deliverables:**
- **Brokerage Entity & Multi-Tenancy** — A `brokerages` table that serves as the organizational container. Every user is optionally associated with a brokerage through `brokerage_agents`. All existing queries gain an optional brokerage-scoped filter. Individual agents who are not part of a brokerage continue to work exactly as before (backward compatible).
- **Role-Based Access Control (RBAC)** — Five roles: `managing_broker`, `broker`, `agent`, `transaction_coordinator`, `assistant`. Each role has a defined permission set governing what data they can see and what actions they can take.
- **Broker Dashboard** — A dedicated `/brokerage` route showing aggregate transaction health, pipeline value, agent activity, compliance status, and revenue across the entire brokerage.
- **Compliance Monitoring** — Brokerages define compliance rules (e.g., "All transactions must have a signed agency disclosure within 3 days of contract"). The system automatically evaluates transactions against these rules and surfaces violations.
- **Agent Performance Metrics** — Average days-to-close, deal count, revenue generated, compliance score, milestone completion rate, and response time — all visible to the broker per agent.
- **Team Management** — Invite agents, assign/transfer transactions, deactivate agents, and manage roles.
- **Brokerage Branding** — Custom logo, primary color, and email template overrides per brokerage. Brokerage branding cascades to agents unless they override with their own.

---

## 2. Chain of Verification (CoV)

### Step 1: Baseline
Phase 7 adds multi-tenancy (brokerage entity, brokerage-agent membership, role-based access), a broker dashboard with aggregate metrics, compliance rule definition and automated checking, agent performance scoring, team management (invite, assign, transfer, deactivate), and brokerage-level branding. The system must remain fully functional for individual agents who are not part of any brokerage.

### Step 2: Self-Questioning and Independent Verification

| # | Question | Risk Level | Resolution |
|---|----------|------------|------------|
| 1 | How do we prevent data leakage between brokerages and between agents within the same brokerage? | **Critical** | Every database query that returns user-specific data passes through a `BrokerageScope` middleware that injects the appropriate filter. Agents see only their own transactions. Brokers see all transactions within their brokerage. Cross-brokerage queries are impossible at the ORM level because the scope filter is applied before the query executes, not after. Commission data has a separate visibility flag — brokers can see gross and net totals per agent but NOT individual split details unless the agent grants permission. Unit tests verify that agent A cannot retrieve agent B's data even if agent A manually constructs the URL with agent B's transaction ID. |
| 2 | What happens to existing individual agents when the brokerage feature launches? Do they break? | **Critical** | The `brokerage_id` and `brokerage_agent` associations are fully optional. Existing users with no brokerage association continue to operate identically — their queries are scoped to `agent_id = current_user.id` as before. The `BrokerageScope` middleware checks: if the user has a brokerage association and a broker-level role, expand the scope; otherwise, use the existing agent-scoped filter. No existing API endpoint changes its default behavior. New brokerage endpoints are additive. A comprehensive regression suite (Section 8) verifies that every Phase 1-6 feature works for non-brokerage users after Phase 7 deployment. |
| 3 | How do we handle role escalation attacks — can an agent promote themselves to broker? | **High** | Role changes are only possible through two paths: (a) the `managing_broker` role uses the `/api/brokerage/agents/:id/role` endpoint, which checks that the requester is a `managing_broker` for that brokerage; (b) a system-level admin override (not exposed via API, only via direct database access for support). The role field is never writable by the user on their own profile. All role checks happen server-side via the `require_role()` dependency. Frontend hides UI elements for unauthorized roles, but the backend enforces the actual permission boundary. |
| 4 | How do we handle the migration path — can an existing individual agent join a brokerage? Can they leave? | **High** | When an agent joins a brokerage, their existing transactions remain associated with them (`agent_id` unchanged). The brokerage gains read-only visibility into those transactions through the `brokerage_agents` relationship. When an agent leaves a brokerage, their `brokerage_agents.is_active` is set to `false` and `deactivated_at` is recorded. The broker retains read-only access to transactions that occurred during the agent's tenure (transactions where `created_at` falls between the agent's `joined_at` and `deactivated_at`). The agent retains full ownership. Active transactions can optionally be transferred to another agent in the brokerage (broker-initiated, with both agents notified). |
| 5 | What compliance rules make sense for the MVP, and how do we make them extensible? | **Medium** | Ship with 6 built-in compliance rule types that cover the most common brokerage requirements: (1) required milestone completion within N days of contract, (2) required party role present on transaction, (3) required document uploaded within N days, (4) required communication sent to party role within N days, (5) minimum transaction health score threshold, (6) required closing date set within N days. Each rule type has a parameterized check function. Brokers configure rules by selecting a type and filling in parameters. Custom rule types are out of scope — but the `check_function` column on `compliance_rules` stores a string identifier that maps to a Python function, making it extensible for future custom logic. |
| 6 | How do we calculate agent performance metrics without making the queries prohibitively expensive? | **Medium** | Pre-compute performance metrics via a Celery periodic task that runs nightly. Store the computed metrics in an `agent_performance_snapshots` table with a date column. The broker dashboard reads from the latest snapshot. Real-time "today" adjustments are applied in the API layer (e.g., adding today's newly closed deal to the snapshot count). This keeps dashboard queries fast (single row read per agent) while maintaining accuracy within 24 hours. A "Refresh Now" button triggers an on-demand recalculation for a single agent. |
| 7 | How do we handle brokerage branding vs. agent branding (Phase 6) — who wins? | **Low-Medium** | Branding cascades: brokerage branding is the default. If an agent has configured their own branding (Phase 6 `agent_branding` table), the agent's branding takes precedence for their documents. For compliance-required documents (if the brokerage mandates a standard letterhead), the brokerage can set `enforce_brokerage_branding = true` on the brokerage settings, which overrides agent branding for all generated documents. The document generation service (Phase 6) is modified to check: (1) if brokerage exists and enforces branding, use brokerage branding; (2) else if agent has branding, use agent branding; (3) else if brokerage exists, use brokerage branding as default; (4) else use minimal default. |
| 8 | What about billing — does the brokerage pay for all agents, or does each agent pay individually? | **Medium** | Add a `billing_type` field to `brokerages`: `brokerage_pays` (brokerage pays a per-seat or flat rate for all agents) or `agent_pays` (each agent has their own subscription, brokerage gets the dashboard for free). The actual payment processing (Stripe integration) is out of scope for Phase 7, but the data model supports both billing models. The brokerage creation flow asks the broker which model they prefer. For now, all brokerages are on a manual invoicing model; Stripe integration is a fast-follow. |
| 9 | How do we handle transaction transfer between agents — what about in-progress milestones, communications, and party relationships? | **Medium** | Transaction transfer is a first-class operation with a dedicated service (`TransactionTransferService`). The transfer: (a) changes `transaction.agent_id` to the new agent, (b) logs the transfer in an `agent_transfers` audit table (old_agent, new_agent, reason, timestamp), (c) sends a notification to both agents and all parties ("Your point of contact has changed"), (d) updates any pending notification rules to target the new agent, (e) does NOT change historical communication records (they remain attributed to the original sending agent for audit purposes). Milestones retain their data but future nudges go to the new agent. |
| 10 | What about brokerages with multiple offices/locations? | **Low** | Phase 7 models a brokerage as a single entity. The `brokerages` table has an `address` field but no concept of "office." Agents can be tagged with a `location` string in `brokerage_agents` for reporting purposes, but there is no separate `offices` table. Multi-office support with office-level dashboards and compliance is deferred to a post-Phase 7 enhancement. The data model is designed so that adding an `office_id` FK to `brokerage_agents` later is non-breaking. |
| 11 | How do we onboard a brokerage with 50+ agents efficiently? | **Medium** | Support two onboarding paths: (a) individual invite via email (broker enters email, system sends invite link), (b) bulk CSV upload (broker uploads a CSV with columns: email, name, role). The invite system creates a `brokerage_invites` record with a unique token. When the agent clicks the invite link, they either sign up (new user) or link their existing account to the brokerage. Invites expire after 14 days. The broker can resend or revoke invites. |
| 12 | What audit trail does a managing broker need for regulatory compliance? | **Medium** | Every brokerage-scoped action is logged in a `brokerage_audit_log` table: who did what, when, to which resource. Key audited actions: agent invited, agent deactivated, role changed, transaction transferred, compliance rule created/modified, compliance check overridden. The audit log is append-only (no deletes) and accessible only to `managing_broker` role. Export as CSV for regulatory submissions. |

### Step 3: Confidence Check
**Confidence: 91%** — The multi-tenancy retrofit is the highest-risk element. The middleware-based scoping approach is proven but requires touching every existing query path. The mitigation is the extensive regression test suite (Section 8) and the fact that the brokerage association is fully optional — existing users are not affected unless they explicitly join a brokerage. The compliance rules MVP (6 parameterized types) covers the most common needs without overengineering.

### Step 4: Implement
Proceed with Phase 7. Start with the data model and RBAC middleware (Week 18), then broker dashboard and team management (Week 19), compliance engine (Week 20), frontend (Week 21), and integration testing with branding (Week 22).

---

## 3. Detailed Requirements

### 3.1 Multi-Tenancy Architecture

The brokerage multi-tenancy model uses a **shared database, shared schema** approach with row-level filtering. This is the simplest model that works at the scale we are targeting (brokerages with 5-200 agents).

**How it works:**

1. A `brokerages` table contains the brokerage entity.
2. A `brokerage_agents` join table links users to brokerages with a role.
3. A `BrokerageScope` dependency (FastAPI `Depends`) is injected into every endpoint that returns data. It inspects the current user's brokerage membership and role, then returns a scoping function.
4. For **individual agents** (no brokerage membership): the scope is `WHERE agent_id = :current_user_id` — identical to the current behavior.
5. For **agents within a brokerage**: the scope is still `WHERE agent_id = :current_user_id` — agents see only their own transactions. Being part of a brokerage does not expand an agent's data access.
6. For **brokers and managing brokers**: the scope expands to `WHERE agent_id IN (SELECT user_id FROM brokerage_agents WHERE brokerage_id = :brokerage_id AND is_active = true)` — they see all transactions for all active agents in their brokerage.
7. For **transaction coordinators**: the scope is either their own transactions OR transactions explicitly assigned to them via a `tc_assignments` relationship (broker assigns a TC to specific transactions).
8. For **assistants**: scoped to transactions of the agent(s) they are assigned to assist.

**Critical constraint:** The scope filter is applied at the query layer, not the application layer. This means even if a malicious client sends a valid transaction UUID, the query will return 404 if the transaction does not fall within the user's scope. There is no path to data leakage through direct ID access.

### 3.2 Role-Based Access Control (RBAC)

| Role | Code | Data Access | Actions |
|------|------|-------------|---------|
| Managing Broker | `managing_broker` | All transactions in brokerage. All agent data. Compliance rules. Audit log. Commission totals per agent. | Invite/remove agents. Change roles. Transfer transactions. Create/edit compliance rules. Override compliance checks. Export audit log. Configure brokerage branding. |
| Broker | `broker` | All transactions in brokerage. Agent performance metrics. Compliance status (read-only). | View all dashboards. Transfer transactions. View compliance. Cannot change roles or edit compliance rules. |
| Agent | `agent` | Own transactions only. Own commission data. Own performance metrics. | Full transaction CRUD. All Phase 1-6 features on own transactions. Cannot see other agents' data. |
| Transaction Coordinator | `transaction_coordinator` | Assigned transactions only. Cannot see commission data. | Edit milestones, update statuses, manage communications, upload documents on assigned transactions. Cannot create new transactions. |
| Assistant | `assistant` | Transactions of assigned agent(s). Cannot see commission data. | Read-only access to assigned transactions. Can add notes and upload documents. Cannot modify milestones, send communications, or change transaction status. |

**Permission matrix (per endpoint group):**

| Endpoint Group | Managing Broker | Broker | Agent | TC | Assistant |
|---------------|----------------|--------|-------|----|-----------|
| Transaction CRUD | Full (brokerage-wide) | Read (brokerage-wide) | Full (own) | Edit (assigned) | Read (assigned) |
| Milestone CRUD | Full (brokerage-wide) | Read (brokerage-wide) | Full (own) | Full (assigned) | Read (assigned) |
| Commission data | Read totals (brokerage-wide) | Read totals (brokerage-wide) | Full (own) | None | None |
| Compliance rules | Full | Read | None | None | None |
| Compliance checks | Read + override | Read | Read (own) | Read (assigned) | None |
| Agent management | Full | Read | None | None | None |
| Brokerage settings | Full | Read | None | None | None |
| Audit log | Full | None | None | None | None |
| Document generation | Full (brokerage-wide) | Read (brokerage-wide) | Full (own) | Full (assigned) | None |
| AI Advisor | Brokerage-wide context | Brokerage-wide context | Own context | Assigned context | None |

### 3.3 Compliance Monitoring

Compliance is the managing broker's primary concern. State real estate commissions hold the broker responsible for agent conduct. The compliance engine automates the supervisory checks that managing brokers currently do manually (or, more often, fail to do at all).

**Built-in compliance rule types:**

| Rule Type | Code | Parameters | Check Logic |
|-----------|------|------------|-------------|
| Milestone deadline | `milestone_deadline` | `milestone_name: string`, `max_days_from_contract: int` | Checks if a milestone matching the name exists and was completed within N days of contract execution date |
| Required party | `required_party` | `party_role: string` | Checks if a party with the specified role exists on the transaction |
| Required document | `required_document` | `document_keyword: string`, `max_days_from_contract: int` | Checks if a file containing the keyword in its name was uploaded within N days |
| Required communication | `required_communication` | `party_role: string`, `max_days_from_contract: int` | Checks if at least one communication was sent to a party with the specified role within N days |
| Health score threshold | `health_score_min` | `min_score: int` | Checks if the transaction health score (Phase 1) is at or above the threshold |
| Closing date set | `closing_date_required` | `max_days_from_contract: int` | Checks if the closing date has been set within N days of transaction creation |

**Compliance check lifecycle:**

1. When a compliance rule is created or modified, the system queues a Celery task to evaluate all active transactions in the brokerage against the rule.
2. A nightly Celery beat task re-evaluates all active transactions against all compliance rules for their brokerage.
3. When a transaction is updated (milestone completed, document uploaded, party added, communication sent), the system re-evaluates that transaction against all applicable compliance rules.
4. Compliance check results are stored in `compliance_checks` with status: `pass`, `fail`, `warning`, `overridden`.
5. The broker can override a `fail` to `overridden` with a required reason (stored in `override_reason`). This is logged in the audit trail.
6. The compliance dashboard shows: total checks run, pass rate, failing transactions (grouped by rule), and a trend chart of compliance over time.

**Default compliance templates:** When a brokerage is created, the system suggests a set of common compliance rules based on the brokerage's state:
- Agency disclosure signed within 3 days
- Buyer represented (buyer agent or dual agency)
- Inspection completed within inspection period
- Title company party present
- Closing date set within 7 days of contract
- Weekly communication to client (buyer or seller)

The broker can accept, modify, or dismiss each suggestion.

### 3.4 Agent Onboarding and Team Management

**Invite flow:**

1. Managing broker clicks "Invite Agent" on the agent management page.
2. Enters the agent's email and selects a role (default: `agent`).
3. System creates a `brokerage_invites` record with a unique token and sends an email via Resend.
4. The invited person clicks the link:
   - If they have an existing Armistead account: they see a "Join [Brokerage Name]" confirmation screen. On confirm, a `brokerage_agents` record is created.
   - If they do not have an account: they are directed to the sign-up flow. After sign-up, the invite is automatically applied.
5. Invite tokens expire after 14 days. The broker can resend (generates a new token) or revoke.

**Bulk invite:**

1. Managing broker clicks "Bulk Invite" and uploads a CSV file.
2. Required CSV columns: `email`, `name`. Optional: `role`, `phone`, `license_number`.
3. System validates the CSV: checks email format, deduplicates against existing members, and checks for previously invited emails.
4. System sends invites to all valid rows and returns a summary: "Sent 47 invites. Skipped 3 (already members)."

**Transaction assignment and transfer:**

- A managing broker or broker can assign a transaction to a different agent within the brokerage.
- The transfer operation is described in CoV #9: changes `agent_id`, logs the transfer, notifies parties, and updates notification targeting.
- Transfer reason is required (dropdown: "Agent departure", "Workload balancing", "Client request", "Other" with free text).
- The original agent retains read-only access to the transferred transaction for 90 days (for their records and potential commission disputes).

**Agent deactivation:**

- When an agent leaves the brokerage, the managing broker sets `brokerage_agents.is_active = false` and `deactivated_at = now()`.
- Active transactions are flagged for transfer — the broker sees a "Transfer Required" alert.
- The deactivated agent loses brokerage-scoped features but retains access to their own transactions through their individual account (if `billing_type = agent_pays`) or loses access entirely (if `billing_type = brokerage_pays` and the brokerage revokes the seat).
- Historical data is preserved for the brokerage's audit trail.

### 3.5 Brokerage Branding

Brokerage branding provides a consistent visual identity across all agents in the brokerage.

**Configurable elements:**
- `logo_url` — Brokerage logo (uploaded to MinIO). Displayed in the top-left of the broker dashboard and on generated documents.
- `primary_color` — Hex color code used for accents in the dashboard and document headers.
- `secondary_color` — Optional secondary accent color.
- `email_header_html` — Custom HTML snippet prepended to all emails sent by agents in the brokerage (for regulatory compliance — some states require brokerage identification on all agent communications).
- `email_footer_html` — Custom HTML snippet appended to all emails (brokerage address, fair housing notice, etc.).
- `enforce_brokerage_branding` — Boolean. If true, brokerage branding overrides individual agent branding (Phase 6) on all generated documents.
- `company_name` — Displayed name (may differ from legal entity name).
- `address`, `phone`, `website` — Brokerage contact information for documents and emails.

**Cascade logic:**
1. If `enforce_brokerage_branding` is true: all documents and emails use brokerage branding. Agent branding is ignored.
2. If `enforce_brokerage_branding` is false and agent has their own branding: agent branding is used for their documents. Brokerage email header/footer is still appended to emails.
3. If `enforce_brokerage_branding` is false and agent has no branding: brokerage branding is used as the default.
4. If user is not part of a brokerage: existing Phase 6 behavior (agent branding or minimal default).

### 3.6 Broker Dashboard

The broker dashboard (`/brokerage`) is the managing broker's command center. It provides a high-level overview of the entire brokerage's transaction activity, compliance health, and revenue.

**Dashboard sections:**

1. **Summary Cards (top row):**
   - Total active transactions (across all agents)
   - Total pipeline value (sum of all projected commissions)
   - Brokerage-wide compliance rate (% of compliance checks passing)
   - Agents active / total agents
   - Transactions closing this month
   - Revenue closed YTD (actual commissions from Phase 5)

2. **Agent Activity Feed (left column):**
   - Real-time feed of recent actions across the brokerage: transactions created, milestones completed, documents generated, communications sent. Each entry shows the agent name, action, and timestamp. Filterable by agent and action type.

3. **Compliance Overview (center):**
   - Donut chart: pass / fail / warning / overridden
   - List of currently failing compliance checks, grouped by rule, with transaction links and agent names
   - "Compliance Trend" line chart showing pass rate over the last 30/60/90 days

4. **Agent Performance Table (right column):**
   - Table of all agents with columns: name, active deals, pipeline value, avg days-to-close, compliance score, last activity date
   - Sortable by any column
   - Click agent name to drill into agent detail view

5. **Pipeline by Month (bottom):**
   - Stacked bar chart showing expected revenue by month, colored by confidence level (Phase 5 forecast data aggregated across all agents)
   - Comparison line showing last year's actuals (if data exists)

### 3.7 Agent Performance Metrics

Performance metrics are computed nightly by a Celery beat task and stored in `agent_performance_snapshots`.

**Metrics computed per agent:**

| Metric | Code | Calculation |
|--------|------|-------------|
| Active deal count | `active_deals` | COUNT of transactions with status = 'active' |
| Closed deal count (YTD) | `closed_ytd` | COUNT of transactions closed in current year |
| Closed deal count (MTD) | `closed_mtd` | COUNT of transactions closed in current month |
| Average days to close | `avg_days_to_close` | AVG(closing_date - created_at) for closed transactions in trailing 12 months |
| Total pipeline value | `pipeline_value` | SUM of projected_net from active transaction commissions |
| Revenue closed YTD | `revenue_ytd` | SUM of actual_net (or projected_net if actual is null) for transactions closed in current year |
| Revenue closed MTD | `revenue_mtd` | SUM of actual_net for transactions closed in current month |
| Compliance score | `compliance_score` | (passing_checks / total_checks) * 100 across active transactions |
| Milestone completion rate | `milestone_completion_rate` | (completed_milestones / total_milestones) * 100 across active transactions |
| Average health score | `avg_health_score` | AVG of transaction health scores (Phase 1) across active transactions |
| Lost deal count (YTD) | `lost_ytd` | COUNT of cancelled/terminated transactions in current year |
| Conversion rate | `conversion_rate` | closed_ytd / (closed_ytd + lost_ytd) * 100 |

**Agent detail view** (`/brokerage/agents/:id`):
- Agent profile: name, email, phone, license number, role, joined date, last active
- Performance metrics table (current snapshot)
- Performance trend charts (last 6 months of snapshots)
- List of active transactions with health scores
- Compliance checks for the agent's transactions (pass/fail breakdown)
- Transaction history (closed and lost in the last 12 months)

---

## 4. Data Model

### 4.1 brokerages

The core brokerage entity.

```python
class Brokerage(BaseModel):
    __tablename__ = "brokerages"

    name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)  # display name if different from legal name
    license_number = Column(String, nullable=True)  # brokerage license
    state = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)  # MinIO URL
    primary_color = Column(String, nullable=True)  # hex, e.g. "#1a56db"
    secondary_color = Column(String, nullable=True)
    email_header_html = Column(Text, nullable=True)
    email_footer_html = Column(Text, nullable=True)
    enforce_brokerage_branding = Column(Boolean, default=False)
    billing_type = Column(String, nullable=False, default="brokerage_pays")  # brokerage_pays | agent_pays
    settings = Column(JSON, nullable=True)  # extensible settings blob
    is_active = Column(Boolean, default=True)

    # Relationships
    agents = relationship("BrokerageAgent", back_populates="brokerage", cascade="all, delete-orphan")
    compliance_rules = relationship("ComplianceRule", back_populates="brokerage", cascade="all, delete-orphan")
    invites = relationship("BrokerageInvite", back_populates="brokerage", cascade="all, delete-orphan")
    audit_log = relationship("BrokerageAuditLog", back_populates="brokerage", cascade="all, delete-orphan")
```

### 4.2 brokerage_agents

Join table linking users to brokerages with role and metadata.

```python
class BrokerageAgent(BaseModel):
    __tablename__ = "brokerage_agents"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False, default="agent")  # managing_broker | broker | agent | transaction_coordinator | assistant
    is_active = Column(Boolean, default=True)
    joined_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    deactivated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    location = Column(String, nullable=True)  # office location tag (free text for reporting)
    assigned_to_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # for TC/assistant: which agent(s) they support

    # Unique constraint: a user can belong to only one brokerage at a time
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_brokerage_agents_user_id"),
    )

    # Relationships
    brokerage = relationship("Brokerage", back_populates="agents")
    user = relationship("User", back_populates="brokerage_membership", foreign_keys=[user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_agent_id])
```

### 4.3 compliance_rules

Defines the compliance rules a brokerage has configured.

```python
class ComplianceRule(BaseModel):
    __tablename__ = "compliance_rules"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=False)
    name = Column(String, nullable=False)  # human-readable name, e.g. "Agency Disclosure within 3 days"
    description = Column(Text, nullable=True)
    rule_type = Column(String, nullable=False)  # milestone_deadline | required_party | required_document | required_communication | health_score_min | closing_date_required
    parameters = Column(JSON, nullable=False)  # type-specific params, e.g. {"milestone_name": "Agency Disclosure", "max_days_from_contract": 3}
    severity = Column(String, nullable=False, default="warning")  # warning | critical
    is_active = Column(Boolean, default=True)
    applies_to_status = Column(JSON, nullable=True)  # which transaction statuses this rule applies to, e.g. ["active", "pending_close"]. Null = all statuses.
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Relationships
    brokerage = relationship("Brokerage", back_populates="compliance_rules")
    created_by = relationship("User")
    checks = relationship("ComplianceCheck", back_populates="rule", cascade="all, delete-orphan")
```

### 4.4 compliance_checks

Stores the result of evaluating a compliance rule against a specific transaction.

```python
class ComplianceCheck(BaseModel):
    __tablename__ = "compliance_checks"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("compliance_rules.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # the agent who owns the transaction
    status = Column(String, nullable=False)  # pass | fail | warning | overridden
    checked_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    details = Column(JSON, nullable=True)  # explanation, e.g. {"found_milestone": "Agency Disclosure", "completed_at": "...", "days_elapsed": 2}
    override_reason = Column(Text, nullable=True)  # required when status = overridden
    overridden_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    overridden_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Unique constraint: one check result per rule per transaction (latest wins)
    __table_args__ = (
        UniqueConstraint("transaction_id", "rule_id", name="uq_compliance_check_txn_rule"),
    )

    # Relationships
    transaction = relationship("Transaction", back_populates="compliance_checks")
    rule = relationship("ComplianceRule", back_populates="checks")
    agent = relationship("User", foreign_keys=[agent_id])
    overridden_by = relationship("User", foreign_keys=[overridden_by_id])
```

### 4.5 brokerage_invites

Tracks pending agent invitations.

```python
class BrokerageInvite(BaseModel):
    __tablename__ = "brokerage_invites"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=False)
    email = Column(String, nullable=False)
    role = Column(String, nullable=False, default="agent")
    token = Column(String, unique=True, nullable=False)  # unique invite token
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending | accepted | expired | revoked
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    accepted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    brokerage = relationship("Brokerage", back_populates="invites")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])
```

### 4.6 agent_performance_snapshots

Pre-computed agent performance metrics for efficient dashboard rendering.

```python
class AgentPerformanceSnapshot(BaseModel):
    __tablename__ = "agent_performance_snapshots"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    active_deals = Column(Integer, default=0)
    closed_ytd = Column(Integer, default=0)
    closed_mtd = Column(Integer, default=0)
    avg_days_to_close = Column(Numeric(8, 2), nullable=True)
    pipeline_value = Column(Numeric(14, 2), default=0)
    revenue_ytd = Column(Numeric(14, 2), default=0)
    revenue_mtd = Column(Numeric(14, 2), default=0)
    compliance_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    milestone_completion_rate = Column(Numeric(5, 2), nullable=True)  # 0-100
    avg_health_score = Column(Numeric(5, 2), nullable=True)  # 0-100
    lost_ytd = Column(Integer, default=0)
    conversion_rate = Column(Numeric(5, 2), nullable=True)  # 0-100

    __table_args__ = (
        UniqueConstraint("agent_id", "snapshot_date", name="uq_perf_snapshot_agent_date"),
    )

    # Relationships
    agent = relationship("User")
    brokerage = relationship("Brokerage")
```

### 4.7 agent_transfers

Audit log for transaction transfers between agents.

```python
class AgentTransfer(BaseModel):
    __tablename__ = "agent_transfers"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    from_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    to_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transferred_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # the broker who initiated
    reason = Column(String, nullable=False)  # agent_departure | workload_balancing | client_request | other
    reason_details = Column(Text, nullable=True)
    transferred_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    transaction = relationship("Transaction")
    from_agent = relationship("User", foreign_keys=[from_agent_id])
    to_agent = relationship("User", foreign_keys=[to_agent_id])
    transferred_by = relationship("User", foreign_keys=[transferred_by_id])
```

### 4.8 brokerage_audit_log

Append-only audit log for brokerage-level actions.

```python
class BrokerageAuditLog(BaseModel):
    __tablename__ = "brokerage_audit_log"

    brokerage_id = Column(UUID(as_uuid=True), ForeignKey("brokerages.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # who performed the action
    action = Column(String, nullable=False)  # agent_invited | agent_deactivated | role_changed | transaction_transferred | compliance_rule_created | compliance_rule_modified | compliance_check_overridden | branding_updated | settings_updated
    resource_type = Column(String, nullable=True)  # user | transaction | compliance_rule | compliance_check | brokerage
    resource_id = Column(UUID(as_uuid=True), nullable=True)  # ID of the affected resource
    details = Column(JSON, nullable=True)  # additional context, e.g. {"old_role": "agent", "new_role": "broker"}
    ip_address = Column(String, nullable=True)

    # Relationships
    brokerage = relationship("Brokerage", back_populates="audit_log")
    actor = relationship("User")
```

### 4.9 Modifications to Existing Models

```python
# --- User model additions ---
# Add to User:
brokerage_membership = relationship("BrokerageAgent", back_populates="user", uselist=False, foreign_keys="BrokerageAgent.user_id")

# --- Transaction model additions ---
# Add to Transaction:
compliance_checks = relationship("ComplianceCheck", back_populates="transaction", cascade="all, delete-orphan")
transfers = relationship("AgentTransfer", back_populates="transaction")
```

### 4.10 Alembic Migration Notes

The Phase 7 migration is the most complex in the project. It should be split into multiple revisions for safety:

1. **Migration 7a:** Create `brokerages`, `brokerage_agents`, `brokerage_invites` tables. Add `brokerage_membership` relationship to User. No data migration required — all existing users simply have no brokerage membership.
2. **Migration 7b:** Create `compliance_rules`, `compliance_checks` tables. Add `compliance_checks` relationship to Transaction.
3. **Migration 7c:** Create `agent_performance_snapshots`, `agent_transfers`, `brokerage_audit_log` tables.
4. All migrations are additive (new tables, new columns). No existing columns are modified or dropped. This ensures zero-downtime deployment.

---

## 5. API Endpoints

### 5.1 Brokerage Management

| Method | Endpoint | Auth | Description | Request Body | Response |
|--------|----------|------|-------------|-------------|----------|
| POST | `/api/brokerages` | Authenticated user | Create a new brokerage (caller becomes managing_broker) | `{name, state, address, phone, billing_type}` | `{id, name, ...}` |
| GET | `/api/brokerages/me` | Brokerage member | Get the current user's brokerage details | - | `{id, name, agent_count, settings, ...}` |
| PATCH | `/api/brokerages/me` | Managing Broker | Update brokerage details | `{name?, address?, phone?, settings?}` | `{id, name, ...}` |
| PUT | `/api/brokerages/me/branding` | Managing Broker | Update brokerage branding | `{logo_url?, primary_color?, email_header_html?, enforce_brokerage_branding?}` | `{branding}` |
| POST | `/api/brokerages/me/logo` | Managing Broker | Upload brokerage logo | Multipart file | `{logo_url}` |

### 5.2 Broker Dashboard

| Method | Endpoint | Auth | Description | Query Params | Response |
|--------|----------|------|-------------|-------------|----------|
| GET | `/api/brokerage/dashboard` | Broker+ | Aggregate brokerage dashboard data | `period=30d\|60d\|90d\|ytd` | `{summary_cards, compliance_overview, pipeline_by_month}` |
| GET | `/api/brokerage/activity` | Broker+ | Recent activity feed across brokerage | `limit, offset, agent_id?, action_type?` | `{activities: [{agent, action, resource, timestamp}]}` |
| GET | `/api/brokerage/pipeline` | Broker+ | Brokerage-wide pipeline summary | `period` | `{total_pipeline, monthly_forecast[], at_risk_transactions[]}` |

### 5.3 Agent Management

| Method | Endpoint | Auth | Description | Request Body | Response |
|--------|----------|------|-------------|-------------|----------|
| GET | `/api/brokerage/agents` | Broker+ | List all agents with performance metrics | `?role=&is_active=&sort_by=` | `{agents: [{user, role, performance_snapshot}]}` |
| GET | `/api/brokerage/agents/:id` | Broker+ | Agent detail with full metrics | - | `{user, role, performance, active_transactions[], compliance_checks[]}` |
| POST | `/api/brokerage/agents/invite` | Managing Broker | Invite a single agent | `{email, role?}` | `{invite_id, status}` |
| POST | `/api/brokerage/agents/invite/bulk` | Managing Broker | Bulk invite via CSV | Multipart CSV file | `{sent: int, skipped: int, errors: []}` |
| PATCH | `/api/brokerage/agents/:id/role` | Managing Broker | Change an agent's role | `{role}` | `{agent_id, new_role}` |
| POST | `/api/brokerage/agents/:id/deactivate` | Managing Broker | Deactivate an agent | `{transfer_transactions_to?: agent_id}` | `{status, transactions_to_transfer: int}` |
| POST | `/api/brokerage/agents/:id/reactivate` | Managing Broker | Reactivate a previously deactivated agent | - | `{status}` |
| GET | `/api/brokerage/invites` | Managing Broker | List all pending invites | `?status=pending` | `{invites: [{email, role, status, expires_at}]}` |
| POST | `/api/brokerage/invites/:id/resend` | Managing Broker | Resend an invite email | - | `{status}` |
| DELETE | `/api/brokerage/invites/:id` | Managing Broker | Revoke an invite | - | `{status: "revoked"}` |

### 5.4 Transaction Transfer

| Method | Endpoint | Auth | Description | Request Body | Response |
|--------|----------|------|-------------|-------------|----------|
| POST | `/api/brokerage/transactions/:id/transfer` | Broker+ | Transfer a transaction to another agent | `{to_agent_id, reason, reason_details?}` | `{transfer_id, status}` |
| GET | `/api/brokerage/transfers` | Broker+ | List all transfers in the brokerage | `?from_agent_id=&to_agent_id=&limit=` | `{transfers: [{transaction, from, to, reason, date}]}` |

### 5.5 Compliance

| Method | Endpoint | Auth | Description | Request Body | Response |
|--------|----------|------|-------------|-------------|----------|
| GET | `/api/brokerage/compliance/rules` | Broker+ | List all compliance rules | `?is_active=true` | `{rules: [{id, name, rule_type, parameters, severity}]}` |
| POST | `/api/brokerage/compliance/rules` | Managing Broker | Create a compliance rule | `{name, rule_type, parameters, severity}` | `{id, name, ...}` |
| PATCH | `/api/brokerage/compliance/rules/:id` | Managing Broker | Update a compliance rule | `{name?, parameters?, severity?, is_active?}` | `{id, ...}` |
| DELETE | `/api/brokerage/compliance/rules/:id` | Managing Broker | Delete a compliance rule | - | `{status: "deleted"}` |
| GET | `/api/brokerage/compliance/checks` | Broker+ | List compliance check results | `?status=fail&agent_id=&rule_id=&limit=&offset=` | `{checks: [{transaction, rule, agent, status, checked_at, details}]}` |
| GET | `/api/brokerage/compliance/summary` | Broker+ | Compliance summary (pass/fail counts, trend) | `?period=30d` | `{total, pass, fail, warning, overridden, trend_data[]}` |
| POST | `/api/brokerage/compliance/checks/:id/override` | Managing Broker | Override a failing check | `{reason}` | `{status: "overridden"}` |
| POST | `/api/brokerage/compliance/evaluate` | Managing Broker | Trigger on-demand compliance evaluation | `{transaction_id?}` | `{job_id, status: "queued"}` |

### 5.6 Invite Acceptance (Public)

| Method | Endpoint | Auth | Description | Query Params | Response |
|--------|----------|------|-------------|-------------|----------|
| GET | `/api/invites/:token` | None (public) | Validate an invite token | - | `{brokerage_name, role, email, is_valid, expires_at}` |
| POST | `/api/invites/:token/accept` | Authenticated user | Accept an invite and join the brokerage | - | `{brokerage_id, role, status: "accepted"}` |

### 5.7 Audit Log

| Method | Endpoint | Auth | Description | Query Params | Response |
|--------|----------|------|-------------|-------------|----------|
| GET | `/api/brokerage/audit-log` | Managing Broker | Browse audit log | `?action=&actor_id=&resource_type=&from=&to=&limit=&offset=` | `{entries: [{actor, action, resource, details, timestamp}]}` |
| GET | `/api/brokerage/audit-log/export` | Managing Broker | Export audit log as CSV | `?from=&to=` | CSV file download |

### 5.8 Middleware: BrokerageScope

A FastAPI dependency that injects scoping logic into every data-fetching endpoint.

```python
async def get_brokerage_scope(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BrokerageScope:
    """
    Returns a BrokerageScope object that provides query filters based on
    the current user's brokerage membership and role.

    Usage in endpoints:
        scope = Depends(get_brokerage_scope)
        query = select(Transaction).where(scope.transaction_filter())
    """
    membership = await get_user_brokerage_membership(db, current_user.id)

    if membership is None:
        # Individual agent with no brokerage — existing behavior
        return BrokerageScope(
            scope_type="agent",
            user_id=current_user.id
        )

    if membership.role in ("managing_broker", "broker"):
        # Broker-level: sees all transactions in the brokerage
        return BrokerageScope(
            scope_type="brokerage",
            brokerage_id=membership.brokerage_id,
            user_id=current_user.id,
            role=membership.role
        )

    if membership.role == "transaction_coordinator":
        # TC: sees only explicitly assigned transactions
        return BrokerageScope(
            scope_type="assigned",
            user_id=current_user.id,
            assigned_to=membership.assigned_to_agent_id
        )

    if membership.role == "assistant":
        # Assistant: read-only on assigned agent's transactions
        return BrokerageScope(
            scope_type="read_only_assigned",
            user_id=current_user.id,
            assigned_to=membership.assigned_to_agent_id
        )

    # Default: agent within a brokerage — sees only own transactions
    return BrokerageScope(
        scope_type="agent",
        user_id=current_user.id
    )
```

The `BrokerageScope` class provides the following methods:

```python
class BrokerageScope:
    def transaction_filter(self) -> ColumnElement:
        """Returns a SQLAlchemy WHERE clause for Transaction queries."""
        if self.scope_type == "brokerage":
            # Subquery: all user_ids in the brokerage
            agent_ids = select(BrokerageAgent.user_id).where(
                BrokerageAgent.brokerage_id == self.brokerage_id,
                BrokerageAgent.is_active == True
            )
            return Transaction.agent_id.in_(agent_ids)
        elif self.scope_type == "assigned":
            return Transaction.agent_id == self.assigned_to
        elif self.scope_type == "read_only_assigned":
            return Transaction.agent_id == self.assigned_to
        else:
            return Transaction.agent_id == self.user_id

    def can_write(self) -> bool:
        """Returns whether the current scope allows write operations."""
        return self.scope_type != "read_only_assigned"

    def commission_filter(self) -> ColumnElement:
        """Returns a filter for commission queries.
        Brokers see totals only, not individual split details."""
        ...

    def requires_audit_log(self) -> bool:
        """Returns True if the current user's access should be audited."""
        return self.scope_type == "brokerage"
```

---

## 6. Frontend Components

### 6.1 Broker Dashboard Page

**Route:** `/brokerage`
**Access:** `managing_broker`, `broker`
**Layout:** Full-width dashboard with summary cards at top, three-column body (activity feed, compliance, agent table), and pipeline chart at bottom.

**Components:**
- `BrokerageSummaryCards` — Six KPI cards (active transactions, pipeline value, compliance rate, active agents, closing this month, revenue YTD). Each card shows the current value and a delta vs. previous period.
- `BrokerageActivityFeed` — Scrollable list of recent actions. Each entry: avatar, agent name, action description, timestamp, and link to the relevant transaction. Filter dropdown for action type and agent.
- `ComplianceOverviewPanel` — Donut chart (recharts `PieChart`) showing pass/fail/warning/overridden distribution. Below the chart: list of failing checks with transaction address, rule name, agent name, and "View" link. "Override" button for managing brokers.
- `AgentPerformanceTable` — Sortable data table using `@tanstack/react-table`. Columns: agent name (linked), active deals, pipeline value ($), avg days-to-close, compliance score (color-coded), last active. Row click navigates to agent detail.
- `BrokeragePipelineChart` — Stacked bar chart (recharts `BarChart`) showing monthly revenue forecast aggregated across all agents. Bars segmented by confidence level (high/medium/low).

### 6.2 Agent Management Page

**Route:** `/brokerage/agents`
**Access:** `managing_broker`, `broker` (read-only for broker)
**Layout:** Two-column: agent list/table on the left (70%), action panel on the right (30%).

**Components:**
- `AgentListTable` — Full agent roster with columns: name, email, role, status (active/inactive), joined date, active deals, compliance score. Row actions: edit role, deactivate, view detail.
- `InviteAgentModal` — Modal form with email input and role selector. "Send Invite" button. Shows confirmation with invite details.
- `BulkInviteModal` — Modal with CSV upload zone (drag-and-drop), preview of parsed rows, validation errors highlighted in red, and "Send All Invites" button.
- `PendingInvitesPanel` — Table of pending invites with columns: email, role, sent date, expires date, status. Actions: resend, revoke.
- `AgentDetailDrawer` — Slide-over drawer showing full agent detail: profile info, performance metrics, active transactions list, compliance check results, and recent activity.
- `ChangeRoleDialog` — Confirmation dialog for role changes with role selector and explanation of permission changes.
- `DeactivateAgentDialog` — Confirmation dialog listing the agent's active transactions with option to transfer them to another agent.
- `TransferTransactionModal` — Modal showing the transaction details and a searchable dropdown of agents in the brokerage. Requires a transfer reason selection.

### 6.3 Compliance Monitoring Page

**Route:** `/brokerage/compliance`
**Access:** `managing_broker`, `broker`
**Layout:** Tabs: "Dashboard", "Rules", "Checks".

**Tab: Dashboard**
- `ComplianceSummaryCards` — Four cards: total checks, pass rate (%), failing checks count, overridden count.
- `ComplianceTrendChart` — Line chart (recharts `LineChart`) showing compliance pass rate over the selected period (30/60/90 days).
- `FailingChecksList` — Grouped by compliance rule. Each group shows the rule name, severity badge, and a list of failing transactions with agent name, transaction address, and days since failure.

**Tab: Rules**
- `ComplianceRulesList` — Table of all rules with columns: name, type, severity, status (active/inactive), created by, created date. Row actions: edit, toggle active, delete.
- `CreateRuleModal` — Step-by-step rule creation: (1) select rule type from cards with descriptions, (2) configure parameters (form fields change based on type), (3) set severity and name, (4) preview which existing transactions would pass/fail, (5) confirm.
- `EditRuleDrawer` — Slide-over form for editing rule parameters with live impact preview.

**Tab: Checks**
- `ComplianceChecksTable` — Filterable table of all check results. Columns: transaction, rule, agent, status (color-coded badge), checked date, details. Filters: status, agent, rule, date range. "Override" button on failing checks (managing broker only).
- `OverrideDialog` — Modal requiring a reason (text input, minimum 20 characters). Shows the check details and rule being overridden.

### 6.4 Brokerage Settings Page

**Route:** `/brokerage/settings`
**Access:** `managing_broker`
**Layout:** Vertical sections with save buttons per section.

**Sections:**
- `BrokerageProfileForm` — Name, address, phone, website, license number. Standard form fields with validation.
- `BrandingSection` — Logo upload (drag-and-drop with preview), primary color picker, secondary color picker, email header/footer HTML editors (simple textarea with preview), "Enforce brokerage branding" toggle with explanation.
- `BillingSection` — Display current billing type, agent seat count, and placeholder for Stripe integration. "Contact us to change your plan" link.
- `ComplianceDefaultsSection` — Quick-setup section showing recommended compliance rules for the brokerage's state. Checkboxes to enable/disable each default rule. "Apply Selected" button creates the rules.

### 6.5 Navigation Updates

The main navigation (`Layout.tsx`) is updated based on the user's role:

- **Individual agent (no brokerage):** No changes. Existing nav items: Today View, Transactions, Pipeline, Documents, Settings.
- **Agent within a brokerage:** Same as individual agent. No brokerage nav items. The agent's experience is unchanged.
- **Broker / Managing Broker:** Additional nav section "Brokerage" with sub-items: Dashboard, Agents, Compliance, Settings. This section appears above the personal section in the sidebar.
- **Transaction Coordinator:** Nav items: Assigned Transactions, Documents. No brokerage admin items.
- **Assistant:** Nav items: Assigned Transactions (read-only). Minimal nav.

### 6.6 Invite Acceptance Page

**Route:** `/invite/:token`
**Access:** Public (unauthenticated or authenticated)
**Layout:** Centered card.

**Components:**
- `InviteAcceptanceCard` — Shows brokerage name, brokerage logo, invited role, and two CTAs:
  - If authenticated: "Join [Brokerage Name]" button that calls POST `/api/invites/:token/accept`.
  - If not authenticated: "Sign Up to Join" button that redirects to sign-up flow with `?invite_token=` query parameter. After sign-up, auto-accepts the invite.
  - If invite is expired/revoked/already accepted: appropriate error message with "Contact your broker" fallback.

### 6.7 Agent Detail Page

**Route:** `/brokerage/agents/:id`
**Access:** `managing_broker`, `broker`
**Layout:** Full page with tabbed content.

**Tabs:**
- **Overview** — Profile card (name, email, phone, license, role, joined date, last active), performance metrics summary cards (active deals, pipeline value, revenue YTD, compliance score, avg days-to-close), and performance trend sparklines for the last 6 months.
- **Transactions** — Table of the agent's transactions with columns: property address, status (badge), purchase price, closing date, health score (color-coded), commission. Click to open transaction detail. Filters: status, date range.
- **Compliance** — Table of compliance checks for this agent's transactions. Grouped by status (failing first). Each row: rule name, transaction address, status, checked date, details. Override button for managing broker.
- **Activity** — Timeline of the agent's recent actions: transactions created, milestones completed, documents generated, emails sent. Filterable by action type. Paginated.
- **History** — Closed and lost transactions in the last 12 months. Revenue summary: total closed, total lost, conversion rate.

---

## 7. Definition of Success

| # | Criteria | Verification |
|---|----------|-------------|
| 1 | A managing broker can create a brokerage and become the managing_broker | Create brokerage via API; verify brokerage record and brokerage_agents record with role = managing_broker |
| 2 | Inviting an agent sends an email with a valid invite link; the agent can accept and join | Invite agent; verify email sent via Resend; click invite link; accept; verify brokerage_agents record created with correct role |
| 3 | Bulk CSV invite processes 50 agents correctly | Upload CSV with 50 rows; verify 50 invites created; verify summary (sent/skipped) is accurate |
| 4 | Agents within a brokerage see only their own transactions — no data leakage | Create two agents in same brokerage with different transactions; verify agent A's GET /transactions does NOT return agent B's transactions |
| 5 | Brokers see all transactions across the brokerage | Create broker user; verify GET /transactions returns all agents' transactions scoped to the brokerage |
| 6 | Role-based access control prevents unauthorized actions | Attempt role change as agent (should 403); attempt compliance rule creation as broker (should 403); attempt audit log access as broker (should 403) |
| 7 | Transaction transfer changes ownership and notifies all parties | Transfer transaction from agent A to agent B; verify agent_id changed; verify transfer logged; verify notification emails sent to both agents and all parties |
| 8 | Compliance rules evaluate correctly against transactions | Create "Agency Disclosure within 3 days" rule; create transaction without the milestone; verify compliance check = fail; add and complete the milestone; re-evaluate; verify check = pass |
| 9 | Compliance dashboard shows accurate aggregate data | Create 10 transactions with mixed compliance results; verify pass rate, failing count, and trend data match manual calculation |
| 10 | Managing broker can override a failing compliance check with a reason | Override a failing check; verify status changed to overridden; verify reason stored; verify audit log entry created |
| 11 | Agent performance snapshots compute correctly | Create agent with known transaction data; run snapshot task; verify all 12 metrics match manual calculation |
| 12 | Broker dashboard displays correct aggregate metrics | Create brokerage with 3 agents and known data; verify dashboard summary cards (total transactions, pipeline value, compliance rate, revenue) match expected values |
| 13 | Brokerage branding cascades to generated documents | Configure brokerage branding with logo and enforce flag; agent generates document; verify brokerage logo and colors appear on PDF |
| 14 | Agent deactivation prevents brokerage access but preserves data | Deactivate agent; verify agent cannot access brokerage endpoints; verify broker still sees agent's historical transactions |
| 15 | Existing individual agents (no brokerage) are completely unaffected | Run full Phase 1-6 test suite with a non-brokerage user; verify zero regressions |
| 16 | Audit log records all brokerage-level actions | Perform invite, role change, transfer, compliance override, branding update; verify each action has a corresponding audit log entry with correct actor and details |
| 17 | Invite expiration and revocation work correctly | Create invite; advance time past 14 days; verify acceptance returns error. Create invite; revoke it; verify acceptance returns error |
| 18 | Cross-brokerage data isolation is enforced | Create two brokerages; verify broker A cannot access any data from brokerage B through any endpoint |

---

## 8. Regression Test Plan

### 8.1 Phase 7 New Tests (22 tests)

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P7-T01 | Create brokerage and verify managing_broker role assigned | Brokerage created; creator has managing_broker role in brokerage_agents |
| P7-T02 | Invite agent via email; accept invite; verify membership | Invite sent; token valid; acceptance creates brokerage_agents record with agent role |
| P7-T03 | Invite agent with existing Armistead account; verify no duplicate user created | Existing user linked to brokerage; no new user record |
| P7-T04 | Bulk CSV invite with 10 valid and 2 duplicate emails | 10 invites sent; 2 skipped with "already member" message |
| P7-T05 | Agent data isolation: agent A cannot see agent B transactions | GET /transactions for agent A returns only agent A's transactions; agent B's transaction ID returns 404 |
| P7-T06 | Broker scope: broker sees all brokerage transactions | GET /transactions for broker returns transactions from all agents in the brokerage |
| P7-T07 | Cross-brokerage isolation: broker A cannot see brokerage B data | Broker A requests transaction belonging to brokerage B; returns 404 |
| P7-T08 | Role escalation prevention: agent cannot change own role | PATCH /brokerage/agents/:self/role returns 403 |
| P7-T09 | Managing broker can change agent to broker role | PATCH role to "broker"; verify brokerage_agents.role updated; audit log entry created |
| P7-T10 | Transaction transfer updates agent_id and creates audit record | POST transfer; verify transaction.agent_id changed; agent_transfers record created; notifications sent |
| P7-T11 | Transaction transfer preserves historical communications | After transfer; verify old communications still attributed to original agent |
| P7-T12 | Compliance rule: milestone_deadline evaluates pass/fail correctly | Create rule requiring milestone within 5 days; transaction with milestone completed in 3 days = pass; 7 days = fail |
| P7-T13 | Compliance rule: required_party evaluates correctly | Create rule requiring "title_company" party; transaction with party = pass; without = fail |
| P7-T14 | Compliance rule: required_document evaluates correctly | Create rule requiring "disclosure" document within 7 days; file uploaded in 5 days = pass; no file = fail |
| P7-T15 | Compliance override requires reason and logs to audit | Override without reason returns 400; override with reason succeeds; audit log entry created |
| P7-T16 | Nightly compliance evaluation task processes all active transactions | Run task; verify all active transactions have compliance_checks for all active rules |
| P7-T17 | Agent performance snapshot calculates all 12 metrics accurately | Seed agent with known data; run snapshot; verify each metric value matches manual calculation |
| P7-T18 | Broker dashboard summary cards return correct aggregate values | Seed brokerage with known data; GET /brokerage/dashboard; verify all summary values |
| P7-T19 | Agent deactivation sets is_active=false and flags transactions | Deactivate agent; verify is_active=false and deactivated_at set; verify active transactions flagged for transfer |
| P7-T20 | Invite expiration: accept expired invite returns error | Create invite; set expires_at to past; attempt accept; verify 400 response |
| P7-T21 | Brokerage branding enforced on generated documents | Set enforce_brokerage_branding=true; agent generates document; verify brokerage logo appears (not agent logo) |
| P7-T22 | Audit log export produces valid CSV with all expected entries | Perform 5 audited actions; export CSV; verify 5 rows with correct columns |

### 8.2 Phase 1-6 Regression Tests (16 tests)

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P7-R01 | Individual agent (no brokerage) creates transaction | Transaction created successfully; no brokerage-related errors |
| P7-R02 | Individual agent Today View loads with all sections | Today View renders overdue, due today, coming up, this week sections |
| P7-R03 | Individual agent milestone template application works | Apply template; milestones created with correct dates |
| P7-R04 | Individual agent transaction health score calculates | Health score endpoint returns valid 0-100 score |
| P7-R05 | Individual agent email generation and sending works (Phase 2) | Generate email; send via Resend; verify delivery and communication log |
| P7-R06 | Individual agent notification rules fire correctly (Phase 2) | Create overdue milestone; verify nudge email generated and sent |
| P7-R07 | Party portal unique links work for non-brokerage transactions (Phase 3) | Generate portal link; access portal; verify party sees correct data |
| P7-R08 | AI Transaction Advisor works for non-brokerage agent (Phase 4) | Send query to advisor; receive contextual response |
| P7-R09 | Inspection analysis works for non-brokerage agent (Phase 4) | Upload inspection report; verify findings extracted |
| P7-R10 | Commission tracking works for non-brokerage agent (Phase 5) | Configure commission; create transaction; verify commission calculated |
| P7-R11 | Pipeline dashboard works for non-brokerage agent (Phase 5) | Verify pipeline totals, forecast, and at-risk display correctly |
| P7-R12 | Document generation works for non-brokerage agent (Phase 6) | Generate repair letter; verify PDF renders with agent branding |
| P7-R13 | Agent within brokerage can use all Phase 1-6 features on own transactions | Agent in brokerage creates transaction, applies template, generates email, tracks commission, generates document; all work |
| P7-R14 | Brokerage agent's generated documents use correct branding cascade | Agent with own branding + brokerage branding (not enforced); verify agent branding used. Toggle enforce; verify brokerage branding used |
| P7-R15 | Commission data visibility: broker sees totals but not split details | Broker GET /brokerage/agents includes revenue_ytd but not individual commission split line items |
| P7-R16 | Existing API endpoints return 200 for non-brokerage users without new required fields | Hit every Phase 1-6 endpoint with non-brokerage user; verify no 500 or 422 errors from missing brokerage context |

---

## 9. Implementation Order

### Week 18: Data Model, RBAC, and Multi-Tenancy Foundation

| Day | Tasks | Files |
|-----|-------|-------|
| Mon | Create Alembic migration 7a: `brokerages`, `brokerage_agents`, `brokerage_invites` tables. SQLAlchemy models for all three. Add `brokerage_membership` relationship to User model. | `backend/alembic/versions/007a_brokerage_tables.py`, `backend/app/models/brokerage.py`, `backend/app/models/brokerage_agent.py`, `backend/app/models/brokerage_invite.py`, `backend/app/models/user.py` (modify), `backend/app/models/__init__.py` (modify) |
| Tue | Create Alembic migration 7b: `compliance_rules`, `compliance_checks` tables. SQLAlchemy models. Add `compliance_checks` relationship to Transaction model. | `backend/alembic/versions/007b_compliance_tables.py`, `backend/app/models/compliance_rule.py`, `backend/app/models/compliance_check.py`, `backend/app/models/transaction.py` (modify) |
| Wed | Create Alembic migration 7c: `agent_performance_snapshots`, `agent_transfers`, `brokerage_audit_log` tables. SQLAlchemy models. | `backend/alembic/versions/007c_performance_audit_tables.py`, `backend/app/models/agent_performance_snapshot.py`, `backend/app/models/agent_transfer.py`, `backend/app/models/brokerage_audit_log.py` |
| Thu | Implement `BrokerageScope` middleware and `require_role()` dependency. Write scope filter logic for all five roles. Unit test scope filtering with mock data. | `backend/app/middleware/brokerage_scope.py`, `backend/app/dependencies/auth.py` (modify), `backend/tests/test_brokerage_scope.py` |
| Fri | Retrofit existing endpoints (transactions, milestones, parties, files, communications) to use `BrokerageScope`. Verify backward compatibility for non-brokerage users. | `backend/app/api/transactions.py` (modify), `backend/app/api/parties.py` (modify), `backend/app/api/milestones.py` (modify), `backend/app/api/files.py` (modify), `backend/tests/test_scope_backward_compat.py` |

### Week 19: Brokerage CRUD, Team Management, and Invites

| Day | Tasks | Files |
|-----|-------|-------|
| Mon | Brokerage CRUD endpoints: create, get, update, branding upload. Pydantic schemas for brokerage. | `backend/app/api/brokerage.py`, `backend/app/schemas/brokerage.py`, `backend/app/services/brokerage_service.py` |
| Tue | Agent invite system: single invite, bulk CSV, accept, resend, revoke. Invite email template via Resend. Token generation and validation. | `backend/app/api/brokerage_agents.py`, `backend/app/services/invite_service.py`, `backend/app/services/email_templates/invite.html` |
| Wed | Agent management endpoints: list with performance, change role, deactivate, reactivate. Audit log service for all brokerage actions. | `backend/app/api/brokerage_agents.py` (extend), `backend/app/services/audit_service.py`, `backend/app/schemas/brokerage_agent.py` |
| Thu | Transaction transfer service: change agent_id, create transfer record, send notifications, update notification rules. Transfer API endpoint. | `backend/app/services/transfer_service.py`, `backend/app/api/brokerage_transfers.py`, `backend/app/schemas/transfer.py` |
| Fri | Audit log endpoints: browse with filters, CSV export. Pydantic schemas for audit entries. Integration tests for all team management features. | `backend/app/api/brokerage_audit.py`, `backend/app/schemas/audit.py`, `backend/tests/test_team_management.py` |

### Week 20: Compliance Engine and Performance Metrics

| Day | Tasks | Files |
|-----|-------|-------|
| Mon | Compliance rule CRUD endpoints. Compliance rule evaluation engine: implement check functions for all 6 rule types. | `backend/app/api/compliance.py`, `backend/app/services/compliance_service.py`, `backend/app/services/compliance_checks/milestone_deadline.py`, `backend/app/services/compliance_checks/required_party.py`, `backend/app/services/compliance_checks/required_document.py`, `backend/app/services/compliance_checks/required_communication.py`, `backend/app/services/compliance_checks/health_score_min.py`, `backend/app/services/compliance_checks/closing_date_required.py` |
| Tue | Compliance evaluation orchestrator: evaluate single transaction, evaluate all transactions, nightly batch task (Celery beat). Event-driven re-evaluation on transaction updates. | `backend/app/services/compliance_evaluator.py`, `backend/app/tasks/compliance_tasks.py`, `backend/app/tasks/celery_beat_schedule.py` (modify) |
| Wed | Compliance check override endpoint. Compliance summary and dashboard endpoints. Compliance trend data calculation. | `backend/app/api/compliance.py` (extend), `backend/app/services/compliance_summary_service.py` |
| Thu | Agent performance snapshot computation: Celery task that calculates all 12 metrics per agent. Schedule as nightly task. On-demand refresh endpoint. | `backend/app/services/performance_service.py`, `backend/app/tasks/performance_tasks.py`, `backend/app/api/brokerage_agents.py` (extend) |
| Fri | Broker dashboard API endpoint: aggregate summary cards, pipeline by month, compliance overview. Integration tests for compliance and performance. | `backend/app/api/brokerage_dashboard.py`, `backend/app/services/dashboard_service.py`, `backend/tests/test_compliance.py`, `backend/tests/test_performance.py` |

### Week 21: Frontend — Broker Dashboard, Agent Management, Compliance

| Day | Tasks | Files |
|-----|-------|-------|
| Mon | Broker dashboard page: summary cards, activity feed, compliance overview panel. API hooks for dashboard data. | `frontend/src/pages/Brokerage/Dashboard.tsx`, `frontend/src/components/brokerage/BrokerageSummaryCards.tsx`, `frontend/src/components/brokerage/BrokerageActivityFeed.tsx`, `frontend/src/components/brokerage/ComplianceOverviewPanel.tsx`, `frontend/src/lib/api.ts` (extend) |
| Tue | Broker dashboard continued: agent performance table, pipeline chart. Sortable table with @tanstack/react-table. Recharts pipeline visualization. | `frontend/src/components/brokerage/AgentPerformanceTable.tsx`, `frontend/src/components/brokerage/BrokeragePipelineChart.tsx` |
| Wed | Agent management page: agent list table, invite modal, bulk invite modal, pending invites panel. Change role and deactivate dialogs. | `frontend/src/pages/Brokerage/AgentManagement.tsx`, `frontend/src/components/brokerage/InviteAgentModal.tsx`, `frontend/src/components/brokerage/BulkInviteModal.tsx`, `frontend/src/components/brokerage/PendingInvitesPanel.tsx`, `frontend/src/components/brokerage/ChangeRoleDialog.tsx`, `frontend/src/components/brokerage/DeactivateAgentDialog.tsx` |
| Thu | Compliance monitoring page: three tabs (Dashboard, Rules, Checks). Compliance trend chart, failing checks list, rule creation modal, override dialog. | `frontend/src/pages/Brokerage/Compliance.tsx`, `frontend/src/components/brokerage/ComplianceTrendChart.tsx`, `frontend/src/components/brokerage/CreateRuleModal.tsx`, `frontend/src/components/brokerage/ComplianceChecksTable.tsx`, `frontend/src/components/brokerage/OverrideDialog.tsx` |
| Fri | Agent detail drawer/page. Transfer transaction modal. Navigation updates based on role. Invite acceptance page. | `frontend/src/components/brokerage/AgentDetailDrawer.tsx`, `frontend/src/components/brokerage/TransferTransactionModal.tsx`, `frontend/src/components/Layout.tsx` (modify), `frontend/src/pages/InviteAcceptance.tsx`, `frontend/src/App.tsx` (modify routes) |

### Week 22: Branding, Integration Testing, Polish

| Day | Tasks | Files |
|-----|-------|-------|
| Mon | Brokerage settings page: profile form, branding section (logo upload, color pickers, email HTML editors), enforce branding toggle. | `frontend/src/pages/Brokerage/Settings.tsx`, `frontend/src/components/brokerage/BrandingSection.tsx`, `frontend/src/components/brokerage/BrokerageProfileForm.tsx` |
| Tue | Modify Phase 6 document generation to respect brokerage branding cascade. Update Phase 2 email sending to include brokerage email header/footer. | `backend/app/services/document_generation_service.py` (modify), `backend/app/services/email_service.py` (modify), `backend/tests/test_branding_cascade.py` |
| Wed | End-to-end integration testing: create brokerage, invite 5 agents, create transactions as agents, verify broker dashboard data, run compliance evaluation, test transfers. | `backend/tests/e2e/test_brokerage_e2e.py`, `frontend/cypress/e2e/brokerage.cy.ts` (if Cypress is used) |
| Thu | Full Phase 1-6 regression test suite execution for non-brokerage users. Fix any regressions. Cross-brokerage isolation testing. | `backend/tests/regression/test_phase1_regression.py` through `backend/tests/regression/test_phase6_regression.py` |
| Fri | Performance testing for broker dashboard with 50+ agents and 500+ transactions. Query optimization (indexes, eager loading). Bug fixes. | `backend/alembic/versions/007d_performance_indexes.py`, `backend/app/api/brokerage_dashboard.py` (optimize) |

---

## 10. Dependencies

### 10.1 Phase Dependencies

| Dependency | Requirement | Impact if Missing |
|------------|-------------|-------------------|
| Phase 1 Complete | Transaction model, milestone model, health score calculation, Today View | Brokerage dashboard cannot aggregate transaction data or health scores |
| Phase 2 Complete | Email sending via Resend, communication model, notification rules | Invite emails cannot be sent; compliance rules checking communications fail; brokerage email header/footer injection impossible |
| Phase 3 Complete | Party model, portal tokens | Compliance rules checking required parties fail; party notifications during transfer fail |
| Phase 4 Complete | AI insights, inspection analysis | Compliance rules checking documents fail; broker-wide AI advisor context unavailable |
| Phase 5 Complete | Commission model, pipeline forecasting, revenue calculations | Broker dashboard pipeline/revenue cards empty; agent performance revenue metrics unavailable |
| Phase 6 Complete | Document generation, agent branding, weasyprint pipeline | Brokerage branding cascade cannot override agent branding on documents; generated documents referenced in compliance checks unavailable |

### 10.2 Infrastructure Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Celery Beat | Nightly compliance evaluation and performance snapshot tasks | Already configured from Phase 2. Add new periodic tasks to the beat schedule. |
| Resend | Invite emails, transfer notifications | Already configured from Phase 2. New email templates for invites and transfers. |
| MinIO | Brokerage logo storage, CSV import temp files | Already configured from Phase 1. New bucket path: `/brokerages/{id}/`. |
| Redis | Celery broker, potential caching for dashboard aggregates | Already configured. Consider caching dashboard endpoint responses for 5 minutes to reduce database load. |
| PostgreSQL indexes | Performance for brokerage-scoped queries | New indexes needed: `brokerage_agents(brokerage_id, is_active)`, `compliance_checks(transaction_id, rule_id)`, `agent_performance_snapshots(agent_id, snapshot_date)`, `brokerage_audit_log(brokerage_id, created_at)`. |

### 10.3 Frontend Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| @tanstack/react-table | Sortable, filterable data tables for agent list, compliance checks, audit log | May already be installed; if not, add to package.json |
| recharts | Charts for compliance trend, pipeline forecast, performance trends | Already available from Phase 5 pipeline dashboard |
| react-colorful or similar | Color picker for brokerage branding primary/secondary colors | New dependency; lightweight (< 5kb) |
| papaparse | CSV parsing for bulk agent invite | New dependency for client-side CSV parsing |

### 10.4 Data Migration Considerations

No data migration is required for existing users. All new tables are additive. The key architectural decision is that `brokerage_id` is NOT added as a column to the `transactions` table. Instead, brokerage scoping is derived through the `brokerage_agents` join table: a transaction belongs to a brokerage because its `agent_id` maps to a user who has a `brokerage_agents` record. This means:

- No existing table is modified (except adding relationships to User and Transaction models).
- No existing row is updated.
- Zero-downtime deployment is possible.
- An agent who leaves a brokerage retains their transactions (the join path breaks when `is_active = false`, but the broker retains read-only access via the date range check described in CoV #4).

---

*Phase 7 Complete -> Armistead RE Brokerage Platform is live. Proceed to pricing, onboarding playbook, and sales.*
