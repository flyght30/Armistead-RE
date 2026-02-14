# Phase 5: Money — Commission Tracking, Pipeline Forecasting & Revenue Intelligence

**Timeline:** Weeks 13-14
**Status:** Not Started
**Depends On:** Phase 4 Complete
**CoV Status:** Verified (see below)

---

## 1. Phase Overview

Build the financial layer that tracks commission per transaction, models team splits and referral fees, forecasts pipeline revenue based on projected closing dates, and surfaces revenue-at-risk from overdue or troubled deals. This transforms Armistead from a transaction management tool into a business intelligence platform.

**Deliverable:** Every transaction carries commission data (gross, splits, net). The agent sees a pipeline dashboard showing total projected revenue, monthly forecasts, at-risk revenue, and a breakdown by transaction status. Commission configurations are saved per agent with support for default rates, broker splits, team splits, and referral fees.

---

## 2. Scope

### In Scope
- Commission configuration (default rates, broker split, team splits, referral fees)
- Per-transaction commission tracking (gross, splits, net to agent)
- Commission types: flat fee and percentage
- Commission recalculation on price changes (amendments)
- Projected vs. actual commission (pre-closing vs. post-closing)
- Pipeline dashboard (total value, monthly forecast, at-risk)
- Revenue at risk (overdue deals multiplied by their commission value)
- Dual agency commission handling
- Commission export (CSV for tax/bookkeeping)
- Commission summary per transaction on detail page

### Out of Scope (This Phase)
- 1099 generation or tax filing integration
- Brokerage-level commission aggregation (Phase 7)
- Integration with accounting software (QuickBooks, etc.)
- Historical market comparison
- Commission disputes/arbitration workflow

---

## 3. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-5.1 | As an agent, I can configure my default commission rates | Settings page with default percentage rate, flat fee option, broker split percentage, and team split rules |
| US-5.2 | As an agent, each transaction shows commission breakdown | Transaction detail displays gross commission, broker split, team split, referral fee, and net to agent |
| US-5.3 | As an agent, I can override commission on a per-transaction basis | Edit commission fields on any transaction; overrides persist and do not affect defaults |
| US-5.4 | As an agent, commission recalculates when price changes | Amending purchase price triggers commission recalculation with agent confirmation |
| US-5.5 | As an agent, I see projected vs. actual commission | Before closing: "projected"; after closing: "actual"; clear visual distinction |
| US-5.6 | As an agent, I see a pipeline dashboard with total projected revenue | Dashboard card showing total pipeline value, number of active deals, average commission |
| US-5.7 | As an agent, I see monthly revenue forecasts based on projected closing dates | Bar chart or table showing expected revenue per month based on closing dates |
| US-5.8 | As an agent, I see revenue at risk from overdue or troubled deals | Highlight transactions with overdue milestones and their associated commission value |
| US-5.9 | As an agent, I can handle team splits and referral fees | Add team members with split percentages; add referral fee as flat or percentage |
| US-5.10 | As an agent, I can export commission data as CSV | Export button generates CSV with all transactions, commission amounts, and status |
| US-5.11 | As an agent, dual agency transactions calculate commission correctly | Both sides of commission shown; proper split applied |
| US-5.12 | As an agent, deals that fall through show lost revenue in reports | Cancelled/terminated transactions appear in a "lost revenue" section with their commission value |

---

## 4. Chain-of-Verification: Phase 5

### Step 1: Baseline
Phase 5 adds commission tracking per transaction, pipeline revenue forecasting, at-risk revenue calculations, and configurable commission structures including splits and referral fees.

### Step 2: Self-Questioning

**Q1:** What about different commission structures (flat fee vs. percentage)?
**Q2:** How do we handle team splits and referral fees?
**Q3:** What if commission changes mid-transaction (price reduction via amendment)?
**Q4:** What about commission not paid until after closing — projected vs. actual?
**Q5:** Tax implications — should we track 1099 data?
**Q6:** Privacy — should other agents on a brokerage see each other's commissions?
**Q7:** What about commission disputes between cooperating agents?
**Q8:** How accurate are forecasts based on projected closing dates?
**Q9:** What about deals that fall through — how do we handle lost revenue?
**Q10:** What about dual agency commission handling?
**Q11:** What about variable commission rates on the same transaction (e.g., 3% on first $500k, 2% on amount above)?
**Q12:** What about commission advances or draws against future commissions?

### Step 3: Independent Verification

**A1 — Flat Fee vs. Percentage:** Agents work under different compensation models. Some charge a flat fee per transaction, others a percentage of sale price, and some use tiered percentages. The commission_configs table must support a `commission_type` enum (`percentage`, `flat`, `tiered`) with appropriate fields for each. On each transaction, the system calculates based on the configured type. The agent can always override the calculated amount.
**Resolution:** Support `percentage`, `flat`, and `tiered` commission types. Percentage is the default. Agent can override per transaction. Calculated values are suggestions, not locked.

**A2 — Team Splits and Referral Fees:** An agent's gross commission is often split further: broker takes a cut (e.g., 30%), team lead takes a cut, or a referral fee is owed to another agent. The `transaction_commissions` table stores each split as a line item: `split_type` (broker, team, referral), `recipient_name`, `amount_or_percentage`, `calculated_amount`. The net to agent is gross minus all splits.
**Resolution:** Commission splits stored as line items in `commission_splits` table. Each has a type, recipient, and amount. Net = gross - sum(splits). Support both percentage-of-gross and flat-amount splits.

**A3 — Mid-Transaction Commission Changes:** If the purchase price changes (via amendment), the percentage-based commission changes. The system should detect price amendments and prompt: "Purchase price changed from $X to $Y. Commission will change from $A to $B. Update?" The agent confirms or manually overrides. If the agent previously set a manual override (flat amount), the system should not auto-recalculate.
**Resolution:** Listen for purchase_price amendment events. If commission is percentage-based and not manually overridden, recalculate and prompt for confirmation. Manual overrides are never auto-changed.

**A4 — Projected vs. Actual:** Until a deal closes, commission is "projected." After closing, it becomes "actual" (and may differ if there were last-minute credits or adjustments). The `transaction_commissions` table has both `projected_amount` and `actual_amount` fields. Before closing, `actual_amount` is null. After closing, the agent can enter the actual received amount, and the system tracks the delta.
**Resolution:** Two amount fields: projected (auto-calculated) and actual (entered post-closing). Dashboard uses projected for open deals, actual for closed deals. Delta report shows variance.

**A5 — Tax / 1099 Data:** Full 1099 generation is out of scope, but we should track enough data to make tax time easier: total commissions received per year, per transaction. The CSV export should be sufficient for an agent to hand to their accountant. We will NOT store SSN/TIN data — that is a liability we do not need.
**Resolution:** No SSN/TIN storage. Annual summary exportable as CSV. Enough data for accountant handoff. Full 1099 generation is a future feature if demand exists.

**A6 — Privacy Between Agents:** In a single-agent system (current), this is not an issue. In Phase 7 (brokerage), commission visibility becomes critical. For now, all commission data is scoped to the authenticated agent. Phase 7 will add broker-level visibility with agent consent controls.
**Resolution:** Commission data scoped to agent_id via existing auth isolation. Phase 7 will add brokerage-level access controls with configurable visibility.

**A7 — Commission Disputes:** Disputes between cooperating agents are handled outside this system (via MLS arbitration, broker negotiation, etc.). The system should track the commission as agreed in the contract. If a dispute arises, the agent can add a note or flag the transaction, but we do not build a dispute resolution workflow.
**Resolution:** Out of scope for automated resolution. Agent can add notes/flags to any commission record. The system tracks what was agreed and what was paid.

**A8 — Forecast Accuracy:** Forecasts are only as good as the closing dates. Historically, about 20-30% of real estate deals have closing date extensions. The forecast should show a "confidence band" — transactions closer to closing are more reliable than those 60+ days out. Transactions with overdue milestones get a risk flag that reduces their forecast weight.
**Resolution:** Monthly forecast with confidence weighting. Deals within 30 days: high confidence. 30-60 days: medium. 60+ days: low. Overdue milestones reduce confidence. Pipeline dashboard shows "expected" and "at-risk" columns.

**A9 — Lost Revenue from Failed Deals:** When a transaction is cancelled or terminated, its projected commission should move from "pipeline" to "lost." The dashboard should show: (1) current pipeline, (2) closed/won this year, (3) lost this year. This gives the agent a realistic view of their conversion rate and revenue trajectory.
**Resolution:** Transaction status `cancelled` or `terminated` moves commission to "lost revenue" bucket. Dashboard shows pipeline, won, and lost totals. Year-to-date and month-to-date views.

**A10 — Dual Agency:** In dual agency, the agent represents both buyer and seller. The commission may be the full amount (buyer side + seller side) or a reduced total. The system should allow dual-agency transactions to specify total commission and how it splits (since there is no cooperating agent). Broker split and team splits still apply to the full amount.
**Resolution:** Dual agency uses `total_commission` field instead of `buyer_side` / `seller_side`. The agent enters the total agreed amount. Splits apply to the total. The system flags dual-agency transactions distinctly in reporting.

**A11 — Variable/Tiered Rates:** Some agents negotiate tiered rates (e.g., 3% on first $500k, 2% above). The `tiered` commission type stores an array of tiers: `[{up_to: 500000, rate: 0.03}, {up_to: null, rate: 0.02}]`. The calculation engine iterates through tiers to compute the gross. This is a power-user feature; most agents will use simple percentage.
**Resolution:** Tiered type supported in commission_configs with a JSON array of tier brackets. Calculation engine handles tier math. UI shows a simple "add tier" interface.

**A12 — Commission Advances:** Some agents take advances against future commissions (from their broker or a factoring company). This is a financial arrangement outside the transaction itself. We will NOT track advances or draws — that is brokerage accounting, not transaction management.
**Resolution:** Out of scope. Advances and draws are brokerage-level financial operations (potentially Phase 7 or beyond).

### Step 4: Confidence Check
**Confidence: 94%** — The core commission tracking and pipeline features are well-defined. The main risk is edge cases around tiered commissions and mid-transaction recalculations, but the agent-in-the-loop override pattern handles these safely.

### Step 5: Implement
Proceed with Phase 5. Focus on percentage-based commissions first (covers 90% of agents), add flat and tiered as configuration options. Projected vs. actual and lost revenue tracking are the key differentiators.

---

## 5. Detailed Requirements

### 5.1 Commission Configuration

The agent configures default commission settings that apply to new transactions:

- **Default commission rate:** Percentage (e.g., 3.0%) or flat fee (e.g., $5,000)
- **Broker split:** Percentage of gross that goes to the brokerage (e.g., 30%)
- **Team splits:** Array of named team members with their split percentage or flat amount
- **Referral fee default:** Optional default referral fee percentage

These defaults pre-populate when a new transaction is created, but every field is overridable per transaction.

### 5.2 Per-Transaction Commission Tracking

Each transaction has:
- **Gross commission:** Calculated from purchase price and rate, or flat amount
- **Commission splits:** Line items for broker, team members, referral fees
- **Net to agent:** Gross minus all splits
- **Projected amount:** Auto-calculated; used before closing
- **Actual amount:** Entered by agent after closing; used in closed reports
- **Status:** `projected` | `pending_close` | `received` | `disputed`

### 5.3 Pipeline Dashboard

The pipeline dashboard shows:
- **Total pipeline value:** Sum of projected commissions for all active transactions
- **Monthly forecast:** Bar chart of expected net commission by month (based on closing dates)
- **At-risk revenue:** Sum of commissions for transactions with overdue milestones
- **Closed/won YTD:** Sum of actual commissions received this year
- **Lost YTD:** Sum of projected commissions from cancelled/terminated transactions
- **Average commission:** Mean net commission across closed transactions
- **Conversion rate:** Closed deals / (Closed + Lost) as a percentage

### 5.4 Revenue at Risk

Revenue at risk is calculated as:
```
at_risk_revenue = SUM(projected_net_commission)
  WHERE transaction.status = 'active'
  AND transaction has at least one overdue milestone
```

Each at-risk transaction shows:
- Transaction identifier (address)
- Projected commission amount
- Number of overdue milestones
- Days overdue (worst milestone)
- Risk level: `elevated` (1-7 days overdue), `high` (8-14 days), `critical` (15+ days)

---

## 6. Data Model

### 6.1 commission_configs

Stores the agent's default commission configuration.

```python
class CommissionConfig(BaseModel):
    __tablename__ = "commission_configs"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    commission_type = Column(String, nullable=False, default="percentage")  # percentage | flat | tiered
    default_rate = Column(Numeric(5, 4), nullable=True)  # e.g., 0.0300 for 3%
    default_flat_amount = Column(Numeric(12, 2), nullable=True)  # e.g., 5000.00
    tiered_rates = Column(JSON, nullable=True)  # [{up_to: 500000, rate: 0.03}, {up_to: null, rate: 0.02}]
    broker_split_percentage = Column(Numeric(5, 4), nullable=True)  # e.g., 0.3000 for 30%
    default_referral_fee_percentage = Column(Numeric(5, 4), nullable=True)
    team_splits = Column(JSON, nullable=True)  # [{name: "Jane", percentage: 0.10}, ...]

    # Relationships
    agent = relationship("User", back_populates="commission_config")
```

### 6.2 transaction_commissions

Stores the commission details for a specific transaction.

```python
class TransactionCommission(BaseModel):
    __tablename__ = "transaction_commissions"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False, unique=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    commission_type = Column(String, nullable=False, default="percentage")  # percentage | flat | tiered
    rate = Column(Numeric(5, 4), nullable=True)
    flat_amount = Column(Numeric(12, 2), nullable=True)
    tiered_rates = Column(JSON, nullable=True)
    gross_commission = Column(Numeric(12, 2), nullable=False)  # calculated or entered
    is_manual_override = Column(Boolean, default=False)
    projected_net = Column(Numeric(12, 2), nullable=False)  # gross - all splits
    actual_net = Column(Numeric(12, 2), nullable=True)  # entered post-closing
    actual_gross = Column(Numeric(12, 2), nullable=True)  # entered post-closing
    status = Column(String, nullable=False, default="projected")  # projected | pending_close | received | disputed
    is_dual_agency = Column(Boolean, default=False)
    notes = Column(String, nullable=True)

    # Relationships
    transaction = relationship("Transaction", back_populates="commission")
    agent = relationship("User")
    splits = relationship("CommissionSplit", back_populates="transaction_commission", cascade="all, delete-orphan")
```

### 6.3 commission_splits

Stores individual split line items for a transaction's commission.

```python
class CommissionSplit(BaseModel):
    __tablename__ = "commission_splits"

    transaction_commission_id = Column(UUID(as_uuid=True), ForeignKey("transaction_commissions.id"), nullable=False)
    split_type = Column(String, nullable=False)  # broker | team | referral
    recipient_name = Column(String, nullable=False)
    is_percentage = Column(Boolean, default=True)
    percentage = Column(Numeric(5, 4), nullable=True)  # percentage of gross
    flat_amount = Column(Numeric(12, 2), nullable=True)
    calculated_amount = Column(Numeric(12, 2), nullable=False)  # actual dollar amount of this split

    # Relationships
    transaction_commission = relationship("TransactionCommission", back_populates="splits")
```

### 6.4 Relationship additions to existing models

```python
# Add to Transaction model:
commission = relationship("TransactionCommission", back_populates="transaction", uselist=False)

# Add to User model:
commission_config = relationship("CommissionConfig", back_populates="agent", uselist=False)
```

---

## 7. API Endpoints

### 7.1 Commission Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/commission/config` | Get agent's commission configuration |
| PUT | `/api/commission/config` | Create or update commission configuration |

### 7.2 Transaction Commission

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/:id/commission` | Get commission details for a transaction |
| PUT | `/api/transactions/:id/commission` | Set or update commission for a transaction |
| POST | `/api/transactions/:id/commission/recalculate` | Recalculate commission (after price change) |
| PATCH | `/api/transactions/:id/commission/actual` | Enter actual post-closing commission amounts |

### 7.3 Commission Splits

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions/:id/commission/splits` | List all splits for a transaction |
| POST | `/api/transactions/:id/commission/splits` | Add a split (broker, team, referral) |
| PATCH | `/api/transactions/:id/commission/splits/:splitId` | Update a split |
| DELETE | `/api/transactions/:id/commission/splits/:splitId` | Remove a split |

### 7.4 Pipeline & Reporting

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pipeline/summary` | Pipeline totals (active, at-risk, closed, lost) |
| GET | `/api/pipeline/forecast` | Monthly forecast with confidence bands |
| GET | `/api/pipeline/at-risk` | Transactions with overdue milestones and their commission values |
| GET | `/api/pipeline/export` | CSV export of all commission data |

---

## 8. Frontend Components

### 8.1 Commission Configuration Page (Settings)

- Accessible from agent settings
- Form fields: commission type selector, rate/amount input, broker split percentage
- Team splits: add/remove team members with name + percentage/amount
- Referral fee default
- Save button with validation

### 8.2 Transaction Commission Panel

- New section on the transaction detail page
- Shows: gross commission, each split line item, net to agent
- Edit button to override any field
- Status badge: projected / pending close / received
- After closing: "Enter actual amounts" form
- Variance display if actual differs from projected

### 8.3 Pipeline Dashboard Page

- New route: `/pipeline`
- Summary cards at top: total pipeline, at-risk, closed YTD, lost YTD, conversion rate
- Monthly forecast chart (bar or area chart by month)
- At-risk transactions table with overdue details
- Filter controls: date range, status, minimum commission amount
- Export button (CSV download)

### 8.4 Dashboard Enhancement

- Add "Pipeline Value" summary card to main dashboard
- Add "Revenue This Month" card showing closed deals for current month
- Mini at-risk indicator if any overdue deals exist

---

## 9. Definition of Success

| # | Criteria | Verification |
|---|----------|-------------|
| 1 | Agent can configure default commission rates (percentage, flat, tiered) | Manual test through settings page |
| 2 | New transactions auto-populate commission from defaults | Create new transaction, verify commission fields populated |
| 3 | Agent can override commission on any transaction | Edit commission on transaction detail, verify override saved |
| 4 | Commission recalculates on purchase price amendment | Amend price, verify recalculation prompt and correct new amount |
| 5 | Team splits and referral fees calculate correctly | Configure splits, verify net = gross - sum(splits) |
| 6 | Pipeline dashboard shows correct totals | Compare dashboard totals to manual calculation across test transactions |
| 7 | Monthly forecast groups revenue by projected closing month | Create transactions with different closing dates, verify grouping |
| 8 | At-risk revenue surfaces transactions with overdue milestones | Create overdue milestone, verify transaction appears in at-risk |
| 9 | Lost revenue tracks cancelled/terminated deals | Cancel transaction, verify it moves from pipeline to lost |
| 10 | Projected vs. actual commission works post-closing | Close transaction, enter actual amount, verify delta display |
| 11 | CSV export contains all commission data | Export and verify all transactions, splits, and amounts present |
| 12 | Dual agency commission handled correctly | Create dual-agency transaction, verify total commission and splits |
| 13 | Commission data scoped to authenticated agent only | Verify no cross-agent data leakage in API responses |
| 14 | All commission calculations are accurate to the cent | Unit test suite for all calculation scenarios |

---

## 10. Regression Test Plan

### 10.1 New Tests — Phase 5 (12 minimum)

| # | Test | Type | Description |
|---|------|------|-------------|
| 1 | Commission config CRUD | Unit | Create, read, update commission configuration; validate all fields |
| 2 | Percentage calculation | Unit | 3% of $350,000 = $10,500; verify with various prices and rates |
| 3 | Flat fee commission | Unit | Flat $5,000 regardless of price; verify no recalculation on price change |
| 4 | Tiered calculation | Unit | 3% on first $500k + 2% on amount above; verify with $750k sale ($15k + $5k = $20k) |
| 5 | Broker split calculation | Unit | 30% broker split on $10,500 gross = $3,150 to broker, $7,350 to agent |
| 6 | Team split + referral combined | Unit | Broker 30% + team 10% + referral 5% on $10,000 gross; verify net = $5,500 |
| 7 | Price amendment recalculation | Integration | Change price from $350k to $325k; verify commission updates from $10,500 to $9,750 |
| 8 | Manual override preserved on price change | Integration | Set manual override to $8,000; change price; verify override unchanged |
| 9 | Pipeline summary accuracy | Integration | Create 5 transactions with known commissions; verify pipeline total matches expected |
| 10 | Monthly forecast grouping | Integration | Transactions closing in March, April, May; verify correct monthly buckets |
| 11 | At-risk detection | Integration | Create transaction with overdue milestone; verify appears in at-risk report |
| 12 | Lost revenue on cancellation | Integration | Cancel transaction; verify moves from pipeline to lost with correct amount |
| 13 | CSV export completeness | Integration | Export CSV; parse and verify all transactions and fields present |
| 14 | Dual agency commission | Integration | Create dual-agency transaction; verify total commission, splits, and net |
| 15 | Projected to actual transition | Integration | Close transaction, enter actual amounts; verify status change and delta |

### 10.2 Prior Phase Regression

All tests from Phases 1-4 must continue to pass. Specific regression concerns for Phase 5:

| Phase | Regression Risk | Test |
|-------|----------------|------|
| Phase 1 | Transaction creation still works with new commission relationship | Create transaction, verify commission auto-populated from defaults |
| Phase 1 | Transaction detail page loads with new commission panel | Load detail page, verify no errors, commission section renders |
| Phase 1 | Contract parsing unaffected | Upload and parse contract, verify all fields still extracted |
| Phase 2 | Email generation unaffected by commission data | Generate emails, verify no commission data leaks into party emails |
| Phase 2 | Communication log still works | Send emails, verify log entries |
| Phase 3 | Milestone tracking unaffected | Create milestones, verify CRUD operations |
| Phase 3 | Overdue detection feeds into at-risk revenue | Mark milestone overdue, verify commission appears in at-risk |
| Phase 4 | Inspection analysis unaffected | Upload inspection report, run analysis, verify results |
| Phase 4 | Repair tracking still works | Update repair status, verify follow-up emails |

---

## 11. Implementation Order

### Week 13

| Day | Tasks |
|-----|-------|
| Mon-Tue | Data model: create `commission_configs`, `transaction_commissions`, `commission_splits` tables; Alembic migration; SQLAlchemy models; relationship additions |
| Wed | Commission calculation engine: percentage, flat, tiered calculators; split calculation logic; net computation |
| Thu | Commission configuration API: GET/PUT `/api/commission/config`; transaction commission API: GET/PUT endpoints |
| Fri | Commission splits API: CRUD endpoints; recalculation endpoint; price amendment listener |

### Week 14

| Day | Tasks |
|-----|-------|
| Mon | Pipeline summary and forecast API endpoints; at-risk calculation service; CSV export |
| Tue | Frontend: commission configuration settings page; form validation |
| Wed | Frontend: transaction commission panel on detail page; split management UI |
| Thu | Frontend: pipeline dashboard page; summary cards, forecast chart, at-risk table |
| Fri | Frontend: dashboard enhancements; CSV export button; integration testing; bug fixes |

---

## 12. Dependencies

| Dependency | Purpose | Notes |
|------------|---------|-------|
| Phase 4 Complete | Milestone overdue data feeds at-risk calculations | Phase 3 milestones also required |
| Transaction model | Commission is a one-to-one relationship on Transaction | Add `commission` relationship |
| User model | Commission config is per-agent | Add `commission_config` relationship |
| Amendment system | Price changes trigger commission recalculation | Listen for purchase_price amendments |
| Chart library (recharts or chart.js) | Monthly forecast visualization | Already available in frontend dependencies |
| CSV generation (Python csv module) | Commission export | Standard library, no new dependency |

---

*Phase 5 Complete -> Proceed to Phase 6: Document Generation*
