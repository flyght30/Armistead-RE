# Phase 3: Milestone Tracking & Automated Follow-Ups

**Timeline:** Weeks 9-12  
**Status:** Not Started  
**Depends On:** Phase 2 Complete  
**CoV Status:** Verified (see below)

---

## 1. Phase Objective

Build the milestone tracking engine that auto-generates deadlines from contract dates, sends proactive reminders to relevant parties before deadlines, and triggers follow-up emails when milestones are completed — keeping all parties informed of what just happened and what comes next.

**Deliverable:** After initial emails are sent, the system automatically tracks every milestone, reminds the right people at the right time, and sends follow-up updates as the transaction progresses through closing.

---

## 2. Scope

### In Scope
- Auto-generation of milestones from contract dates
- Conditional milestones (skip appraisal for cash, adjust per financing type)
- Celery scheduled job engine for time-based triggers
- Reminder emails sent X days before milestone deadlines
- Follow-up emails sent when milestones complete (notifying all parties of status + next steps)
- Milestone status management (upcoming, scheduled, in_progress, completed, waived, overdue)
- Agent can manually add/edit/remove milestones
- Agent can mark milestones complete or waived
- Closing date extension handling (cascade downstream dates)
- Transaction timeline view on dashboard
- In-app notifications for upcoming milestones
- Overdue milestone alerts

### Out of Scope (This Phase)
- Inspection report analysis (Phase 4)
- Repair negotiation tracking (Phase 4)
- Client-facing portal
- SMS notifications

---

## 3. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-3.1 | As an agent, when I confirm a transaction, milestones are auto-created from contract dates | All applicable milestones generated; cash transactions skip financing milestones |
| US-3.2 | As an agent, I see a timeline view of all milestones for a transaction | Visual timeline with dates, statuses, and responsible parties |
| US-3.3 | As an agent, the system sends reminder emails to relevant parties before deadlines | Reminders sent 2 days before each milestone (configurable); correct party notified |
| US-3.4 | As an agent, when I mark a milestone complete, follow-up emails are sent | All relevant parties receive an update email with what happened and what's next |
| US-3.5 | As an agent, I can manually add, edit, or remove milestones | Full CRUD on milestones; custom milestones supported |
| US-3.6 | As an agent, I can waive a milestone | Waived milestones stop generating reminders; noted in transaction log |
| US-3.7 | As an agent, overdue milestones are highlighted | Visual indicator; agent receives in-app notification |
| US-3.8 | As an agent, if I change the closing date, downstream milestones adjust | All milestones tied to closing date recalculate; agent confirms new dates |
| US-3.9 | As an agent, I see all follow-up emails before they send (same preview workflow as initial) | Follow-up emails go through generate → preview → approve → send flow |
| US-3.10 | As an agent, I receive in-app notifications for upcoming milestones (next 3 days) | Notification bell with count; click to see upcoming items |

---

## 4. Technical Tasks

### 4.1 Milestone Engine (Week 9)

| Task | Description | Estimate |
|------|-------------|----------|
| T-3.1 | Milestone auto-generation service (from contract dates + rules) | 6h |
| T-3.2 | Conditional milestone logic (financing type, state-specific) | 4h |
| T-3.3 | Default timeline templates (days relative to contract/closing) | 4h |
| T-3.4 | Milestone CRUD API endpoints | 4h |
| T-3.5 | Milestone status transition logic (upcoming → scheduled → completed) | 3h |
| T-3.6 | Closing date cascade (recalculate downstream milestones) | 4h |
| T-3.7 | Overdue detection job (daily check) | 2h |

### 4.2 Scheduled Jobs & Reminders (Week 10)

| Task | Description | Estimate |
|------|-------------|----------|
| T-3.8 | Celery beat configuration for periodic tasks | 3h |
| T-3.9 | Reminder job: check milestones due in X days, generate reminder emails | 6h |
| T-3.10 | Follow-up job: when milestone marked complete, generate update emails | 6h |
| T-3.11 | FollowUp Coordinator AI Agent (determines which parties to notify and what to say) | 6h |
| T-3.12 | Reminder email templates (per milestone type) | 4h |
| T-3.13 | Follow-up email templates (per milestone type, per party role) | 6h |
| T-3.14 | Overdue alert generation (in-app + optional email to agent) | 3h |
| T-3.15 | Job idempotency (don't send duplicate reminders) | 3h |

### 4.3 API Development (Week 10-11)

| Task | Description | Estimate |
|------|-------------|----------|
| T-3.16 | GET /api/transactions/:id/milestones — list with status filters | 2h |
| T-3.17 | POST /api/transactions/:id/milestones — add custom milestone | 2h |
| T-3.18 | PATCH /api/transactions/:id/milestones/:id — update status/date | 2h |
| T-3.19 | POST /api/transactions/:id/milestones/:id/complete — mark complete + trigger follow-ups | 3h |
| T-3.20 | POST /api/transactions/:id/milestones/:id/waive — waive milestone | 2h |
| T-3.21 | PATCH /api/transactions/:id/closing-date — update with cascade | 3h |
| T-3.22 | GET /api/notifications — agent's notification feed | 3h |
| T-3.23 | WebSocket setup for real-time notifications | 4h |

### 4.4 Frontend Development (Weeks 11-12)

| Task | Description | Estimate |
|------|-------------|----------|
| T-3.24 | Milestone timeline component (visual timeline with status badges) | 8h |
| T-3.25 | Milestone detail panel (edit date, status, notes, responsible party) | 4h |
| T-3.26 | Add custom milestone modal | 3h |
| T-3.27 | Complete/waive milestone actions with confirmation | 3h |
| T-3.28 | Closing date change flow (edit → see cascaded changes → confirm) | 4h |
| T-3.29 | Follow-up email preview integration (reuse Phase 2 preview component) | 4h |
| T-3.30 | Notification bell component with badge count | 4h |
| T-3.31 | Notification dropdown/page with upcoming milestones | 3h |
| T-3.32 | Overdue milestone visual highlighting (red badges, alerts) | 2h |
| T-3.33 | Dashboard enhancement: show next upcoming milestone per transaction | 3h |

---

## 5. Milestone Generation Rules

### 5.1 Standard Rules (Financing Transaction)

```python
MILESTONE_RULES = [
    {
        "type": "earnest_money",
        "title": "Earnest Money Delivery",
        "reference": "contract_date",  # date field to calculate from
        "offset_days": 3,              # days after reference date
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "buyer",
        "reminder_days_before": 1,
        "notify_on_complete": ["buyer", "attorney", "buyer_agent", "seller_agent"]
    },
    {
        "type": "inspection",
        "title": "Home Inspection",
        "reference": "inspection_deadline",  # use contract date if specific deadline exists
        "offset_days": 0,                    # use the deadline itself
        "fallback_reference": "contract_date",
        "fallback_offset_days": 10,
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "buyer",
        "reminder_days_before": 3,
        "notify_on_complete": ["buyer", "seller", "buyer_agent", "seller_agent"]
    },
    {
        "type": "wood_infestation",
        "title": "Wood Infestation Report",
        "reference": "contract_date",
        "offset_days": 14,
        "required": False,  # may be required by state/contract
        "financing_types": ["all"],
        "responsible_role": "buyer",
        "reminder_days_before": 3,
        "notify_on_complete": ["buyer", "lender", "buyer_agent"]
    },
    {
        "type": "repair_request",
        "title": "Repair Request Deadline",
        "reference": "inspection_deadline",
        "offset_days": 3,
        "fallback_reference": "contract_date",
        "fallback_offset_days": 13,
        "required": False,
        "financing_types": ["all"],
        "responsible_role": "buyer",
        "reminder_days_before": 2,
        "notify_on_complete": ["seller", "seller_agent", "attorney"]
    },
    {
        "type": "appraisal_ordered",
        "title": "Appraisal Ordered",
        "reference": "contract_date",
        "offset_days": 10,
        "required": True,
        "financing_types": ["conventional", "fha", "va", "usda"],  # NOT cash
        "responsible_role": "lender",
        "reminder_days_before": 2,
        "notify_on_complete": ["buyer", "seller_agent", "buyer_agent"]
    },
    {
        "type": "appraisal_complete",
        "title": "Appraisal Complete",
        "reference": "appraisal_contingency_deadline",
        "offset_days": 0,
        "fallback_reference": "contract_date",
        "fallback_offset_days": 21,
        "required": True,
        "financing_types": ["conventional", "fha", "va", "usda"],
        "responsible_role": "lender",
        "reminder_days_before": 3,
        "notify_on_complete": ["buyer", "seller", "buyer_agent", "seller_agent", "attorney"]
    },
    {
        "type": "financing_contingency",
        "title": "Financing Contingency Deadline",
        "reference": "financing_contingency_deadline",
        "offset_days": 0,
        "fallback_reference": "closing_date",
        "fallback_offset_days": -7,
        "required": True,
        "financing_types": ["conventional", "fha", "va", "usda"],
        "responsible_role": "lender",
        "reminder_days_before": 5,
        "notify_on_complete": ["buyer", "seller", "buyer_agent", "seller_agent", "attorney"]
    },
    {
        "type": "title_search",
        "title": "Title Search Complete",
        "reference": "contract_date",
        "offset_days": 21,
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "attorney",
        "reminder_days_before": 3,
        "notify_on_complete": ["buyer", "buyer_agent", "lender"]
    },
    {
        "type": "final_walkthrough",
        "title": "Final Walkthrough",
        "reference": "closing_date",
        "offset_days": -2,
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "buyer",
        "reminder_days_before": 2,
        "notify_on_complete": ["buyer", "seller_agent"]
    },
    {
        "type": "closing_prep",
        "title": "Closing Preparation",
        "reference": "closing_date",
        "offset_days": -7,
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "attorney",
        "reminder_days_before": 2,
        "notify_on_complete": ["all"]
    },
    {
        "type": "closing",
        "title": "Closing Day",
        "reference": "closing_date",
        "offset_days": 0,
        "required": True,
        "financing_types": ["all"],
        "responsible_role": "all",
        "reminder_days_before": 1,
        "notify_on_complete": ["all"]
    }
]
```

### 5.2 Cascade Logic for Closing Date Changes

When closing date changes:
1. Identify all milestones with `reference: "closing_date"` or calculated relative to closing
2. Recalculate due dates based on new closing date
3. Show agent a preview: "These milestones will be updated: [list with old → new dates]"
4. Agent confirms → dates updated → amendment logged
5. If any recalculated date is now in the past, flag as needs attention

---

## 6. Follow-Up Email Specification

### 6.1 FollowUp Coordinator AI Agent

```
System Prompt:
You are a real estate transaction follow-up coordinator. When a milestone
is completed, you determine which parties need to be notified and what 
they need to know.

INPUT: Transaction details, completed milestone, milestone history, 
       party list, representation side

OUTPUT: Array of email objects, one per recipient, with:
- recipient_role
- subject
- body (what happened, what it means, what's next)
- urgency (routine, important, urgent)

RULES:
1. Only notify parties who need to know
2. Client emails should be reassuring and clear
3. Professional party emails should be factual and action-oriented
4. Always state what just happened, what it means, and what comes next
5. Reference specific dates for upcoming milestones
6. If a milestone was overdue, acknowledge the delay professionally
```

### 6.2 Follow-Up Email Examples

**After Inspection Complete (Buyer-Side):**

To Buyer: "Your home inspection for [Address] is complete. I'm reviewing the report and will have a detailed summary for you within [timeframe]. The repair request deadline is [Date]."

To Seller's Agent: "Home inspection for [Address] has been completed. We'll be in touch regarding any findings by [Date]."

**After Appraisal Complete:**

To Buyer: "Great news — the appraisal for [Address] has been completed. The appraised value supports the purchase price. We're moving forward toward closing on [Date]."

To All Parties: "The appraisal for [Address] is complete. Financing remains on track. Next milestone: [Next milestone] on [Date]."

**7 Days Before Closing:**

To Buyer: "We're one week from closing on [Address]! Here's what to prepare: [checklist — certified funds, photo ID, final walkthrough scheduling, utility transfers]."

To Seller: "We're one week from closing on [Address]. Please ensure: [checklist — property vacant/clean, all personal items removed, all agreed repairs completed, keys/garage remotes available]."

---

## 7. Chain-of-Verification: Phase 3

### Step 1: Baseline
Phase 3 adds auto-generated milestones, scheduled reminders, follow-up emails on milestone completion, and agent notification system.

### Step 2: Self-Questioning

**Q1:** What happens if the Celery worker goes down — do we lose scheduled reminders?
**Q2:** How do we handle timezone differences (agent in Pacific, attorney in Eastern)?
**Q3:** What if a milestone is completed out of order (e.g., appraisal before inspection)?
**Q4:** How do we prevent reminder fatigue (too many emails to parties)?
**Q5:** What happens when the agent manually marks a milestone complete that already triggered automatic actions?

### Step 3: Independent Verification

**A1 — Celery Reliability:** Celery Beat runs periodic tasks, and if the worker dies, tasks queue up in Redis. On restart, they execute. However, if Redis also goes down, tasks are lost. Use Redis persistence (AOF) and set up monitoring/alerts for worker health. Consider a "catch-up" job on startup that checks for any missed reminders.
**Resolution:** Redis AOF persistence. Worker health monitoring. Startup catch-up job scans for missed reminders.

**A2 — Timezones:** All dates stored as UTC in the database. The agent's timezone is stored in their profile. Reminders are sent based on the agent's local timezone (e.g., reminder for "2 days before" means 9:00 AM in the agent's timezone, 2 days before). Email content displays dates in the recipient's assumed timezone (use agent's timezone as default since we don't know parties' timezones).
**Resolution:** UTC storage. Agent timezone in profile. Reminders sent at 9:00 AM agent's local time.

**A3 — Out-of-Order Milestones:** Real transactions don't always follow the template order. The system should allow any milestone to be completed at any time. When a milestone completes, the follow-up coordinator looks at the ACTUAL state of all milestones, not the expected order, to determine what's next.
**Resolution:** No enforced ordering. Follow-up logic is state-based, not sequence-based.

**A4 — Reminder Fatigue:** If a transaction has 10 milestones and each sends reminders to 3-4 parties, that's 30-40 emails over the life of a transaction. The reminder frequency should be configurable (agent can set reminder lead time per milestone). Default: 2 days before. Some milestones may not need reminders at all. The agent can disable reminders per milestone.
**Resolution:** Configurable reminder lead time. Agent can disable reminders per milestone. Group reminders: if 2 milestones due within same 3-day window, combine into one email.

**A5 — Manual vs. Auto Completion:** If a milestone is automatically detected as complete (future feature) AND the agent also marks it complete, the system should be idempotent. Completing an already-completed milestone is a no-op. Follow-up emails only sent once per completion event.
**Resolution:** completed_at timestamp prevents duplicate completion. Follow-up emails keyed to milestone completion event ID.

### Step 4: Confidence Check
**Confidence: 95%** — Timezone handling and reminder fatigue are the trickiest parts, but the solutions are sound.

### Step 5: Implement
Proceed with Phase 3. Incorporate timezone handling, flexible milestone ordering, and reminder grouping.

---

## 8. Definition of Done (Phase 3)

| Criteria | Verification |
|----------|-------------|
| Milestones auto-generated on transaction confirmation | Create transaction → verify milestones created with correct dates |
| Cash transactions: no appraisal/financing milestones | Create cash transaction → verify reduced milestone set |
| Reminder emails sent before deadlines | Set milestone due tomorrow → verify reminder sent today |
| Follow-up emails sent on milestone completion | Mark inspection complete → verify follow-up emails generated |
| Agent previews follow-up emails before send | E2E test |
| Milestone CRUD works (add, edit, remove, waive) | Manual test + integration tests |
| Closing date cascade works | Change closing date → verify downstream milestones updated |
| Overdue milestones highlighted | Set milestone to past date → verify visual indicator |
| In-app notifications for upcoming milestones | Check notification bell shows upcoming items |
| No duplicate reminders sent | Same reminder period → verify only one email sent |
| Timeline view displays correctly | Manual test with 10+ milestones |

---

## 9. Test Plan

### 9.1 Unit Tests

| Test Area | Tests |
|-----------|-------|
| Milestone generator | Correct milestones per financing type; date calculations; conditional logic |
| Reminder scheduler | Identifies milestones due within reminder window; skips waived/completed |
| Follow-up coordinator | Correct recipients per milestone type; correct content per side |
| Cascade calculator | Correct date shifts; handles past-date scenarios |
| Timezone handler | Correct UTC conversion; reminder timing in agent's local zone |

### 9.2 Integration Tests

| Test | Steps | Expected Result |
|------|-------|----------------|
| Full milestone lifecycle | Create transaction → milestones appear → mark one complete → follow-ups generated | End-to-end flow works |
| Cash transaction milestones | Create cash transaction → check milestones | No appraisal/financing milestones |
| Reminder delivery | Create milestone due in 2 days → run reminder job | Reminder email queued for correct party |
| No premature reminder | Create milestone due in 10 days → run reminder job | No email generated |
| Overdue detection | Create milestone with past date → run overdue job | Milestone marked overdue, agent notified |
| Closing date cascade | Change closing date +7 → check milestones | Closing-relative milestones shifted +7 |
| Waive stops reminders | Waive milestone → run reminder job | No reminder for waived milestone |
| Idempotent completion | Complete milestone twice | Second call is no-op; one set of follow-ups |

### 9.3 E2E Tests

| Test | Flow |
|------|------|
| Full transaction lifecycle | Upload → Confirm → Initial emails → Milestone created → Complete inspection → Follow-up sent → Complete appraisal → Follow-up → Approach closing → Reminder → Close |
| Closing date change | Open transaction → Change closing date → Confirm cascade → Verify new dates |
| Custom milestone | Add custom milestone → Set date → Receive reminder → Complete → Follow-up |

---

## 10. Phase 3 Success Criteria

| Metric | Target | How Measured |
|--------|--------|-------------|
| All user stories completed | 10/10 | Story acceptance criteria |
| Milestones auto-generated correctly | 100% | Integration tests across all financing types |
| Reminders sent on time (within 1 hour of scheduled) | 100% | Job execution logs |
| Follow-up emails relevant and accurate | Reviewed by agent (qualitative) | Manual review of 5 transactions |
| No duplicate reminders or follow-ups | 0 duplicates | Idempotency tests |
| Overdue milestones detected within 24 hours | 100% | Daily job verification |
| Agent can manage full milestone lifecycle without bugs | Verified | E2E test suite passes |

---

*Phase 3 Complete → Proceed to Phase 4: Inspection Analysis*
