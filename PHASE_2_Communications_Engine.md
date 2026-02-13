# Phase 2: Communications Engine

**Timeline:** Weeks 5-8  
**Status:** Not Started  
**Depends On:** Phase 1 Complete  
**CoV Status:** Verified (see below)

---

## 1. Phase Objective

Build the email generation, preview, approval, and delivery system. When an agent confirms a transaction, the system generates role-specific emails for every party, lets the agent preview and edit them, and sends them via SendGrid with tracking.

**Deliverable:** Agent uploads contract → confirms data → previews AI-generated emails for all parties → approves → emails sent with contract attached → delivery/open tracking visible in dashboard.

---

## 2. Scope

### In Scope
- Email Composer AI Agent (Claude API)
- Email template system (role-specific, representation-side-specific)
- Email preview and editing UI
- Email approval workflow (agent reviews before send)
- SendGrid integration for delivery
- Contract attachment to lender/attorney emails
- Email tracking (sent, delivered, opened, bounced)
- Communication log per transaction
- Buyer-side, seller-side, and dual-agency email workflows
- Cash transaction email workflow (skip lender)
- Multi-party email handling (multiple buyers/sellers)
- Agent email signature configuration

### Out of Scope (This Phase)
- Follow-up emails (Phase 3)
- Milestone-triggered emails (Phase 3)
- Gmail/Outlook direct send integration (future)
- SMS notifications (future)

---

## 3. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-2.1 | As an agent, after confirming a transaction I can generate emails for all parties | Click "Generate Emails" → system produces emails for each party based on representation side |
| US-2.2 | As an agent, I can preview each email before it's sent | Preview shows subject, body, recipient, and attachments for each email |
| US-2.3 | As an agent, I can edit any generated email before sending | Full text editing of subject and body; changes saved |
| US-2.4 | As an agent, I can approve and send all emails at once | "Send All" button sends all approved emails; confirmation shown |
| US-2.5 | As an agent, I can send individual emails selectively | Checkbox per email; only checked emails sent |
| US-2.6 | As an agent, I see the executed contract attached to lender and attorney emails | Attachment indicator visible in preview; contract PDF attached on send |
| US-2.7 | As an agent, I can see email delivery status for each communication | Status shown: sent, delivered, opened, bounced |
| US-2.8 | As an agent, I can view all communications sent for a transaction | Communication log with timestamps, recipients, and status |
| US-2.9 | As an agent, I can configure my email signature | Settings page with name, title, brokerage, license #, phone, email |
| US-2.10 | As an agent, emails are appropriate for my representation side | Buyer-side, seller-side, and dual-agency produce different email sets |
| US-2.11 | As an agent, cash transactions don't generate lender emails | No lender email appears in preview for cash transactions |

---

## 4. Technical Tasks

### 4.1 Email Composer AI Agent (Week 5)

| Task | Description | Estimate |
|------|-------------|----------|
| T-2.1 | Design email composition prompt templates (per role, per side) | 8h |
| T-2.2 | Implement EmailComposer agent service (Claude API) | 6h |
| T-2.3 | Build email context assembler (gather all transaction data for prompt) | 4h |
| T-2.4 | Implement buyer-side email generation (4 emails) | 4h |
| T-2.5 | Implement seller-side email generation (4 emails) | 4h |
| T-2.6 | Implement dual-agency email generation (3-4 emails) | 3h |
| T-2.7 | Handle cash transactions (skip lender) | 2h |
| T-2.8 | Handle multi-party naming in emails | 3h |
| T-2.9 | Agent signature injection into all emails | 2h |

### 4.2 SendGrid Integration (Week 6)

| Task | Description | Estimate |
|------|-------------|----------|
| T-2.10 | SendGrid account setup, domain verification, SPF/DKIM/DMARC | 4h |
| T-2.11 | SendGrid Python SDK integration | 3h |
| T-2.12 | Email sending service with attachment support | 4h |
| T-2.13 | Webhook receiver for delivery/open/bounce events | 4h |
| T-2.14 | Email status tracking (update communications table) | 3h |
| T-2.15 | Email queue (Celery task for async sending) | 3h |
| T-2.16 | Bounce/failure handling and retry logic | 3h |
| T-2.17 | HTML email template (responsive, professional) | 4h |

### 4.3 API Development (Week 6-7)

| Task | Description | Estimate |
|------|-------------|----------|
| T-2.18 | POST /api/transactions/:id/emails/generate — trigger AI generation | 4h |
| T-2.19 | GET /api/transactions/:id/emails/preview — return generated emails | 2h |
| T-2.20 | PATCH /api/transactions/:id/emails/:id — edit email before send | 2h |
| T-2.21 | POST /api/transactions/:id/emails/send — send approved emails | 3h |
| T-2.22 | GET /api/transactions/:id/communications — list all sent emails | 2h |
| T-2.23 | POST /api/webhooks/sendgrid — receive delivery events | 3h |
| T-2.24 | PATCH /api/users/:id/settings — save email signature | 2h |

### 4.4 Frontend Development (Weeks 7-8)

| Task | Description | Estimate |
|------|-------------|----------|
| T-2.25 | Email preview page — card per email with subject, body, recipient | 8h |
| T-2.26 | Inline email editor (rich text or markdown) | 6h |
| T-2.27 | Send controls (send all, send selected, checkbox per email) | 3h |
| T-2.28 | Attachment indicator on lender/attorney emails | 2h |
| T-2.29 | Communication log component on transaction detail | 4h |
| T-2.30 | Email status badges (sent, delivered, opened, bounced) | 3h |
| T-2.31 | Agent settings page (email signature configuration) | 4h |
| T-2.32 | Loading/progress state during email generation | 2h |
| T-2.33 | Success/error notifications after sending | 2h |
| T-2.34 | Integration with transaction flow (confirm → generate → preview → send) | 4h |

---

## 5. Email Generation Specification

### 5.1 Email Composer System Prompt

```
You are a professional real estate email composer. You generate clear, 
warm, and action-oriented emails for real estate transactions.

CONTEXT:
- You will receive full transaction details and the target recipient's role
- Emails should be professional but personable
- Each email should clearly state next steps for that specific party
- Include all relevant dates, amounts, and contact information
- Never include information that a party shouldn't have access to

RULES:
1. Buyer/Seller clients: Warm, congratulatory tone. Clear next steps.
   Reassure them you're managing the process.
2. Lender: Professional, factual. Include all data they need to begin.
   Request confirmation of receipt and processing timeline.
3. Attorney/Title: Professional, comprehensive. Include all party 
   contacts and transaction details. Request to open file.
4. Other agent: Professional, collegial. Confirm terms, share contact
   info, establish communication preferences.
5. For dual agency: Acknowledge dual representation clearly in client emails.
6. Always end with agent's contact information.
7. Subject lines should be clear and include property address.

Return JSON with: { subject, body, recipient_role, attachments_needed }
```

### 5.2 Email Templates by Role and Side

**Buyer-Side Emails:**

| # | Recipient | Subject Pattern | Body Includes |
|---|-----------|----------------|---------------|
| 1 | Buyer (client) | "Congratulations! Your Offer on [Address] Has Been Accepted" | Welcome, earnest money instructions, inspection timeline, key dates, what to expect, agent contact |
| 2 | Mortgage Lender | "Executed Contract — [Address] — [Buyer Name]" | Contract attached, property details, purchase price, financing type, closing date, all party contacts |
| 3 | Attorney/Title | "New Transaction — [Address] — Please Open File" | Contract attached, all party contacts, earnest money amount/deadline, financing type, closing date |
| 4 | Listing Agent | "Contract Confirmation — [Address]" | Confirmation of execution, buyer agent contact, lender info, communication preferences |

**Seller-Side Emails:**

| # | Recipient | Subject Pattern | Body Includes |
|---|-----------|----------------|---------------|
| 1 | Seller (client) | "Contract Update — [Address] — Next Steps" | Confirmation, inspection prep, property access info, key dates, agent contact |
| 2 | Attorney/Title | "New Transaction — [Address] — Please Open File" | Contract attached, all party contacts, payoff info request, closing date |
| 3 | Mortgage Lender | "Executed Contract — [Address] — Appraisal Coordination" | Contract attached, property details, access coordination |
| 4 | Buyer's Agent | "Contract Confirmation — [Address]" | Confirmation, seller agent contact, property access instructions |

### 5.3 HTML Email Template

All emails rendered in a responsive HTML template with:
- Clean, professional header with agent's brokerage branding (optional)
- Body content (AI-generated)
- Agent signature block (name, title, brokerage, license, phone, email)
- Brokerage disclaimers and state-required disclosures in footer
- Unsubscribe link (CAN-SPAM compliance)

---

## 6. Chain-of-Verification: Phase 2

### Step 1: Baseline
Phase 2 adds AI email generation, preview/edit workflow, SendGrid delivery, and tracking.

### Step 2: Self-Questioning

**Q1:** What if a party doesn't have an email address in the extracted data?
**Q2:** How do we prevent accidental double-sending if the agent clicks "Send" twice?
**Q3:** What if SendGrid is down or rejects the email?
**Q4:** Are there legal/compliance issues with AI-generated emails in real estate?
**Q5:** What about email threads — will replies go to the agent or a no-reply address?

### Step 3: Independent Verification

**A1 — Missing Email:** Some parties (especially lenders named on contract) may not have email addresses extracted. The system should show a warning "No email address for [Lender Name]" and either (a) prompt the agent to add it manually, or (b) skip that email. The email should NEVER be sent to a null/empty address.
**Resolution:** Validate recipient email before generating. Show "Add email to send" prompt for missing addresses. Skip email generation for parties without email.

**A2 — Double-Send Prevention:** Implement idempotency. Once emails are sent for a transaction's initial outreach, the "Send" button changes to "Resend" with a confirmation dialog. Each email batch gets a unique idempotency key. The backend rejects duplicate send requests within a 60-second window.
**Resolution:** Idempotency key on send endpoint. UI state change after successful send. Resend requires explicit confirmation.

**A3 — SendGrid Failures:** If SendGrid is unreachable, the system should queue the email and retry. The agent should see "Queued — will retry" status. Max 3 retries over 15 minutes. If all retries fail, status becomes "Failed" with option to retry manually.
**Resolution:** Celery task with retry policy. Clear status communication in UI.

**A4 — Legal Compliance:** AI-generated emails sent on behalf of a licensed real estate agent must include proper identification (agent name, license number, brokerage name). They must not make representations the agent hasn't approved. The preview/approval step is the critical control.
**Resolution:** Agent ALWAYS reviews and approves before send. Emails include mandatory disclaimers. Agent can edit any content. No fully autonomous emails in V1.

**A5 — Reply Handling:** Emails should have the agent's actual email as the Reply-To address so replies go directly to the agent. The From address can be system (notifications@domain.com) but Reply-To must be the agent's personal email.
**Resolution:** Configure SendGrid with From: system address, Reply-To: agent's email. This is transparent and keeps conversation in the agent's inbox.

### Step 4: Confidence Check
**Confidence: 97%** — All edge cases handled. The preview/approval workflow is the key safety mechanism.

### Step 5: Implement
Proceed with Phase 2 as specified. Incorporate missing email handling, double-send prevention, and reply-to configuration.

---

## 7. Definition of Done (Phase 2)

| Criteria | Verification |
|----------|-------------|
| Buyer-side emails generated correctly (4 emails) | Manual test with buyer transaction |
| Seller-side emails generated correctly (4 emails) | Manual test with seller transaction |
| Dual-agency emails generated correctly | Manual test with dual transaction |
| Cash transaction skips lender email | Manual test with cash transaction |
| Multi-party names handled correctly | Manual test with 2-buyer contract |
| Agent can preview all emails before sending | E2E test |
| Agent can edit email subject and body | E2E test |
| Agent can send all or selected emails | E2E test |
| Contract PDF attached to lender/attorney emails | Verify received email |
| Emails delivered via SendGrid | Verify delivery in SendGrid dashboard |
| Open tracking works | Open an email, verify status updates |
| Bounce handling works | Test with invalid email address |
| Communication log shows all sent emails | Manual test |
| Agent signature included in all emails | Manual test |
| Reply-To set to agent's email | Verify email headers |
| Missing email address shows warning, not error | Test party without email |
| Double-send prevented | Click send twice rapidly |
| SendGrid failure queues for retry | Simulate SendGrid outage |

---

## 8. Test Plan

### 8.1 Unit Tests

| Test Area | Tests |
|-----------|-------|
| EmailComposer agent | Generates correct emails per role/side; handles missing parties; handles multi-party names |
| Email context assembler | Builds complete context from transaction data; handles null fields |
| SendGrid service | Sends email; attaches files; handles errors; processes webhooks |
| Email validation | Rejects empty recipients; validates email format; checks required fields |

### 8.2 Integration Tests

| Test | Steps | Expected Result |
|------|-------|----------------|
| Buyer-side full flow | Create buyer transaction → generate → preview → send | 4 emails sent, statuses tracked |
| Seller-side full flow | Create seller transaction → generate → preview → send | 4 emails sent, statuses tracked |
| Dual-agency flow | Create dual transaction → generate | Appropriate combined emails generated |
| Cash transaction | Create cash transaction → generate | No lender email generated |
| Edit before send | Generate → edit subject/body → send | Edited version sent (not original) |
| Selective send | Generate 4 → select 2 → send | Only 2 sent, 2 remain as drafts |
| Missing email | Party without email → generate | Warning shown, email skipped |
| SendGrid webhook | Simulate delivery event → check DB | Communication status updated |
| Bounce handling | Send to invalid address → webhook | Status set to "bounced" |
| Double-send | Send same batch twice quickly | Second request rejected or idempotent |

### 8.3 Email Quality Tests

| Test | Criteria |
|------|----------|
| Buyer welcome email tone | Warm, congratulatory, clear next steps, no jargon |
| Lender email completeness | All required data present: price, address, financing type, dates, contacts |
| Attorney email completeness | All party contacts, earnest money details, closing date |
| Other agent email | Professional, collegial, confirms terms |
| Multi-buyer naming | "Dear John and Jane Smith" not "Dear John Smith" |
| Subject lines | Include property address, clear purpose |
| Signature | Agent name, brokerage, license, phone, email all present |
| Disclaimers | State-required disclosures present in footer |

### 8.4 E2E Tests

| Test | Flow |
|------|------|
| Full happy path | Upload → Parse → Confirm → Generate Emails → Preview → Send All → See in log |
| Edit and send | Generate → Edit one email → Send → Verify edited version delivered |
| Partial send | Generate → Select 2 of 4 → Send → 2 delivered, 2 remain as drafts |

---

## 9. Phase 2 Success Criteria

| Metric | Target | How Measured |
|--------|--------|-------------|
| All user stories completed | 11/11 | Story acceptance criteria |
| Email generation time (all parties) | < 15 seconds | Performance test |
| Email delivery success rate | > 98% | SendGrid metrics |
| Correct emails generated per representation side | 100% | Integration tests |
| No email sent without agent approval | 100% | Workflow enforcement |
| Agent can go from confirmed transaction to emails sent in < 5 minutes | Verified | Manual test timing |
| Open tracking accuracy | > 90% (for HTML-capable clients) | SendGrid metrics |

---

*Phase 2 Complete → Proceed to Phase 3: Milestone Tracking & Follow-Ups*
