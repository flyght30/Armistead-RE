# Phase 1: Today View — Intelligent Daily Action List

## 1. Phase Overview

**Goal:** Replace the passive stats-card dashboard with a proactive "Today View" — a prioritized daily action list that makes agents open the app every morning. Auto-generate milestone templates when transactions are created so agents never have to manually build out their checklists from scratch.

**Timeline:** Weeks 1-3

**Key Deliverables:**
- **Today View Dashboard** — A prioritized, urgency-grouped action list that replaces the current stats dashboard as the default `/` route.
- **Milestone Templates** — State-specific, financing-type-specific milestone templates that auto-generate milestones with computed dates when applied to a transaction.
- **Transaction Health Score** — A computed 0-100 score per transaction that surfaces which deals need attention at a glance.
- **Smart Action Items** — Auto-generated (and manually creatable) action items derived from milestone analysis, missing data, and approaching deadlines.

---

## 2. Chain of Verification (CoV)

Critical questions that could cause this phase to fail, with risk assessment and resolution strategies.

| # | Question | Risk | Resolution |
|---|----------|------|------------|
| 1 | What if an agent has 30+ active transactions — does the Today View become overwhelming? | High — a wall of 100+ action items is unusable. Agents will stop using the view entirely. | Implement virtual scrolling and collapse-by-default for the "This Week" section. Show counts per section. Add a "Focus Mode" that pins 1-3 transactions. Default sort is by urgency then by closing date proximity. Paginate after 20 items per section. |
| 2 | What if milestone templates don't match the actual contract dates? | High — agents lose trust and stop using templates, defeating the purpose. | Templates use relative day offsets, not absolute dates. On application, the agent confirms the contract execution date and closing date. A preview step shows all computed dates before milestones are created. Agents can edit any milestone date after creation. |
| 3 | How do we handle timezone differences for "today" and "due today"? | Medium — an agent in Pacific time could see items differently than expected if we store everything in UTC. | Store all dates as TIMESTAMPTZ. Resolve "today" using the agent's profile timezone (default to America/New_York). The Today View endpoint accepts an optional `timezone` query parameter. All date comparisons for grouping (overdue/today/upcoming/this week) are performed in the agent's local timezone. |
| 4 | What if the agent manually added milestones AND applies a template — duplicates? | High — duplicate milestones cause confusion and erode trust in the system. | When applying a template, query existing milestones for the transaction. Match by normalized title (case-insensitive, trimmed). If a match is found, skip that template item and log it. Return a summary: "Created 15 milestones, skipped 3 (already exist)." The agent sees the skip report and can review. |
| 5 | What if a transaction has no closing date — how do we compute milestone dates? | High — many templates reference closing_date offsets (e.g., -3 days from closing for final walkthrough). Without a closing date, those milestones have no anchor. | Milestones with `offset_reference = 'closing_date'` are created with `due_date = NULL` and a status of `pending_date`. They appear in a special "Needs Date" section in the Today View. When the agent later sets a closing date, a cascade recalculates all NULL-dated milestones. The apply-template endpoint warns if closing_date is missing but does not block template application. |
| 6 | What if the health score algorithm is too aggressive and everything looks "red"? | Medium — if every transaction is red, the signal is meaningless. Agents experience alert fatigue and ignore the health score. | Calibrate the algorithm so that a brand-new transaction with no overdue items starts at 85 (green). Only active penalties (overdue milestones, missing critical parties) drive the score down. Run the scoring algorithm against seed data and verify that a healthy transaction scores >= 85 and a moderately behind transaction scores 50-70. Add a `/api/transactions/{id}/health` endpoint that returns a full breakdown so the agent understands why the score is what it is. |
| 7 | What about transactions in draft status — should they show in Today View? | Medium — showing drafts clutters the view with incomplete data. Not showing them means agents forget about drafts. | Draft transactions do NOT appear in the Today View action items. Instead, they appear in the Pipeline Sidebar with a gray dot and a label "Draft." A separate "Incomplete Drafts" card at the top of the Today View shows a count (e.g., "You have 2 draft transactions") with a link to complete them. |
| 8 | What if two milestones from different transactions are due on the same day for the same party? | Low-Medium — the party (e.g., a lender) might receive two reminders on the same day for different transactions. The agent sees two items that look similar. | In the Today View, group items by due date first, then sub-sort by transaction. Show the transaction address prominently on each action item card so the agent can distinguish them. For reminder emails (future phase), batch same-day reminders for the same party into a single email with a summary table. |
| 9 | How do we handle milestone templates for states we don't have templates for yet? | Medium — an agent working in Florida sees no templates and has a degraded experience. | Allow agents to create custom templates. Show a "No templates available for [State]" message with options: (a) start from a blank transaction, (b) copy an existing template from another state and modify it, (c) request a template (logs the request for us to prioritize). Ship with GA and AL templates initially, and add more based on agent requests. |
| 10 | What if the agent wants to customize a template after applying it? | Low — this is expected behavior. Agents always need to tweak dates and add deal-specific milestones. | Template application creates normal milestone records. Once created, milestones are fully editable — change title, date, responsible party, or delete. The `template_item_id` FK is preserved for reference but does not constrain editing. The template is a starting point, not a straitjacket. |
| 11 | What if a closing date changes — do all milestone dates auto-update? | High — if milestones don't update, agents have to manually recalculate and edit every date. If they do auto-update, agents might lose manual overrides they intentionally set. | When closing_date changes on a transaction, auto-update only milestones where `offset_reference = 'closing_date'` AND `is_auto_generated = true` AND the milestone has NOT been manually edited (track via an `is_manually_edited` flag or by comparing current due_date to the computed date). Show a confirmation dialog: "Updating closing date will adjust 8 milestone dates. 2 milestones were manually edited and will NOT change. Proceed?" |

---

## 3. Detailed Requirements

### 3.1 Today View Dashboard

The Today View replaces the current stats-card Dashboard as the default `/` route. It is a prioritized daily action list organized by urgency.

**Sections (displayed in this order):**

- **Overdue** — Past due milestones and action items that have not been completed. Red background accent. Shows days overdue.
- **Due Today** — Milestones and action items due today (in the agent's local timezone). Yellow background accent.
- **Coming Up (Next 3 Days)** — Items due tomorrow through 3 days from now. Green background accent. Shows "in X days."
- **This Week** — Items due 4-7 days from now. Neutral background. Collapsed by default if more than 5 items.

**Each Action Item Card displays:**
- Transaction address (linked to transaction detail)
- Milestone title or action item title
- Responsible party name and role
- Due date and urgency indicator (days overdue in red, "today" in yellow, "in X days" in green)
- Transaction health dot (red/yellow/green)

**Quick Actions (inline buttons on each card):**
- **Mark Complete** — Marks the milestone or action item as completed. Removes from Today View.
- **Send Reminder** — Opens a pre-filled email reminder for the responsible party (Phase 2 feature, button disabled with tooltip in Phase 1).
- **View Transaction** — Navigates to the transaction detail page, scrolled to the relevant milestone.

**Filters:**
- By transaction (dropdown of active transactions)
- By milestone type (e.g., inspection, appraisal, financing, closing)
- By priority (critical, high, medium, low)

**Pipeline Sidebar:**
A compact sidebar (left side, always visible on desktop, drawer on mobile) showing all active transactions.
- Each row: property address, closing date, health dot (red/yellow/green)
- Clicking a row filters the Today View to that transaction
- Shows count of overdue items per transaction
- Draft transactions shown at the bottom with a gray dot

### 3.2 Milestone Templates

Milestone templates encode the standard checklist of milestones for a given state, financing type, and representation side. They are the backbone of the auto-generation system.

**Template Structure:**
- `state_code` (e.g., "GA", "AL") — the state whose regulations and customs the template follows
- `financing_type` (e.g., "conventional", "fha", "va", "cash") — determines which milestones apply
- `representation_side` (e.g., "buyer", "seller") — determines the agent's role and milestone focus

Each template contains an ordered list of milestone definitions.

**Milestone Definition Fields:**
- `type` — category of milestone (e.g., "inspection", "appraisal", "financing", "title", "closing")
- `title` — human-readable milestone name (e.g., "Schedule Home Inspection")
- `day_offset` — integer days relative to a reference date
- `offset_reference` — one of:
  - `contract_date` — offset from the contract execution date (positive integer, e.g., +7 means 7 days after contract)
  - `closing_date` — offset from the closing date (negative integer, e.g., -3 means 3 days before closing)
  - `milestone:{template_item_id}` — offset from when another milestone completes (for chained milestones)
- `responsible_party_role` — which party role is responsible (e.g., "buyer_agent", "seller_agent", "lender", "title_company", "inspector")
- `reminder_days_before` — how many days before the due date to surface this as an action item (default: 2)
- `is_conditional` / `condition_field` / `condition_not_value` — for milestones that should be skipped under certain conditions (e.g., skip appraisal for cash deals)

**Initial Templates to Ship:**

| Template | State | Financing | Side | Milestones |
|----------|-------|-----------|------|------------|
| GA Conventional Buyer | GA | conventional | buyer | 18 |
| GA Conventional Seller | GA | conventional | seller | 14 |
| GA FHA Buyer | GA | fha | buyer | 20 |
| GA VA Buyer | GA | va | buyer | 20 |
| GA Cash Buyer | GA | cash | buyer | 12 |
| AL Conventional Buyer | AL | conventional | buyer | 16 |
| AL Conventional Seller | AL | conventional | seller | 12 |

### 3.3 Transaction Health Score

A computed score from 0-100 that summarizes how "on track" a transaction is. Cached on the transaction record and recomputed periodically (on milestone changes, daily cron, or on-demand).

**Scoring Factors:**

| Factor | Point Impact | Notes |
|--------|-------------|-------|
| Overdue milestone | -20 points each | Capped: 3+ overdue milestones = score floor of 10 |
| Milestone due within 3 days, no action taken | -10 points each | "No action" means status is still pending |
| Missing key party: buyer | -15 points | Only for active (non-draft) transactions |
| Missing key party: seller | -15 points | Only for active (non-draft) transactions |
| Missing key party: lender | -15 points | Only for financed deals (not cash) |
| Missing key document: no contract uploaded | -10 points | Checked via file attachments on the transaction |
| Days-to-close vs milestones-remaining ratio | -5 to -15 points | If remaining milestones / days to close > 0.5, penalize proportionally |

**Base score:** 100 (perfect). Subtract penalties. Floor at 0.

**Display Thresholds:**
- **Red (0-40):** Transaction needs immediate attention. Pulsing red dot in sidebar.
- **Yellow (41-70):** Transaction has issues to address. Steady yellow dot in sidebar.
- **Green (71-100):** Transaction is on track. Steady green dot in sidebar.

### 3.4 Action Items

Action items are the individual cards that appear in the Today View. They are either auto-generated from milestone and transaction analysis, or manually created by the agent.

**Auto-Generation Triggers:**
- A milestone's due date is within `reminder_days_before` days -> create `milestone_due` action item
- A milestone's due date has passed and it is not completed -> create `milestone_overdue` action item
- A transaction is missing a required party (buyer, seller, or lender for financed deals) -> create `missing_party` action item
- A transaction has no uploaded contract document -> create `missing_document` action item
- A transaction's closing date is within 7 days -> create `closing_approaching` action item

**Action Item Types:**
- `milestone_due` — A milestone is approaching its due date
- `milestone_overdue` — A milestone has passed its due date without completion
- `missing_party` — A required party has not been added to the transaction
- `missing_document` — A required document has not been uploaded
- `closing_approaching` — The closing date is within 7 days
- `custom` — Manually created by the agent

**Priority Levels:**
- `critical` — Overdue milestones, closing within 2 days
- `high` — Due today, missing key parties on transactions closing within 14 days
- `medium` — Due within 3 days, missing documents
- `low` — Due within 7 days, informational items

**Actions an agent can take on an action item:**
- **Complete** — Marks as completed. If linked to a milestone, also marks the milestone as completed.
- **Snooze** — Hides the item until a specified date (tomorrow, 2 days, custom date). Sets `snoozed_until`.
- **Dismiss** — Permanently removes the item from the Today View. Does not affect the underlying milestone.

---

## 4. Data Model

### New Tables

```sql
-- Milestone template definitions (e.g., "GA Conventional Buyer Side")
milestone_templates:
  id UUID PK
  name VARCHAR(200) NOT NULL
  state_code VARCHAR(2) NOT NULL
  financing_type VARCHAR(30) NOT NULL        -- conventional, fha, va, cash
  representation_side VARCHAR(10) NOT NULL   -- buyer, seller
  description TEXT
  is_default BOOLEAN DEFAULT false           -- system-provided template
  is_active BOOLEAN DEFAULT true
  created_by UUID FK -> users (nullable)     -- NULL for system templates
  created_at TIMESTAMPTZ
  updated_at TIMESTAMPTZ

-- Individual milestone items within a template
milestone_template_items:
  id UUID PK
  template_id UUID FK -> milestone_templates ON DELETE CASCADE
  type VARCHAR(50) NOT NULL                  -- inspection, appraisal, financing, title, closing, etc.
  title VARCHAR(200) NOT NULL
  day_offset INTEGER NOT NULL                -- positive = from contract, negative = from closing
  offset_reference VARCHAR(30) DEFAULT 'contract_date'  -- contract_date | closing_date | milestone:{id}
  responsible_party_role VARCHAR(30)         -- buyer_agent, seller_agent, lender, title_company, inspector
  reminder_days_before INTEGER DEFAULT 2
  is_conditional BOOLEAN DEFAULT false       -- if true, evaluate condition fields
  condition_field VARCHAR(50)                -- e.g., 'financing_type'
  condition_not_value VARCHAR(50)            -- e.g., 'cash' (skip if financing_type == cash)
  sort_order INTEGER DEFAULT 0
  created_at TIMESTAMPTZ
  updated_at TIMESTAMPTZ

-- Action items displayed in the Today View
action_items:
  id UUID PK
  transaction_id UUID FK -> transactions ON DELETE CASCADE
  milestone_id UUID FK -> milestones (nullable) ON DELETE SET NULL
  type VARCHAR(50) NOT NULL                  -- milestone_due, milestone_overdue, missing_party, etc.
  title VARCHAR(300) NOT NULL
  description TEXT
  priority VARCHAR(20) NOT NULL DEFAULT 'medium'  -- critical, high, medium, low
  status VARCHAR(20) NOT NULL DEFAULT 'pending'   -- pending, snoozed, completed, dismissed
  due_date TIMESTAMPTZ
  snoozed_until TIMESTAMPTZ
  completed_at TIMESTAMPTZ
  agent_id UUID FK -> users
  created_at TIMESTAMPTZ
  updated_at TIMESTAMPTZ
```

### Modifications to Existing Tables

```sql
-- Add to transactions table
ALTER TABLE transactions ADD COLUMN contract_execution_date TIMESTAMPTZ;
ALTER TABLE transactions ADD COLUMN health_score FLOAT;
ALTER TABLE transactions ADD COLUMN template_id UUID REFERENCES milestone_templates(id) ON DELETE SET NULL;

-- Add to milestones table
ALTER TABLE milestones ADD COLUMN template_item_id UUID REFERENCES milestone_template_items(id) ON DELETE SET NULL;
ALTER TABLE milestones ADD COLUMN is_auto_generated BOOLEAN DEFAULT false;
```

---

## 5. API Endpoints

### Today View

```
GET  /api/today
     Query params:
       - filter: "overdue" | "due_today" | "coming_up" | "this_week" (optional)
       - transaction_id: UUID (optional, filter to single transaction)
       - priority: "critical" | "high" | "medium" | "low" (optional)
       - timezone: string (optional, defaults to agent profile timezone)
     Response: {
       overdue: ActionItem[],
       due_today: ActionItem[],
       coming_up: ActionItem[],
       this_week: ActionItem[],
       summary: { overdue_count, due_today_count, coming_up_count, this_week_count }
     }
```

### Milestone Templates

```
GET  /api/templates/milestones
     Query params:
       - state_code: VARCHAR(2) (optional)
       - financing_type: VARCHAR(30) (optional)
       - representation_side: VARCHAR(10) (optional)
     Response: MilestoneTemplate[]

GET  /api/templates/milestones/{id}
     Response: MilestoneTemplate with items[]

POST /api/templates/milestones
     Body: { name, state_code, financing_type, representation_side, description, items[] }
     Response: MilestoneTemplate with items[]

PATCH /api/templates/milestones/{id}
     Body: { name?, description?, is_active?, items[]? }
     Response: MilestoneTemplate with items[]
```

### Template Application

```
POST /api/transactions/{id}/apply-template
     Body: {
       template_id: UUID,
       contract_execution_date: string (ISO date),
       closing_date: string (ISO date, optional)
     }
     Response: {
       milestones_created: number,
       milestones_skipped: number,
       skipped_reasons: { title: string, reason: string }[],
       milestones: Milestone[]
     }
```

### Health Score

```
GET  /api/transactions/{id}/health
     Response: {
       score: number,
       color: "red" | "yellow" | "green",
       breakdown: {
         overdue_milestones: { count, penalty },
         upcoming_no_action: { count, penalty },
         missing_parties: { details[], penalty },
         missing_documents: { details[], penalty },
         pace_ratio: { remaining_milestones, days_to_close, penalty }
       }
     }
```

### Action Items

```
GET  /api/transactions/{id}/action-items
     Query params:
       - status: "pending" | "snoozed" | "completed" | "dismissed" (optional)
       - type: string (optional)
     Response: ActionItem[]

POST /api/transactions/{id}/action-items
     Body: { title, description?, priority?, due_date?, type: "custom" }
     Response: ActionItem

PATCH /api/action-items/{id}
     Body: {
       status?: "completed" | "snoozed" | "dismissed",
       snoozed_until?: string (ISO date),
       title?: string,
       priority?: string
     }
     Response: ActionItem
```

---

## 6. Frontend Components

### New Pages

- **`TodayView.tsx`** — Replaces Dashboard as the `/` route. Renders the four urgency-grouped sections (Overdue, Due Today, Coming Up, This Week) with action item cards. Includes filters and summary counts at the top. Fetches data from `GET /api/today`.

- **`PipelineSidebar.tsx`** — A compact, always-visible sidebar on the left (desktop) or bottom drawer (mobile). Lists all active transactions with: property address, closing date, health dot color. Clicking a transaction filters the Today View. Shows overdue item count per transaction. Draft transactions shown at bottom with gray dot.

### Modified Pages

- **`NewTransaction.tsx`** — After the agent enters basic transaction info (address, parties, dates), a new "Apply Template" step appears. The step shows matching templates based on the transaction's state, financing type, and side. The agent selects a template and confirms dates. Template application happens on submit.

- **`TransactionDetail/index.tsx`** — Add a `HealthBadge` component next to the transaction title. Shows the numeric score and colored indicator. Clicking it opens a breakdown popover showing why the score is what it is.

- **`Layout.tsx`** — Integrate `PipelineSidebar` as a persistent left sidebar. Add responsive behavior: sidebar visible on screens >= 1024px wide, hidden behind a hamburger menu on smaller screens.

- **`App.tsx`** — Update routes: `/` renders `TodayView` instead of `Dashboard`. The old Dashboard stats are removed (replaced by the Today View). Add `/pipeline` route as an alias for the sidebar in full-page mode on mobile.

### New Components

- **`ActionItemCard.tsx`** — Renders a single action item. Displays: transaction address (linked), milestone title, responsible party, due date with urgency styling, health dot. Includes inline quick-action buttons: Mark Complete, Snooze (with dropdown: tomorrow, 2 days, custom), Dismiss, View Transaction.

- **`ActionItemList.tsx`** — Receives an array of action items and a section label (e.g., "Overdue"). Renders them as a list of `ActionItemCard` components. Shows item count in the section header. Supports collapse/expand for sections with many items.

- **`HealthBadge.tsx`** — A small colored badge component. Props: `score: number`. Renders a circle with the score inside, colored red (0-40), yellow (41-70), or green (71-100). Optionally shows a tooltip with the score breakdown.

- **`TemplatePicker.tsx`** — A modal or inline step component for selecting a milestone template. Fetches available templates from `GET /api/templates/milestones`. Filters by state/financing/side. Shows template name, description, and milestone count. On selection, shows a preview of milestone dates (computed from the provided contract and closing dates). Confirm button triggers template application.

- **`PipelineItem.tsx`** — A compact row component used inside `PipelineSidebar`. Renders: health dot, property address (truncated), closing date, overdue count badge. Hover state highlights the row. Click selects the transaction.

---

## 7. Definition of Success

Phase 1 is COMPLETE when ALL of these criteria are met:

| # | Success Criteria | Measurement |
|---|-----------------|-------------|
| 1 | Today View loads in < 2 seconds with 30+ active transactions | Performance test with seeded data; measure time from route navigation to full render |
| 2 | Milestone templates auto-generate correct dates for at least 3 GA templates | Unit tests covering GA Conventional Buyer, GA FHA Buyer, and GA Cash Buyer |
| 3 | Cash transactions correctly skip financing/appraisal milestones | Unit test applying GA Cash template and asserting no financing-related milestones |
| 4 | Health score correctly penalizes overdue milestones and missing parties | Unit tests for green, yellow, and red score scenarios |
| 5 | Action items auto-generate from milestone deadlines | Integration test verifying action items are created when milestones approach or pass due dates |
| 6 | Template application creates milestones with correct computed dates | Integration test applying a template and verifying each milestone's due_date matches expected computation |
| 7 | Closing date change cascades to all milestone dates that reference it | Integration test changing closing_date and verifying milestone date updates |
| 8 | Agent can dismiss, snooze, and complete action items | E2E test exercising all three actions and verifying state changes |
| 9 | Pipeline sidebar shows all active transactions with correct health colors | E2E test verifying sidebar rendering and color accuracy |
| 10 | Today View correctly groups items into Overdue / Due Today / Coming Up / This Week | E2E test with milestones at various due dates, verifying correct section placement |

---

## 8. Regression Test Plan

### Tests that MUST pass before Phase 1 ships

#### Backend Unit Tests

```python
def test_milestone_template_date_computation():
    """Given a template item with day_offset +7 and contract_execution_date
    of 2026-03-01, the computed milestone due_date should be 2026-03-08."""

def test_milestone_template_closing_offset():
    """Given a template item with day_offset -3 and closing_date of
    2026-04-15, the computed milestone due_date should be 2026-04-12."""

def test_milestone_template_cash_conditional():
    """Given a GA Cash template applied to a cash transaction, no appraisal
    or financing milestones should be created. Only the 12 non-conditional
    milestones should exist."""

def test_health_score_all_green():
    """Transaction with all milestones on time, all parties present,
    contract uploaded. Health score should be >= 90."""

def test_health_score_overdue():
    """Transaction with 2 overdue milestones. Health score should be <= 60."""

def test_health_score_missing_parties():
    """Financed transaction with no lender party. Health score should be
    reduced by 15 points from what it would otherwise be."""

def test_today_view_sorting():
    """Given milestones across 5 transactions with various due dates,
    overdue items appear first, then due today, then upcoming, then
    this week."""

def test_today_view_excludes_drafts():
    """Draft transactions should NOT produce action items in the Today View.
    They should only appear in the Pipeline Sidebar."""

def test_action_item_auto_generation():
    """When a milestone's due date passes without completion, an action item
    of type 'milestone_overdue' is auto-created."""

def test_action_item_snooze():
    """Snoozed action items with snoozed_until in the future do not appear
    in the Today View results. They reappear after the snooze expires."""
```

#### Backend Integration Tests

```python
def test_apply_template_creates_milestones():
    """Apply the GA Conventional Buyer template to a new transaction.
    Verify exactly 18 milestones are created with correct dates relative
    to the provided contract_execution_date and closing_date."""

def test_apply_template_no_duplicates():
    """Create a transaction, manually add a milestone titled 'Schedule
    Home Inspection'. Then apply a template that also includes that
    milestone. The manual milestone should be preserved and the template
    item should be skipped. Total milestone count should not include
    duplicates."""

def test_closing_date_cascade():
    """Apply a template to a transaction, then change the closing date by
    +7 days. All milestones with offset_reference='closing_date' and
    is_auto_generated=true should have their due_dates shifted by +7 days.
    Milestones with offset_reference='contract_date' should be unchanged."""

def test_today_endpoint_aggregation():
    """Create 3 transactions with milestones in various states: some
    overdue, some due today, some upcoming, some completed. GET /api/today
    should return correctly categorized and sorted action items. Completed
    milestones should not appear."""
```

#### Frontend E2E Tests

```typescript
test('today_view_renders_sections', async () => {
  // Navigate to /
  // Verify sections exist: Overdue, Due Today, Coming Up, This Week
  // Verify items appear in the correct sections based on their due dates
});

test('today_view_mark_complete', async () => {
  // Click "Mark Complete" on an action item
  // Item disappears from the Today View list
  // Verify the underlying milestone status is updated to completed
});

test('template_picker_in_new_transaction', async () => {
  // Navigate to new transaction form
  // Fill in basic info with state=GA, financing=conventional, side=buyer
  // Template picker step appears
  // Select "GA Conventional Buyer" template
  // Verify 18 milestones created and visible on the timeline tab
});

test('pipeline_sidebar_health_colors', async () => {
  // Seed transactions with various health scores
  // Verify transactions with overdue milestones show red health dot
  // Verify transactions fully on track show green health dot
  // Verify yellow threshold transactions show yellow dot
});

test('health_score_on_transaction_detail', async () => {
  // Navigate to a transaction detail page
  // Verify HealthBadge component displays with correct numeric score
  // Verify the badge color matches the score threshold
});
```

#### Regression Tests (Existing Features)

```python
def test_existing_dashboard_features_preserved():
    """Transaction list is still accessible (moved to /pipeline).
    Transaction creation still works end-to-end.
    Transaction detail tabs (milestones, parties, files, amendments) all
    still load correctly."""

def test_milestone_crud_still_works():
    """Manual milestone creation, editing, and deletion all function.
    Template-created milestones can also be edited and deleted without
    error."""

def test_party_crud_still_works():
    """All party CRUD operations (create, read, update, delete) continue
    to function correctly after Phase 1 changes."""

def test_document_upload_still_works():
    """File upload to S3 still functions. File download/viewing still
    works. File metadata is preserved."""

def test_contract_parsing_still_works():
    """AI contract parsing via Claude API still functions. Confidence
    scores still display on parsed fields. Parsed data still populates
    transaction fields correctly."""

def test_amendment_tracking_still_works():
    """Transaction updates still create amendment records. Amendment
    history is still viewable on the transaction detail page."""
```

---

## 9. Implementation Order

### Week 1: Data Layer and Core Services

**Backend:**
- Create `MilestoneTemplate`, `MilestoneTemplateItem`, and `ActionItem` SQLAlchemy models
- Create Alembic migration for new tables and column additions to `transactions` and `milestones`
- Create Pydantic schemas for templates, template items, and action items
- Create `template_service.py` — CRUD for templates, template application logic with date computation and duplicate detection
- Create `health_score_service.py` — score computation with full breakdown
- Seed the 7 milestone templates with realistic milestone definitions and day offsets
- Write unit tests for date computation, conditional milestone skipping, and health score calculation

### Week 2: API Endpoints and Auto-Generation

**Backend:**
- Create `today_service.py` — aggregation logic for the Today View endpoint, timezone handling, section grouping
- Create `action_item_service.py` — auto-generation logic triggered by milestone state changes, snooze/dismiss/complete logic
- Create API routes: `/api/today`, `/api/templates/milestones`, `/api/transactions/{id}/apply-template`, `/api/transactions/{id}/health`, `/api/transactions/{id}/action-items`, `/api/action-items/{id}`
- Write integration tests for template application, today endpoint aggregation, closing date cascade

**Frontend:**
- Build `TodayView.tsx` page with four urgency-grouped sections
- Build `ActionItemCard.tsx` and `ActionItemList.tsx` components
- Wire up API calls to `GET /api/today`
- Implement Mark Complete action

### Week 3: Frontend Polish, Sidebar, and Integration Testing

**Frontend:**
- Build `PipelineSidebar.tsx` and `PipelineItem.tsx`
- Integrate sidebar into `Layout.tsx` with responsive behavior
- Build `HealthBadge.tsx` and add to `TransactionDetail`
- Build `TemplatePicker.tsx` and integrate into `NewTransaction.tsx` flow
- Implement Snooze and Dismiss actions on action items
- Update `App.tsx` routes: `/` -> TodayView, add `/pipeline` route

**Testing:**
- Run full integration test suite
- Run all regression tests for existing features
- Performance test Today View with 30+ seeded transactions
- Build verification (frontend builds without errors, backend starts without errors)

---

## 10. Dependencies

- **No new external service dependencies.** All features are computed locally — no new third-party APIs, no new cloud services.
- **Requires existing milestone CRUD to be working.** Verified in Phase 1 Step 1.2 and 1.3.
- **Requires existing transaction CRUD to be working.** Verified in Phase 1 Step 1.2 and 1.3.
- **Requires existing party CRUD to be working.** Health score checks for missing parties.
- **Requires existing file upload to be working.** Health score checks for missing contract documents.
- **No new npm packages needed.** The frontend uses existing Tailwind CSS, React Query, and component patterns.
- **No new Python packages needed.** The backend uses existing SQLAlchemy, Pydantic, and FastAPI patterns.
