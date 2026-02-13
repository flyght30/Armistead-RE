# Transaction-to-Close: Master Test Plan

**Version:** 1.0  
**Date:** February 12, 2026  
**Coverage:** All 5 Phases

---

## 1. Testing Strategy Overview

The TTC platform uses a 5-level testing strategy. Each level catches different categories of defects, and all levels must pass before any phase is considered complete.

| Level | What It Tests | Tools | When |
|-------|--------------|-------|------|
| **Unit Tests** | Individual functions, services, models | pytest (backend), React Testing Library (frontend) | On every commit (CI) |
| **Integration Tests** | API endpoints, database operations, service interactions | pytest + httpx (backend), Playwright (frontend) | On every PR (CI) |
| **AI Accuracy Tests** | Claude API output quality for parsing, emails, analysis | Custom test harness + manual review | Per phase, on AI prompt changes |
| **E2E Tests** | Full user workflows from UI through backend | Playwright or Cypress | On every PR to main (CI) |
| **Performance Tests** | Response times, throughput, concurrent load | Locust or k6 | Pre-release per phase |

---

## 2. Test Environment

| Environment | Purpose | Data |
|-------------|---------|------|
| **Local (Docker Compose)** | Developer testing | Seed data + test contracts |
| **CI (GitHub Actions)** | Automated test suite | Test fixtures, mocked AI |
| **Staging** | Pre-production validation | Anonymized real data |
| **Production** | Live system | Real agent data |

**AI Testing Note:** Unit and integration tests should use MOCKED Claude API responses to avoid cost and flakiness. AI accuracy tests use the REAL API against sample documents.

---

## 3. Phase 1 Tests — Foundation & Contract Parsing

### 3.1 Unit Tests (48 tests estimated)

**Transaction Service**
- Create transaction with valid data → success
- Create transaction with missing required fields → validation error
- List transactions for agent → returns only that agent's data
- List with status filter → correct filtering
- Soft delete → status changes, data preserved
- Update transaction → amendment logged

**Party Service**
- Add party with valid role → success
- Add party with invalid role → validation error
- Remove party → cascade or error if referenced
- Update party email → success
- List parties for transaction → correct set

**AI Client Wrapper**
- Successful API call → parsed response
- API timeout → retry 3 times with backoff
- API 429 (rate limit) → retry with backoff
- API 500 → retry then raise
- Invalid response schema → raise validation error
- API returns low-confidence fields → flagged correctly

**S3 Service**
- Upload file → returns URL
- Generate signed URL → valid for 15 minutes
- Upload too-large file → rejection

**PDF Extraction**
- Text PDF → extracted text
- Scanned PDF (no text) → triggers vision fallback
- Corrupt PDF → clear error

### 3.2 Integration Tests (20 tests estimated)

| # | Test | Method | Expected |
|---|------|--------|----------|
| 1 | Create transaction via API | POST /api/transactions | 201, record in DB |
| 2 | Upload contract file | POST /api/transactions/:id + file | File in S3, URL saved |
| 3 | Trigger parse | POST /api/transactions/:id/parse | AI extracts fields, response matches schema |
| 4 | Parse text PDF | Upload text PDF → parse | All fields populated |
| 5 | Parse scanned PDF | Upload scanned PDF → parse | Vision fallback, fields populated |
| 6 | Parse cash contract | Upload cash contract → parse | financing_type = "cash" |
| 7 | Parse multi-buyer | Upload multi-buyer → parse | 2+ buyer parties |
| 8 | Parse non-standard | Upload commercial contract → parse | contract_type = "non_standard" |
| 9 | Confirm transaction | POST /api/transactions/:id/confirm | Status = "active" |
| 10 | List transactions | GET /api/transactions | Paginated list |
| 11 | Get transaction detail | GET /api/transactions/:id | Full data + parties |
| 12 | Update transaction | PATCH /api/transactions/:id | Updated + amendment logged |
| 13 | Delete transaction | DELETE /api/transactions/:id | Soft deleted |
| 14 | Add party | POST /api/transactions/:id/parties | Party added |
| 15 | Auth required | GET /api/transactions (no token) | 401 |
| 16 | Data isolation | GET /api/transactions/:other-agent-id | 403 |
| 17 | File size limit | Upload 30MB file | 413 |
| 18 | Invalid file type | Upload .exe | 400 |
| 19 | API retry on failure | Simulate Claude 500 → retry | Success on retry |
| 20 | Parse timeout | Simulate slow response | Timeout error, retry |

### 3.3 AI Accuracy Tests (8 contracts)

| # | Contract | Type | Key Validation |
|---|----------|------|---------------|
| 1 | AL standard residential (text) | Buyer side, conventional | All fields, 90%+ accuracy |
| 2 | AL standard residential (text) | Seller side, FHA | All fields, financing type correct |
| 3 | AL standard residential (scanned) | Buyer side, VA | Vision fallback works, 85%+ |
| 4 | AL standard residential (scanned) | Seller side, conventional | Vision fallback, 85%+ |
| 5 | Cash transaction | No lender | financing_type = "cash", no lender party |
| 6 | Multi-buyer | 2 buyers | Both buyers extracted |
| 7 | Non-standard (commercial) | N/A | contract_type = "non_standard" |
| 8 | Partially executed | Missing signature | fully_executed = false, warning |

### 3.4 E2E Tests (5 scenarios)

| # | Scenario | Steps |
|---|----------|-------|
| 1 | Happy path | Sign up → Upload → Parse → Review → Edit one field → Confirm → Dashboard shows transaction |
| 2 | Edit after confirm | Open transaction → Edit price → Save → Verify amendment |
| 3 | Parse failure retry | Upload → Simulate error → See message → Retry → Success |
| 4 | Empty dashboard | New user → See empty state CTA |
| 5 | Multiple transactions | Upload 3 contracts → Dashboard shows all 3 with correct data |

---

## 4. Phase 2 Tests — Communications Engine

### 4.1 Unit Tests (36 tests estimated)

**Email Composer**
- Buyer-side emails: correct number (4), correct recipients, correct content per role
- Seller-side emails: correct number (4), correct recipients, correct content per role
- Dual-agency emails: merged workflow, correct recipients
- Cash transaction: no lender email generated
- Multi-party naming: "John and Jane Smith" format
- Missing email address: party skipped, warning returned
- Agent signature injected into all emails

**SendGrid Service**
- Send email → success, message ID returned
- Send with attachment → attachment included
- Send to invalid email → error captured
- Webhook processing: delivered event → status updated
- Webhook processing: opened event → timestamp recorded
- Webhook processing: bounced event → status updated
- Retry on failure → queued, retried

**Idempotency**
- Send batch → success
- Resend same batch within 60s → rejected (idempotent)
- Resend after 60s with explicit confirmation → allowed

### 4.2 Integration Tests (16 tests estimated)

| # | Test | Expected |
|---|------|----------|
| 1 | Generate buyer-side emails | 4 emails returned with correct content |
| 2 | Generate seller-side emails | 4 emails returned |
| 3 | Generate dual-agency emails | 3-4 emails, dual disclosure present |
| 4 | Generate for cash transaction | 3 emails (no lender) |
| 5 | Preview emails | GET returns all generated emails |
| 6 | Edit email before send | PATCH updates body → send delivers edited version |
| 7 | Send all emails | POST → all statuses change to "sent" |
| 8 | Send selected emails | POST with selection → only selected sent |
| 9 | SendGrid webhook delivery | POST webhook → communication status updated |
| 10 | SendGrid webhook open | POST webhook → opened_at timestamp set |
| 11 | SendGrid webhook bounce | POST webhook → status = "bounced" |
| 12 | Communication log | GET → all sent communications listed |
| 13 | Double-send prevention | Send same batch twice → second rejected |
| 14 | Missing email warning | Party without email → warning, no email generated |
| 15 | Contract attachment | Lender/attorney emails → PDF attached |
| 16 | Reply-To header | Send email → Reply-To = agent's email |

### 4.3 E2E Tests (4 scenarios)

| # | Scenario |
|---|----------|
| 1 | Full flow: Confirm → Generate → Preview → Edit one → Send All → See in log |
| 2 | Partial send: Generate → Select 2/4 → Send → 2 delivered, 2 draft |
| 3 | Cash flow: Cash transaction → Generate → No lender email → Send |
| 4 | Dual flow: Dual agency → Generate → Verify dual disclosure → Send |

---

## 5. Phase 3 Tests — Milestone Tracking

### 5.1 Unit Tests (32 tests estimated)

**Milestone Generator**
- Financing transaction → correct milestone set (10+ milestones)
- Cash transaction → reduced set (no appraisal/financing)
- Dates calculated correctly from contract dates
- Fallback dates used when specific dates missing
- Conditional milestones based on state config

**Reminder Scheduler**
- Milestone due in 2 days → reminder generated
- Milestone due in 10 days → no reminder
- Completed milestone → no reminder
- Waived milestone → no reminder
- Duplicate reminder prevention → only one sent

**Cascade Calculator**
- Closing date +7 → all closing-relative milestones shift +7
- Recalculated date in past → flagged for attention

**Timezone Handler**
- UTC storage → correct local time conversion
- Reminder at 9:00 AM agent local time → correct UTC scheduling

### 5.2 Integration Tests (12 tests estimated)

| # | Test | Expected |
|---|------|----------|
| 1 | Transaction confirm → milestones created | Correct milestones with correct dates |
| 2 | Cash transaction milestones | No appraisal/financing milestones |
| 3 | Reminder job fires | Milestone due in 2 days → email queued |
| 4 | Complete milestone → follow-ups | Follow-up emails generated for correct parties |
| 5 | Waive milestone → no more reminders | Waived status stops reminder generation |
| 6 | Overdue detection | Past-due milestone → marked overdue, agent notified |
| 7 | Closing date cascade | Change closing date → downstream milestones updated |
| 8 | Custom milestone | Agent adds custom → appears in timeline |
| 9 | Complete already-complete | Idempotent → no duplicate follow-ups |
| 10 | Out-of-order completion | Complete appraisal before inspection → both work |
| 11 | Multiple transactions | 3 transactions with milestones → all tracked independently |
| 12 | Notification feed | Upcoming milestones → appear in notification bell |

---

## 6. Phase 4 Tests — Inspection Analysis

### 6.1 Unit Tests (24 tests estimated)

**Inspection Analyzer**
- Standard report → findings extracted with severity
- All severity levels assigned correctly
- Cost ranges provided per finding
- Safety items ranked above non-safety regardless of cost
- Executive summary generated
- Client summary is non-technical
- Safety category checklist present even for clean report

**Report Processing**
- Text PDF → full extraction
- Large report (60+ pages) → chunked correctly
- Scanned report → vision fallback
- Short text (< 5K chars) → warning about image-heavy report

### 6.2 Integration Tests (8 tests estimated)

| # | Test | Expected |
|---|------|----------|
| 1 | Upload + analyze | Findings extracted, ranked, costed |
| 2 | Large report (60 pages) | Completes < 90 seconds |
| 3 | Clean report | Risk = "low", recommendation = "proceed_as_is" |
| 4 | Critical findings | Safety items first, appropriate recommendation |
| 5 | Client summary email | Non-technical, includes disclaimer, sent via email system |
| 6 | Repair status tracking | Status updates work, follow-ups generated |
| 7 | Milestone integration | Analysis complete → inspection milestone marked done |
| 8 | Scanned report fallback | Image-heavy report → warning + vision analysis |

---

## 7. Phase 5 Tests — Integration & Launch

### 7.1 Full Lifecycle E2E Tests (4 scenarios)

Each scenario tests the COMPLETE flow from account creation through transaction closing. See Phase 5 spec for detailed step-by-step scenarios:

1. **Buyer-side financing** (27 steps)
2. **Seller-side cash** (condensed lifecycle)
3. **Dual-agency** (combined workflow)
4. **Error recovery** (failures at each stage)

### 7.2 Security Tests

| Test | Method | Expected |
|------|--------|----------|
| Unauthenticated access | Call APIs without token | 401 on all endpoints |
| Cross-agent access | Agent A → Agent B's data | 403 |
| SQL injection | Malicious input in all text fields | Parameterized queries prevent |
| XSS | Script tags in input fields | Sanitized, not executed |
| File upload exploitation | Upload malicious file types | Rejected |
| S3 URL expiry | Access signed URL after 15 min | Expired, access denied |
| CSRF | Cross-site request | Blocked by CORS + token |
| Rate limiting | 100 requests/minute to single endpoint | Rate limited after threshold |

### 7.3 Performance Tests

| Test | Tool | Target |
|------|------|--------|
| Dashboard load (100 transactions) | k6/Locust | < 2 seconds |
| Transaction detail load | k6/Locust | < 500ms |
| Contract parse | Manual timing | < 30 seconds |
| Email generation (4 emails) | Manual timing | < 15 seconds |
| Inspection analysis | Manual timing | < 60 seconds |
| Concurrent agents (10) | Locust | All operations within 2x solo time |
| File upload (10MB) | Manual timing | < 5 seconds |

### 7.4 Compatibility Tests

| Browser/Device | Test |
|---------------|------|
| Chrome (latest) | Full E2E |
| Firefox (latest) | Full E2E |
| Safari (latest) | Full E2E |
| Edge (latest) | Full E2E |
| iPad (Safari) | Responsive layout + core flows |
| iPhone (Safari) | Responsive layout + core flows |
| Android (Chrome) | Responsive layout + core flows |

---

## 8. Test Data Requirements

| Data | Count Needed | Source |
|------|-------------|--------|
| Alabama residential purchase agreements (text PDF) | 3+ | Real contracts (redacted) or realistic samples |
| Alabama residential purchase agreements (scanned) | 2+ | Scanned versions of above |
| Cash purchase agreement | 1+ | Real or sample |
| Multi-buyer purchase agreement | 1+ | Real or sample |
| Non-standard contract (commercial) | 1+ | Sample |
| Home inspection reports (standard) | 3+ | Real reports (redacted) |
| Home inspection reports (image-heavy) | 1+ | Scanned report |
| Home inspection report (clean / minimal issues) | 1+ | Report with no major findings |

---

## 9. Defect Management

### 9.1 Severity Definitions

| Severity | Definition | Response Time | Fix Timeline |
|----------|-----------|---------------|-------------|
| **Critical** | System down, data loss, security breach, email sent to wrong person | Immediate | Same day |
| **High** | Major feature broken, incorrect data displayed, wrong emails generated | 4 hours | 1-2 days |
| **Medium** | Feature partially works, UI display issue, minor calculation error | 24 hours | Current sprint |
| **Low** | Cosmetic, typo, minor UX improvement | 1 week | Next sprint |

### 9.2 Bug Report Template

```
Title: [Brief description]
Severity: Critical / High / Medium / Low
Phase: 1 / 2 / 3 / 4 / 5
Steps to Reproduce:
1. ...
2. ...
3. ...
Expected Result: ...
Actual Result: ...
Environment: Local / Staging / Production
Screenshots: [if applicable]
```

---

## 10. Test Completion Criteria (Per Phase)

Every phase must meet ALL of the following before being marked complete:

| Criteria | Threshold |
|----------|----------|
| Unit test pass rate | 100% |
| Integration test pass rate | 100% |
| E2E test pass rate | 100% |
| AI accuracy tests pass | Per-phase targets met |
| Performance tests pass | All within target |
| Critical/High bugs | 0 open |
| Medium bugs | < 3 open (documented, scheduled) |
| Code coverage (backend) | ≥ 80% |
| Code coverage (frontend) | ≥ 70% |
| Security tests pass | 0 critical/high findings |

---

*Master Test Plan — maintained and updated throughout development.*
