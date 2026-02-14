# Phase 3: Multi-Party Transparency Portal

**Timeline:** Weeks 7-9
**Status:** Not Started
**Depends On:** Phase 1 (health score, milestones, action items, file model) + Phase 2 (email delivery via Resend, notification system)
**CoV Status:** Verified (see Section 2)

---

## 1. Phase Overview

### Goal

Build a multi-party transparency portal that gives every party on a transaction a read-only (with targeted upload and task-completion capability) view of what is relevant to them -- via unique, unguessable links that require no account creation. Each party sees only the milestones, documents, action items, and contact information appropriate to their role. The portal eliminates the constant back-and-forth of "where are we in the process?" communications by giving every stakeholder a living, always-current view of their transaction.

The platform shift is from passive data storage to proactive deal protection. Phase 1 gave the agent a Today View with smart action items and milestone templates. Phase 2 wired up real email delivery with automated reminders and escalation chains. Phase 3 extends the platform outward: instead of the agent being the sole window into deal progress, every party on the transaction gets their own curated, real-time view. This eliminates an estimated 70% of "where are we?" emails that agents currently field.

**Core Capabilities:**

- **Unique portal links:** Each party receives a UUID v4 token-based URL. No login, no account, no password. The same model used by DocuSign, Calendly, and Dotloop -- link-based access that is familiar to every real estate participant.
- **Role-based views:** Buyers see buyer-relevant data. Lenders see loan-relevant data. Inspectors see inspection-relevant data. Attorneys see everything needed for closing coordination. No party ever sees data outside their role scope.
- **Document access:** Parties can view documents relevant to their role. Document visibility is controlled by an explicit role array on each file record, configurable by the agent.
- **Action buttons:** Parties can mark their assigned action items as complete and upload requested files (pre-approval letters, inspection reports, title searches, etc.), triggering instant notifications back to the agent.
- **File upload with quarantine:** All party-uploaded files go through a quarantine pipeline -- validated for type, size, and magic bytes, stored in a quarantine S3 prefix, and held for agent review before becoming visible to other parties.
- **Real-time sync:** When a party completes a task or uploads a document, the agent sees it immediately in their transaction detail view. When the agent updates milestones or documents, the portal reflects changes within the cache TTL window.
- **Mobile-first design:** Industry data shows 65-75% of email opens happen on mobile devices. A party receiving a portal link in email will almost certainly tap it on their phone first. The portal is designed for 375px screens first and enhanced for larger viewports.

**Deliverable:** After creating a transaction and adding parties, the agent can generate portal links for every party with one click. Each party clicks their link (received via Phase 2 email) and sees a clean, branded page showing transaction progress, their action items, relevant documents, and a way to contact their agent -- all without creating an account.

### Timeline: Weeks 7-9

| Week | Focus | Key Deliverables |
|------|-------|-----------------|
| Week 7 | Token system, data model, API endpoints, role-based query layer | Portal tokens table, portal access logs table, action items table, role-scoped query functions, all authenticated (agent) and public (portal) API endpoints functional with integration tests |
| Week 8 | Portal frontend, role-based views, file upload, document viewer | Public portal pages rendering per-role views, document viewer with signed S3 URLs, inline file upload with quarantine flow, action item completion via portal |
| Week 9 | Agent-side management UI, email integration, mobile optimization, full testing | Agent can generate/revoke/regenerate links, review uploaded files, manage document visibility, portal links included in Phase 2 emails, mobile testing on iOS Safari and Android Chrome, full regression suite |

### Depends On

- **Phase 1:** Transaction data model (status, property fields, closing_date), party model (role, name, email, phone, company), milestone model (type, due_date, status, responsible_party_role), file model (name, content_type, url), health score calculation (progress percentage for the portal progress bar), action items system (the Phase 1 `action_items` table is extended for portal use).
- **Phase 2:** Email delivery via Resend (portal links are distributed by including them in transaction emails and follow-up communications), notification system (agent receives notifications when parties complete tasks or upload files), Celery task infrastructure (for portal access log cleanup and token expiration jobs).

---

## 2. Chain of Verification (CoV)

### Step 1: Baseline

Phase 3 delivers a public-facing portal where each party on a transaction can view their role-scoped data, see action items, upload requested documents, mark tasks complete, and track progress -- all via a unique token-based link with no authentication required. The portal must be secure against enumeration attacks, enforce strict role-based data scoping at the query layer, handle file uploads safely via quarantine, and render correctly on mobile devices used by non-technical parties.

### Step 2: Self-Questioning and Independent Verification

| # | Question | Risk Level | Resolution |
|---|----------|------------|------------|
| Q1 | **What if someone guesses or brute-forces a portal token?** UUID v4 tokens have 122 bits of randomness, yielding 5.3 x 10^36 possible values. Brute-forcing is computationally infeasible at current computational capabilities. However, sequential or predictable token generation would be vulnerable, and a determined attacker could still attempt automated enumeration. | **High** | Use Python's `uuid.uuid4()` which relies on `os.urandom()` (cryptographically secure random number generator). Implement rate limiting on all `/api/portal/*` endpoints: 30 requests per minute per token, 100 requests per minute per IP address. Log and alert on repeated failed token lookups from the same IP (threshold: 10 failures within 5 minutes, triggers a log warning and optional webhook to agent). Return identical 404 responses for invalid, expired, and revoked tokens -- the response body, status code, headers, and response time must be indistinguishable to prevent enumeration via timing or content analysis. Never include the token value itself in server logs; use the `portal_tokens.id` (internal UUID) for log references. |
| Q2 | **What if a party shares their portal link with unauthorized people?** This is inherent to any link-based access system. A buyer who shares their link with a friend gives that friend read access to buyer-scoped transaction data. The shared buyer link does NOT expose seller data, lender data, or agent-internal data -- exposure is strictly limited to the role's visible scope. | **Medium** | Accept this as a known and acceptable trade-off of link-based access (same model as DocuSign, Dotloop, Google Docs "anyone with the link"). Mitigations: (a) The agent can regenerate (revoke + create new) any party's token at any time if unauthorized sharing is suspected. (b) Add a visible footer on every portal page: "This link is unique to you. Do not share it." (c) Log all portal access with IP address and user-agent for audit trail -- if the agent sees access from 15 different IPs for one party, that is a signal. (d) The portal shows only role-scoped data, so the blast radius of a shared link is limited to what that specific party role is allowed to see. (e) Uploaded files go through quarantine, so even if an unauthorized person has the link, they cannot inject files that bypass agent review. |
| Q3 | **What if a party's portal token expires while the transaction is still active?** A party checking their portal at 11 PM the night before closing must still have access. Time-based expiry during an active transaction creates support burden and confusion -- the agent gets calls asking why the link stopped working. | **High** | Tokens remain active for the lifetime of the transaction. There is no time-based expiry while the transaction is in an active status (`draft`, `active`, `confirmed`, `pending_close`). Tokens are invalidated only when: (a) the transaction status changes to `closed` -- at that point, `expires_at` is set to `now() + 90 days` to provide an archive access window; (b) the transaction is soft-deleted -- all tokens immediately revoked; (c) the agent explicitly regenerates or revokes the token; (d) the party is removed from the transaction -- token cascades to revoked. After the 90-day archive window, tokens return 404 on access. A scheduled Celery task (daily) cleans up expired tokens. |
| Q4 | **What documents should each party role see vs. not see?** Document visibility must be explicitly scoped. A buyer should never see the seller's closing statement. A lender should not see inspection details unless the agent specifically shares them. An inspector should see nothing beyond the inspection scope. If visibility is implicit (guessed from document type), edge cases will leak data. | **High** | Define a `visibility` column on the `files` table as a JSON array of role strings (e.g., `["buyer", "lender", "attorney"]`). When the agent uploads a document, they set visibility explicitly (with sensible defaults based on document type). When a party uploads a file via the portal, the file enters quarantine with `visibility = NULL` (agent-only until reviewed). The portal query layer filters files by intersecting the requesting party's role against the file's visibility array. If `visibility IS NULL`, the file is visible only to the agent (not to any portal user). The agent can modify visibility at any time via the `PATCH /api/transactions/{id}/files/{file_id}/visibility` endpoint. Default visibility rules by document type are configurable but always overridable. |
| Q5 | **What if a party uploads a malicious file through their portal?** The portal upload is the only write operation available to unauthenticated users via a token. Malicious files (executables disguised as PDFs, oversized files, zip bombs, polyglot files) are a real risk. An attacker with a valid portal token could attempt to upload harmful content. | **High** | Enforce strict multi-layer file validation: (a) Allowed MIME types: `application/pdf`, `image/jpeg`, `image/png`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (DOCX) only. (b) Maximum file size: 25 MB, enforced at both the reverse proxy (nginx) and application layer. (c) Server-side MIME validation using `python-magic` to inspect file magic bytes -- do not trust the `Content-Type` header from the client. (d) All party uploads are stored in a quarantine S3 prefix (`/quarantine/{transaction_id}/`) separate from agent-uploaded files. (e) Files remain in quarantine (`files.quarantine = TRUE`) until the agent reviews and approves them. (f) Quarantined files are NOT visible to any portal users (including the uploader) -- they see only a confirmation that the file was received and is pending review. (g) S3 lifecycle policy auto-deletes quarantined files older than 30 days (for abandoned/rejected uploads). (h) When the agent approves a file, it is moved from the quarantine prefix to the permanent prefix, `quarantine` flag set to `FALSE`, and `visibility` array set by the agent. |
| Q6 | **Should parties see each other's information? For example, should a buyer see the seller's email?** In standard real estate transactions, buyers and sellers do NOT communicate directly -- all communication flows through their respective agents. However, attorneys need everyone's contact info for closing coordination, and lenders may need agent contacts for the other side. | **High** | Implement strict role-based contact visibility enforced at the query layer. **Buyers** see: their agent's name, phone, and email only. **Sellers** see: their agent's name, phone, and email only. **Lenders** see: buyer agent contact, seller agent contact, and attorney/title contact (for closing coordination). **Attorneys/Title** see: all party contact information (names, emails, phones) -- they need this for closing coordination. **Inspectors** see: listing agent name and phone only (for property access). **Other agents** (buyer's agent or seller's agent) see: the counterpart agent's contact info. **Critical rule:** No party ever sees another principal's (buyer/seller) direct contact information through the portal. This is enforced in the `portal_contacts_service.py` query layer, not in the frontend. The frontend receives only the data it is allowed to display. |
| Q7 | **What about the mobile experience? Most parties will open portal links on their phones.** A desktop-only design would fail in production. Agents send portal links via email; parties tap the link on their phone. If the portal does not render correctly on a 375px screen, the feature is effectively broken for the majority of users. | **High** | Design mobile-first. All CSS starts at 375px and scales up. Specifics: (a) Single-column layout below 768px. (b) Touch-friendly tap targets: minimum 44x44px for all interactive elements per WCAG 2.5.5 Target Size. (c) Progress bar collapses to a compact horizontal bar with percentage label on mobile; expands to include milestone labels on desktop. (d) Document viewer uses a signed S3 URL that opens in the browser's native PDF viewer (or a lightweight inline viewer for images). (e) Upload uses the device's native file picker, which on mobile includes camera and file system access. (f) Test on iOS Safari (iPhone 13 and newer) and Android Chrome (Pixel and Samsung Galaxy) as primary targets. (g) No horizontal scrolling at any breakpoint. (h) Maximum content width of 640px centered on desktop with 16px horizontal padding on mobile. (i) System font stack for consistent rendering: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`. |
| Q8 | **What if the agent revokes a party's portal access?** An agent may need to revoke access if a deal falls through, a party is replaced, or unauthorized sharing is suspected. Revocation must be immediate and complete -- no cached pages, no stale API responses. | **Medium** | When the agent regenerates a token, the old token's `revoked_at` is set to `now()`. Any subsequent request with the old token returns `404 { "error": "Portal not found" }` -- the generic message gives no indication of whether the token was revoked vs. never existed vs. expired. Cache entries for the old token are explicitly busted (all Redis keys with the old `token_id` prefix are deleted). The agent can optionally generate a new token for the same party (revoke + recreate), or revoke without regenerating (party loses access entirely). The API returns the new token URL if regenerating, or a 204 if simply revoking. |
| Q9 | **How do we handle the case where a party is removed from the transaction?** If a lender is replaced mid-transaction, the old lender's portal token must stop working, and the new lender needs a fresh token. Party removal is a Phase 1 capability -- the portal must respect it without orphaning tokens. | **Medium** | When a party is removed (soft-deleted or hard-deleted) from a transaction, all associated portal tokens are invalidated by setting `revoked_at = now()`. This is implemented via a SQLAlchemy `after_delete` or `after_update` event listener on the Party model, or explicitly in the `party_service.py` deletion logic. When a new party is added in the same role, the agent must explicitly generate a new portal token for them -- tokens are never auto-generated on party creation (the agent controls when and whether to share portal access). If the old party attempts to access their portal after removal, they see the generic "Portal not found" error page. |
| Q10 | **What if two parties have the same email address? For example, a married couple buying together -- John Smith and Jane Smith both listed as buyers with the same email.** Each party is a separate record in the `parties` table, but portal links are distributed via email. Sending two different portal links to the same email could confuse the recipients. | **Medium** | Each party ALWAYS gets their own unique token and their own portal view, regardless of shared email addresses. Each token resolves to exactly one party record, so there is no ambiguity on the portal side. For email distribution: when sending portal links, the system queries for parties with the same email address on the same transaction. If duplicates are found, a SINGLE email is sent containing ALL portal links for that email address, with clear labels: "John Smith's Portal: [link]" and "Jane Smith's Portal: [link]". The Phase 2 email template system must handle this case with a conditional block that renders multiple links when applicable. The email subject line should reflect this: "Your Portal Links for 123 Main St" (plural). |
| Q11 | **What about accessibility? The portal must be usable by non-technical people.** Portal users range from tech-savvy lenders who use transaction management software daily, to elderly home sellers who may struggle with anything beyond basic email. The portal must be usable by someone who has never used a web application beyond email. | **Medium** | Design for the least technical user. Specifics: (a) No jargon -- use "Your Tasks" not "Action Items Queue", use "Upload Your Pre-Approval Letter" not "Attach Document". (b) Large, clear typography: minimum 16px body text, 20px headings. (c) High contrast colors: WCAG AA compliance minimum, target AAA where possible. (d) Semantic HTML for screen reader compatibility: proper heading hierarchy, ARIA labels on interactive elements, role attributes on landmarks. (e) Clear, descriptive button labels that state the action: "Upload Your Pre-Approval Letter" not "Upload". (f) Status indicators use both color AND text/icons -- not color alone, for colorblindness consideration. A green checkmark says "Complete" next to it; a red circle says "Overdue" next to it. (g) No infinite scrolling -- simple, well-separated sections with clear headings. (h) Loading states with clear text: "Loading your transaction details..." not a spinner alone. (i) Error messages in plain language: "Something went wrong. Please try again, or contact your agent at [phone]." |
| Q12 | **Do portal views count toward our API rate limits? How do we handle portal traffic at scale?** Portal endpoints are public (no auth). A busy agent with 50 active transactions, each with 6 parties, means 300 potential portal users. Each portal page load hits multiple API endpoints. Volume could spike around milestone deadlines when parties check status frequently. | **Medium** | Portal endpoints are rate-limited separately from authenticated agent API endpoints. Portal rate limits: 30 requests/minute per token, 100 requests/minute per IP. Portal responses are aggressively cached in Redis: transaction overview cached for 60 seconds, milestone data cached for 30 seconds, document lists cached for 120 seconds, contact data cached for 300 seconds, action items cached for 15 seconds. Cache is busted explicitly when the agent makes changes (milestone update, file upload, visibility change, etc.). Portal API does NOT trigger any Claude API calls (no AI processing on portal views). Static assets (CSS, JS, images) should be served from a CDN in production. The portal frontend bundle should be code-split from the authenticated app bundle to minimize initial load size. |

### Step 3: Confidence Check

**Confidence: 94%** -- The token security model is sound (UUID v4 with cryptographic randomness + rate limiting + identical error responses). The main risk areas are: (a) file upload security, mitigated by the quarantine pipeline with magic byte validation; (b) the complexity of role-based visibility rules across 6+ party roles, mitigated by explicit visibility arrays on documents and a thoroughly tested query layer with per-role integration tests; (c) mobile rendering quality, which requires manual testing on real devices and cannot be fully automated. The 6% gap is operational: real-world testing will surface edge cases in role-based scoping that our test fixtures may not anticipate, and mobile rendering across the fragmented Android ecosystem is inherently unpredictable.

### Step 4: Implement

Proceed with Phase 3 as specified. Incorporate all resolutions from the CoV analysis into the implementation, particularly: quarantine-based file uploads with magic byte validation, explicit document visibility arrays with agent override capability, aggressive Redis caching for portal endpoints with explicit cache busting, mobile-first responsive design tested on real iOS and Android devices, and identical 404 responses for all token failure modes.

---

## 3. Detailed Requirements

### 3.1 Portal Token System

**Token Specification:**

- Tokens are UUID v4 values generated via Python's `uuid.uuid4()` (backed by `os.urandom()`, cryptographically secure random number generator)
- Token format in URL: `/portal/{uuid}` (e.g., `/portal/a1b2c3d4-e5f6-7890-abcd-ef1234567890`)
- One active token per party per transaction at any time (enforced at the application layer with a check-before-create pattern, backed by a partial unique index on `party_id WHERE revoked_at IS NULL` as a database-level safety net)
- Token record stores: `party_id`, `transaction_id`, `token` (the public UUID), `created_at`, `updated_at`, `revoked_at`, `expires_at`, `last_accessed_at`
- The `token` field is the value exposed in URLs. The `id` field is the internal primary key used for log references, cache keys, and foreign key relationships. The token value itself never appears in server logs.

**Token Lifecycle:**

| Event | Action | Notes |
|-------|--------|-------|
| Agent clicks "Generate Portal Link" for a party | New `portal_tokens` row created with `revoked_at = NULL`, `expires_at = NULL`. If a previous active token exists for that party, it is revoked first (set `revoked_at = now()`). | Returns the portal URL to the agent for copying or emailing. |
| Agent clicks "Generate All Portal Links" | Tokens created for all parties on the transaction that have `portal_enabled = TRUE` and do not already have an active (non-revoked, non-expired) token. | Returns a list of all generated tokens with party names and roles. |
| Party accesses portal via GET `/api/portal/:token` | `last_accessed_at` updated on the token record. Access logged in `portal_access_logs` (IP, user-agent, endpoint, timestamp). | The `last_accessed_at` update is fire-and-forget (async) to avoid slowing the portal response. |
| Agent regenerates a token | Old token's `revoked_at` set to `now()`. Old token's Redis cache keys deleted. New token created for the same party. | Agent receives the new portal URL. Old URL immediately returns 404. |
| Agent revokes without regenerating | Token's `revoked_at` set to `now()`. Redis cache keys deleted. | Party loses access entirely. No new token is created. |
| Party removed from transaction | All tokens for that party have `revoked_at` set to `now()`. | Triggered by party deletion logic in `party_service.py`. |
| Transaction status changes to "closed" | All active tokens for the transaction have `expires_at` set to `now() + 90 days`. | 90-day archive access window. Parties can still view (read-only) during this period. Upload and task-completion actions are disabled during archive mode. |
| Transaction soft-deleted | All tokens for the transaction have `revoked_at` set to `now()`. | Immediate full revocation. No archive period. |
| 90 days after transaction closed | Token lookup returns 404 (expired). | Cleanup job runs daily to delete expired token rows older than 90 days past their `expires_at`. |

**Security Measures:**

- Rate limiting: 30 requests/minute per token, 100 requests/minute per IP on all `/api/portal/*` endpoints. Implemented via Redis sliding window counters.
- Identical 404 response for invalid, revoked, and expired tokens: `{ "error": "Portal not found" }` with status code 404. No variation in response body, headers, or response time.
- All portal access logged in `portal_access_logs` table (IP address supporting IPv6 via VARCHAR(45), user_agent, token_id, endpoint, timestamp).
- Alert threshold: 10+ failed token lookups from the same IP within 5 minutes triggers a `WARNING` level log entry. Future enhancement: webhook to agent.
- Tokens never appear in server application logs. All log entries reference `portal_tokens.id` (internal UUID), not the `token` value.
- HTTPS required for all portal endpoints (enforced at the reverse proxy / load balancer level).
- No session cookies -- every request is authenticated solely by the token in the URL path. No server-side session state.
- CORS configured to allow requests from the portal's origin domain only.

### 3.2 Role-Based Views

Each party role has a precisely defined scope of visible data. The portal backend enforces these rules at the query level -- the frontend never receives data outside the party's scope. Even if someone inspects network requests or modifies the frontend JavaScript, they cannot access data that the backend does not return.

#### Buyer View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Current status label + visual progress bar (percentage toward closing) | Progress calculated as: (completed milestones visible to buyer) / (total milestones visible to buyer) * 100 |
| **Action Items** | Earnest money delivery, inspection scheduling, pre-approval letter upload, walkthrough scheduling, closing document review | System-generated + agent-created items where `party_id` matches the buyer's party record |
| **Milestones** | Earnest money deadline, inspection deadline, appraisal (status only -- not detailed results), financing contingency, final walkthrough, closing date | Shows due date, status (upcoming/complete/overdue), days remaining. Does NOT show milestones assigned to other roles unless they are general transaction milestones. |
| **Documents** | Executed contract, inspection report (only after agent approves sharing and sets buyer visibility), closing disclosure, any other documents where visibility array includes "buyer" | View via signed S3 URL. Upload area for items requested from buyer. |
| **Contact** | Agent name, phone, email. "Contact Your Agent" button (mailto: and tel: links). | Cannot see: seller contact, seller agent contact, lender details, attorney contact |
| **Cannot See** | Seller's contact information, seller's personal details, internal agent notes, commission data, listing price history, other parties' action items, seller-side milestones |

#### Seller View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Current status + visual progress bar | Same calculation method as buyer, scoped to seller-visible milestones |
| **Action Items** | Property access scheduling for inspection, property access for appraisal, repair response (after inspection), closing preparation, key/remote handoff | System-generated + agent-created items scoped to seller |
| **Milestones** | Inspection (property access needed), appraisal (access coordination), repair request/response window, closing preparation, closing date | Shows what requires seller action |
| **Documents** | Executed contract, repair request (if any), repair response, seller-visible documents per agent configuration | View, upload area for requested items |
| **Contact** | Agent name, phone, email. "Contact Your Agent" button. | Cannot see: buyer contact, buyer financial info, lender details |
| **Cannot See** | Buyer's financial information, lender details, buyer's pre-approval specifics, internal agent notes, commission data, buyer's action items, buyer-side milestones |

#### Lender View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Loan-relevant status (pre-approval, appraisal ordered, appraisal complete, clear to close, closed) | Simplified status focused on the loan lifecycle. The progress bar reflects only loan-related milestones. |
| **Action Items** | Order appraisal, provide commitment letter, provide clear-to-close letter, upload pre-approval letter | Loan-specific items only |
| **Milestones** | Appraisal ordered, appraisal complete, financing contingency deadline, clear to close, closing date | Only loan-related milestones visible |
| **Documents** | Executed contract, appraisal report (after completion and agent approval) | Upload area for: pre-approval letter, commitment letter, clear-to-close letter |
| **Contact** | Buyer agent contact, seller agent contact, attorney/title contact (for closing coordination) | Sees agent and attorney contacts for coordination. Does NOT see buyer/seller personal contact. |
| **Cannot See** | Inspection details, repair negotiations, party personal contact info beyond agents and attorney, internal agent notes, commission data, non-loan milestones |

#### Attorney / Title View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Full status + progress bar | Attorney needs complete picture for closing coordination |
| **Action Items** | Open title file, title search, survey ordering, closing disclosure preparation, closing scheduling, recording coordination | Title/attorney-specific items |
| **Milestones** | All milestones visible | Attorney needs the full timeline for closing coordination |
| **Documents** | All documents except agent internal notes | Upload area for: title search results, survey, closing disclosure, settlement statement |
| **Contact** | All party contact information (names, emails, phones, companies) | Attorney needs to coordinate with everyone for closing |
| **Cannot See** | Commission data, internal agent notes, agent-to-agent private communications |

#### Inspector View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Not shown (irrelevant to the inspector's scope) | Inspector only needs to know about the inspection itself |
| **Action Items** | "Upload inspection report" (single action item, possibly supplementary items for radon test, wood infestation report) | Minimal scope -- inspector's only portal interaction is uploading reports |
| **Milestones** | Inspection milestone only (date, time, status) | No other milestones visible |
| **Documents** | None by default (inspector uploads only) | Upload area for: inspection report, radon test results, wood infestation report |
| **Contact** | Listing agent name and phone (for property access coordination). Property address prominently displayed with any access instructions. | Cannot see any other party information |
| **Cannot See** | Financial data, other milestones, other party information, purchase price, contract details, any documents not explicitly shared with the inspector role |

#### Other Agent (Buyer's Agent or Seller's Agent) View

| Section | Visible Data | Notes |
|---------|-------------|-------|
| **Transaction Status** | Full status + progress bar | Co-operating agent needs the full picture |
| **Action Items** | Items relevant to their side (buyer agent sees buyer-side items, seller agent sees seller-side items) | Scoped to their representation side |
| **Milestones** | Full milestone timeline with all dates and statuses | Both agents need to track the full timeline to coordinate |
| **Documents** | All non-confidential documents (contract, inspection report, appraisal, closing docs) | Cannot upload -- uploads go through the listing/transaction-owning agent |
| **Contact** | Party contact info for their side + counterpart agent contact | Buyer agent sees buyer contact + seller agent contact. Seller agent sees seller contact + buyer agent contact. |
| **Cannot See** | Commission data, internal notes from the other agent, the other side's private communications |

**Role-Based Scoping Implementation:**

The role scoping is implemented as a set of Python functions in `backend/app/services/portal_scope_service.py`. Each function accepts the party's role string and returns the appropriate query filters for milestones, documents, contacts, and action items. This is the security-critical layer -- it must have 100% unit test coverage for all 6 roles with edge cases (empty data, null fields, mixed roles).

```python
# Pseudocode for the scoping interface
def get_visible_milestone_types(role: str) -> list[str] | None:
    """Returns milestone types visible to this role, or None for 'all visible'."""

def get_visible_document_filter(role: str, file_visibility: list[str] | None) -> bool:
    """Returns True if this file should be visible to the given role."""

def get_visible_contacts(role: str, transaction_parties: list[Party]) -> list[ContactInfo]:
    """Returns only the contacts this role is allowed to see."""
```

### 3.3 Party Action Items

Action items are the primary interactive element of the portal. They tell each party exactly what is needed from them and give them a way to respond. Phase 1 introduced the `action_items` table for agent-facing action items. Phase 3 extends this same table to support portal-facing action items assigned to specific parties.

**Action Item Properties (extending the Phase 1 `action_items` table):**

The Phase 1 `action_items` table already has: `id`, `transaction_id`, `milestone_id`, `type`, `title`, `description`, `priority`, `status`, `due_date`, `snoozed_until`, `completed_at`, `agent_id`, `created_at`, `updated_at`. Phase 3 adds the following columns:

- `party_id`: UUID FK to parties (nullable). When set, this action item is assigned to a specific party and appears on their portal. When NULL, the action item is agent-only (Phase 1 behavior).
- `action_type`: VARCHAR(50). Replaces the generic Phase 1 `type` for portal items. Values: `upload_request`, `acknowledgment`, `information`, `custom`. Phase 1 types (`milestone_due`, `milestone_overdue`, `missing_party`, etc.) remain valid for agent-only items.
- `file_id`: UUID FK to files (nullable). Linked when a party uploads a file in response to an `upload_request` action item.
- `created_by`: VARCHAR(50). `"system"` for auto-generated items, or the agent's user_id UUID string for manually created items.

**Auto-Generated Portal Action Items:**

| Trigger | Action Item Title | Type | Assigned To | Example |
|---------|-------------------|------|-------------|---------|
| Transaction confirmed, financing_type != "cash" | "Upload your pre-approval letter" | upload_request | Buyer | Auto-generated when transaction is confirmed |
| Earnest money milestone created | "Deliver earnest money by [date]" | acknowledgment | Buyer | Party clicks "Mark as Done" after delivery |
| Inspection milestone approaching (3 days before) | "Please provide property access for inspection on [date]" | acknowledgment | Seller | Auto-generated from milestone trigger |
| Inspection milestone completed by agent | "Upload inspection report" | upload_request | Inspector | Auto-generated when agent marks inspection milestone complete |
| Agent creates custom item | "[Agent-defined task description]" | custom | Any party | Agent manually creates via action item manager |
| Title search milestone approaching | "Upload title search results by [date]" | upload_request | Attorney | Auto-generated from milestone trigger |
| Closing prep milestone approaching | "Prepare closing disclosure" | upload_request | Attorney | Auto-generated from milestone trigger |
| Appraisal milestone approaching (3 days before) | "Coordinate property access for appraisal on [date]" | acknowledgment | Seller | Auto-generated from milestone trigger |
| Financing contingency approaching | "Upload commitment letter" | upload_request | Lender | Auto-generated from milestone trigger |

**Party Interaction Flow:**

1. Party opens their portal and sees a "Your Tasks" section at the top (most prominent section after the progress bar).
2. Each task is rendered as an `ActionItemCard` with clear instructions, due date, and an action button.
3. For `upload_request` items: a file upload button appears inline. Party selects a file, sees the filename and size displayed, clicks "Upload". The file is validated (type, size, magic bytes), uploaded to the S3 quarantine prefix, and linked to the action item. The action item status changes to `completed` and `completed_at` is set. The party sees a confirmation message: "Your file has been uploaded and is being reviewed by your agent."
4. For `acknowledgment` items: a "Mark as Done" button appears. Party clicks it, and the item transitions to `completed`. Party sees a confirmation: "Done! Your agent has been notified."
5. For `information` items: read-only display, no action button. Used for status updates like "Your agent has submitted the repair request."
6. On completion of any action item: (a) the agent receives an in-app notification via the Phase 2 notification system: "[Party Name] completed: [Action Item Title]", (b) if the action item has an associated `upload_request` and a file was uploaded, the agent also sees the file in their file review queue, (c) portal activity is logged in `portal_access_logs`.

**File Upload Completion Flow (detailed):**

1. Party clicks "Choose File" on an `upload_request` action item.
2. Browser's native file picker opens (on mobile: includes camera option).
3. Party selects a file. Frontend validates: (a) file extension is one of `.pdf`, `.jpg`, `.jpeg`, `.png`, `.docx`; (b) file size <= 25 MB; (c) displays filename and size for confirmation.
4. Party clicks "Upload". Frontend shows a progress bar.
5. Backend receives the multipart upload at `POST /api/portal/:token/upload`. Backend validates: (a) file extension whitelist; (b) file size <= 25 MB; (c) MIME type via `python-magic` magic byte inspection; (d) MIME type matches expected type for the file extension (prevents `.pdf` files that are actually executables).
6. File is uploaded to S3 at key `quarantine/{transaction_id}/{uuid}_{original_filename}`.
7. A `files` record is created: `quarantine = TRUE`, `review_status = "pending_review"`, `uploaded_by_party_id = party_id`, `visibility = NULL` (agent-only until reviewed).
8. The action item's `file_id` is set to the new file's ID. Status changes to `completed`, `completed_at` set to `now()`.
9. Notification sent to agent: "[Party Name] uploaded [filename] for [Action Item Title]."
10. Agent reviews the file in their `FileReviewQueue` component. Options: (a) Approve -- file moves from quarantine prefix to permanent prefix, `quarantine = FALSE`, `review_status = "approved"`, agent sets `visibility` array. (b) Reject -- file remains in quarantine, `review_status = "rejected"`, agent can add a rejection reason and the system creates a new `upload_request` action item for the party to re-upload.

### 3.4 Portal Design

**Design Principles:**

- **Mobile-first:** Design for 375px width first, then enhance for tablet (768px) and desktop (1024px+). CSS uses `min-width` media queries to add complexity, not `max-width` to remove it.
- **Zero learning curve:** A person who has never used the platform should understand the entire page within 5 seconds. Sections are clearly labeled, actions are described in plain English, and progress is immediately visible.
- **Branded:** Show the agent's name and brokerage name at the top. Optionally display a brokerage logo. Primary accent color is configurable per transaction (stored in `transactions.portal_branding_color`, defaults to `#1e40af`).
- **Calming:** Real estate transactions are stressful. Use calm colors (slate and blue palette), clear typography, generous whitespace, and reassuring language. Avoid alarm-colored elements except for truly overdue items.
- **Accessible:** WCAG AA compliance minimum, targeting AAA where feasible. Color is never the sole indicator of status. All interactive elements have visible focus states, text labels, and appropriate ARIA attributes.

**Page Layout (Mobile - 375px):**

```
+------------------------------------------+
|  [Agent Name] | [Brokerage Name]         |
|  [Optional Brokerage Logo]               |
+------------------------------------------+
|                                          |
|  Property: 123 Main St, Birmingham, AL   |
|  Closing Date: March 14, 2026           |
|                                          |
|  ======== Progress: 65% ========         |
|  [============================------]    |
|  Contract > Inspection > Appraisal >     |
|  Financing > Closing                     |
|                                          |
+------------------------------------------+
|                                          |
|  YOUR TASKS (2 remaining)                |
|  +------------------------------------+  |
|  | Upload Pre-Approval Letter         |  |
|  | Due: Feb 20, 2026                  |  |
|  | Your lender needs this to proceed  |  |
|  | [Choose File] [Upload]             |  |
|  +------------------------------------+  |
|  +------------------------------------+  |
|  | Schedule Final Walkthrough         |  |
|  | Due: Mar 5, 2026                   |  |
|  | Contact your agent to schedule     |  |
|  | [Mark as Done]                     |  |
|  +------------------------------------+  |
|                                          |
+------------------------------------------+
|                                          |
|  TIMELINE                                |
|  * Earnest Money      Feb 15  [Done]     |
|  * Home Inspection    Feb 22  [Done]     |
|  * Appraisal          Mar 1   [Pending]  |
|  * Financing          Mar 8   [Pending]  |
|  * Final Walkthrough  Mar 12  [Pending]  |
|  * Closing            Mar 14  [Pending]  |
|                                          |
+------------------------------------------+
|                                          |
|  DOCUMENTS                               |
|  [PDF] Purchase Agreement    [View]      |
|  [PDF] Inspection Report     [View]      |
|                                          |
+------------------------------------------+
|                                          |
|  NEED HELP?                              |
|  [Contact Your Agent]                    |
|  Tyler Pettis                            |
|  (205) 555-1234  |  tyler@armistead.re   |
|  Armistead Real Estate                   |
|                                          |
+------------------------------------------+
|  This link is unique to you.             |
|  Do not share it with others.            |
+------------------------------------------+
```

**Design Specifications:**

| Element | Specification |
|---------|--------------|
| Typography | System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`). Body: 16px/1.5 line-height. Headings: 20px/1.3 bold. Section labels: 14px/1.2 uppercase tracking-wide semibold in slate-500. |
| Colors | Primary: agent's brokerage color (configurable via `portal_branding_color`, default `#1e40af` blue). Success: `#16a34a` green. Warning: `#ca8a04` amber. Danger: `#dc2626` red. Background: `#f8fafc` slate-50. Card background: `#ffffff` white. Border: `#e2e8f0` slate-200. Text primary: `#0f172a` slate-900. Text secondary: `#64748b` slate-500. |
| Progress bar | Full-width, 8px height, rounded-full corners. Filled portion in primary color with subtle gradient. Unfilled in `#e2e8f0`. Percentage label centered above the bar in 14px semibold. On desktop (>768px): milestone labels displayed below the bar at proportional positions. |
| Action item cards | White background, 1px `#e2e8f0` border, 8px border-radius, 16px padding. Overdue items get a 4px left border accent in `#dc2626` red and a small "Overdue" badge in red. Completed items show a green checkmark icon with "Done" text and `completed_at` date. |
| Milestone timeline | Vertical list with status dots aligned left. Dots: 12px diameter. Green (`#16a34a`) = complete, blue (`#3b82f6`) = in progress, gray (`#9ca3af`) = pending, red (`#dc2626`) = overdue. Connecting line between dots in `#e2e8f0`. Each row: dot + title + date + status text. |
| Document row | File type icon (PDF red, image blue, DOCX blue), filename (truncated at 30 chars with ellipsis), file size, [View] button in primary color. Upload rows have [Choose File] + [Upload] buttons. |
| Contact button | Full-width, primary color background, white text, 48px height, centered text, 8px border-radius. On mobile: "Call" button uses `tel:` link, "Email" button uses `mailto:` link. Both buttons displayed side by side. |
| Footer notice | 12px text, `#94a3b8` slate-400 color, centered, with privacy note. |
| Tap targets | Minimum 44x44px for all interactive elements per WCAG 2.5.5. |
| Max content width | 640px centered on desktop. Full-width with 16px horizontal padding on mobile. |
| Loading skeleton | Matches the page layout structure to prevent layout shift (CLS). Animated pulse placeholders for each section. |

---

## 4. Data Model

### 4.1 New Tables

#### `portal_tokens`

Stores the token records that grant portal access to parties.

```sql
CREATE TABLE portal_tokens (
    -- BaseModel columns inherited
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Portal-specific columns
    token UUID NOT NULL DEFAULT gen_random_uuid(),
        -- The public-facing portal token used in URLs. Separate from the PK.
    party_id UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    revoked_at TIMESTAMPTZ,
        -- NULL = active. Set to NOW() when revoked or superseded.
    expires_at TIMESTAMPTZ,
        -- NULL = no expiry (transaction is active). Set to NOW()+90 days on transaction close.
    last_accessed_at TIMESTAMPTZ
        -- Updated on each portal access. Used for agent-side "last seen" display.
);

-- Primary lookup: portal access by token value
CREATE UNIQUE INDEX ix_portal_tokens_token ON portal_tokens(token);

-- Find token(s) by party
CREATE INDEX ix_portal_tokens_party_id ON portal_tokens(party_id);

-- Find all tokens for a transaction (agent management view)
CREATE INDEX ix_portal_tokens_transaction_id ON portal_tokens(transaction_id);

-- Enforce one active token per party (application layer primary, DB safety net)
CREATE UNIQUE INDEX ix_portal_tokens_active_party
    ON portal_tokens(party_id) WHERE revoked_at IS NULL;
```

#### `portal_access_logs`

Audit trail for all portal access. This table will grow large and requires a retention policy.

```sql
CREATE TABLE portal_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id UUID NOT NULL REFERENCES portal_tokens(id) ON DELETE CASCADE,
    ip_address VARCHAR(45) NOT NULL,
        -- Supports IPv6 (max 45 chars for full IPv6 notation)
    user_agent TEXT,
    endpoint VARCHAR(255) NOT NULL,
        -- Which portal API endpoint was accessed
    action VARCHAR(50),
        -- Optional: 'view', 'upload', 'complete_task', 'download_document'
    metadata JSONB,
        -- Optional: additional context (e.g., action_item_id, file_id)
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Access history per token (agent viewing portal activity)
CREATE INDEX ix_portal_access_logs_token_id ON portal_access_logs(token_id);

-- Rate limiting and abuse detection by IP
CREATE INDEX ix_portal_access_logs_ip ON portal_access_logs(ip_address);

-- Time-based queries and retention cleanup
CREATE INDEX ix_portal_access_logs_accessed_at ON portal_access_logs(accessed_at);
```

**Retention policy:** A scheduled Celery task (daily) deletes rows from `portal_access_logs` where `accessed_at < NOW() - INTERVAL '180 days'`. This prevents unbounded table growth while retaining 6 months of audit history.

### 4.2 Modifications to Existing Tables

#### `action_items` table -- add columns (extends Phase 1 table)

```sql
ALTER TABLE action_items
    ADD COLUMN party_id UUID REFERENCES parties(id) ON DELETE SET NULL,
        -- When set, this action item appears on the party's portal.
        -- When NULL, the item is agent-only (Phase 1 behavior preserved).
    ADD COLUMN action_type VARCHAR(50),
        -- For portal items: 'upload_request', 'acknowledgment', 'information', 'custom'.
        -- NULL for Phase 1 agent-only items (they use the existing 'type' column).
    ADD COLUMN file_id UUID REFERENCES files(id) ON DELETE SET NULL,
        -- Linked when a party uploads a file for an 'upload_request' item.
    ADD COLUMN created_by VARCHAR(50) DEFAULT 'system';
        -- 'system' for auto-generated, or agent user_id for manual creation.

-- Portal query: "action items for this party"
CREATE INDEX ix_action_items_party_id ON action_items(party_id)
    WHERE party_id IS NOT NULL;

-- Portal query: "pending action items for this party"
CREATE INDEX ix_action_items_party_status ON action_items(party_id, status)
    WHERE party_id IS NOT NULL;
```

#### `files` table -- add columns

```sql
ALTER TABLE files
    ADD COLUMN visibility JSONB,
        -- Array of role strings that can see this file via portal.
        -- e.g., '["buyer", "lender", "attorney"]'
        -- NULL = visible to agent only (no portal visibility).
    ADD COLUMN uploaded_by_party_id UUID REFERENCES parties(id) ON DELETE SET NULL,
        -- Non-NULL when a party uploaded this file via the portal.
        -- NULL = agent uploaded via the authenticated interface.
    ADD COLUMN review_status VARCHAR(50),
        -- 'pending_review', 'approved', 'rejected'.
        -- Only set for party-uploaded files. NULL for agent uploads.
    ADD COLUMN reviewed_at TIMESTAMPTZ,
        -- When the agent reviewed the party-uploaded file.
    ADD COLUMN review_notes TEXT,
        -- Agent's notes on review (especially rejection reason).
    ADD COLUMN quarantine BOOLEAN NOT NULL DEFAULT FALSE;
        -- TRUE = file is in the S3 quarantine prefix.
        -- Party uploads start as TRUE. Set to FALSE when agent approves.

-- Find files pending review (agent's review queue)
CREATE INDEX ix_files_review_status ON files(review_status)
    WHERE review_status = 'pending_review';
```

#### `parties` table -- add column

```sql
ALTER TABLE parties
    ADD COLUMN portal_enabled BOOLEAN NOT NULL DEFAULT TRUE;
        -- Agent can disable portal access for a specific party
        -- without revoking their token. When FALSE, token generation
        -- is blocked and existing tokens are treated as inactive.
```

#### `transactions` table -- add columns

```sql
ALTER TABLE transactions
    ADD COLUMN portal_branding_color VARCHAR(7),
        -- Hex color for portal branding, e.g., '#1e40af'.
        -- Falls back to system default if NULL.
    ADD COLUMN portal_branding_logo_url VARCHAR(500);
        -- S3 URL for brokerage logo displayed on portal header.
        -- NULL = no logo displayed.
```

---

## 5. API Endpoints

### 5.1 Authenticated Endpoints (Agent-Side)

These endpoints require the agent's authentication token (Clerk JWT) and are prefixed with `/api`. They allow the agent to manage portal tokens, action items, document visibility, and file reviews.

#### Portal Token Management

**`POST /api/transactions/{txn_id}/portal/tokens`**

Generate a portal token for a single party.

```
Request Body:
{
  "party_id": "uuid"
}

Response 201:
{
  "id": "uuid",
  "token": "uuid",
  "token_url": "https://app.armistead.re/portal/{token}",
  "party_id": "uuid",
  "party_name": "John Smith",
  "party_role": "buyer",
  "created_at": "2026-03-01T10:00:00Z"
}

Errors:
  400 - Party does not belong to this transaction
  400 - Party already has an active portal token (use regenerate instead)
  400 - Party has portal_enabled = false
  404 - Transaction or party not found
```

**`POST /api/transactions/{txn_id}/portal/tokens/bulk`**

Generate portal tokens for all eligible parties on the transaction. Eligible = `portal_enabled = TRUE` and no active (non-revoked, non-expired) token.

```
Request Body: (empty or optional)
{
  "include_roles": ["buyer", "seller", "lender", "attorney"]  // optional filter
}

Response 201:
{
  "tokens": [
    {
      "party_id": "uuid",
      "party_name": "John Smith",
      "role": "buyer",
      "token_url": "https://app.armistead.re/portal/{token}",
      "created_at": "2026-03-01T10:00:00Z"
    },
    ...
  ],
  "skipped": [
    {
      "party_id": "uuid",
      "party_name": "Jane Doe",
      "role": "seller",
      "reason": "already_has_active_token"
    }
  ]
}
```

**`GET /api/transactions/{txn_id}/portal/tokens`**

List all portal tokens (active and revoked) for a transaction.

```
Query Params:
  - active_only: boolean (default: true, only return non-revoked non-expired tokens)

Response 200:
{
  "tokens": [
    {
      "id": "uuid",
      "party_id": "uuid",
      "party_name": "John Smith",
      "party_role": "buyer",
      "token_url": "https://app.armistead.re/portal/{token}",
      "created_at": "2026-03-01T10:00:00Z",
      "last_accessed_at": "2026-03-10T14:30:00Z",
      "revoked_at": null,
      "expires_at": null,
      "is_active": true
    }
  ]
}
```

**`POST /api/transactions/{txn_id}/portal/tokens/{token_id}/regenerate`**

Revoke the existing token and create a new one for the same party.

```
Request Body: (empty)

Response 201:
{
  "old_token_id": "uuid",
  "old_token_revoked_at": "2026-03-10T15:00:00Z",
  "new_token": {
    "id": "uuid",
    "token_url": "https://app.armistead.re/portal/{new_token}",
    "party_id": "uuid",
    "created_at": "2026-03-10T15:00:00Z"
  }
}
```

**`DELETE /api/transactions/{txn_id}/portal/tokens/{token_id}`**

Revoke a portal token without generating a replacement. Party loses access.

```
Response 204: No Content
```

#### Portal Access Logs

**`GET /api/transactions/{txn_id}/portal/access-logs`**

View portal access history for a transaction.

```
Query Params:
  - party_id: UUID (optional, filter to specific party)
  - limit: integer (default: 50, max: 200)
  - offset: integer (default: 0)

Response 200:
{
  "logs": [
    {
      "id": "uuid",
      "party_name": "John Smith",
      "party_role": "buyer",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (iPhone; ...) Safari/604.1",
      "endpoint": "/api/portal/{token}",
      "action": "view",
      "accessed_at": "2026-03-10T14:30:00Z"
    }
  ],
  "total": 45,
  "limit": 50,
  "offset": 0
}
```

#### Portal Action Items (Agent Management)

**`POST /api/transactions/{txn_id}/action-items`**

Create a custom action item. Extends the Phase 1 endpoint to support `party_id` for portal items.

```
Request Body:
{
  "party_id": "uuid",         // required for portal items, NULL for agent-only
  "title": "Upload your homeowner's insurance policy",
  "description": "Your lender requires proof of insurance before closing.",
  "action_type": "upload_request",  // upload_request | acknowledgment | information | custom
  "due_date": "2026-03-15T00:00:00Z",
  "priority": "medium"
}

Response 201:
{
  "id": "uuid",
  "transaction_id": "uuid",
  "party_id": "uuid",
  "title": "Upload your homeowner's insurance policy",
  "description": "Your lender requires proof of insurance before closing.",
  "action_type": "upload_request",
  "status": "pending",
  "due_date": "2026-03-15T00:00:00Z",
  "priority": "medium",
  "created_by": "agent-user-uuid",
  "created_at": "2026-03-10T15:00:00Z"
}
```

**`GET /api/transactions/{txn_id}/action-items`**

List all action items for a transaction. Extends Phase 1 with party filter.

```
Query Params:
  - party_id: UUID (optional, filter to specific party's items)
  - status: "pending" | "completed" | "snoozed" | "dismissed" (optional)
  - portal_only: boolean (optional, only items with party_id set)

Response 200:
{
  "items": [ ActionItem objects... ],
  "total": 12
}
```

**`PATCH /api/transactions/{txn_id}/action-items/{item_id}`**

Update an action item (title, description, due_date, status, party_id, action_type).

```
Request Body: (partial update, any subset of fields)
{
  "title": "Updated title",
  "due_date": "2026-03-20T00:00:00Z",
  "status": "completed"
}

Response 200:
{ ...updated ActionItem object... }
```

**`DELETE /api/transactions/{txn_id}/action-items/{item_id}`**

Delete an action item.

```
Response 204: No Content
```

#### File Review (Agent reviews party-uploaded files)

**`PATCH /api/transactions/{txn_id}/files/{file_id}/review`**

Approve or reject a party-uploaded file.

```
Request Body:
{
  "review_status": "approved",     // "approved" | "rejected"
  "visibility": ["buyer", "lender", "attorney"],  // required if approving
  "review_notes": "Looks good"     // optional, especially useful for rejections
}

Response 200:
{
  "id": "uuid",
  "name": "pre_approval_letter.pdf",
  "review_status": "approved",
  "reviewed_at": "2026-03-10T16:00:00Z",
  "quarantine": false,             // false after approval
  "visibility": ["buyer", "lender", "attorney"]
}

Notes:
  - On approval: file is moved from quarantine S3 prefix to permanent prefix.
    quarantine flag set to FALSE. visibility set from request body.
  - On rejection: file remains in quarantine. review_status = "rejected".
    A new upload_request action item can optionally be created for the party.
```

**`PATCH /api/transactions/{txn_id}/files/{file_id}/visibility`**

Update document visibility (which roles can see it via portal).

```
Request Body:
{
  "visibility": ["buyer", "seller", "lender", "attorney"]
}

Response 200:
{
  "id": "uuid",
  "name": "purchase_agreement.pdf",
  "visibility": ["buyer", "seller", "lender", "attorney"]
}

Notes:
  - Setting visibility to NULL or [] makes the file agent-only.
  - Cache busted for all active portal tokens on this transaction.
```

### 5.2 Public Endpoints (Portal-Side)

These endpoints require NO authentication. The portal token in the URL path acts as the sole authorization mechanism. All endpoints are prefixed with `/api/portal`. All responses omit data outside the party's role scope, enforced at the query layer.

**Common Token Validation (applied to all portal endpoints):**

1. Look up `portal_tokens` by `token` value.
2. If not found: return `404 { "error": "Portal not found" }`.
3. If `revoked_at IS NOT NULL`: return `404 { "error": "Portal not found" }`.
4. If `expires_at IS NOT NULL AND expires_at < NOW()`: return `404 { "error": "Portal not found" }`.
5. If the associated party has `portal_enabled = FALSE`: return `404 { "error": "Portal not found" }`.
6. Update `last_accessed_at` (async, fire-and-forget).
7. Log access in `portal_access_logs` (async).
8. Proceed with role-scoped data retrieval.

**`GET /api/portal/{token}`**

Main portal data payload. Returns transaction overview, party info, and branding.

```
Response 200:
{
  "party": {
    "name": "John Smith",
    "role": "buyer"
  },
  "transaction": {
    "property_address": "123 Main St, Birmingham, AL 35242",
    "status": "active",
    "closing_date": "2026-03-14",
    "progress_percent": 65
  },
  "branding": {
    "agent_name": "Tyler Pettis",
    "brokerage_name": "Armistead Real Estate",
    "primary_color": "#1e40af",
    "logo_url": null
  },
  "agent": {
    "name": "Tyler Pettis",
    "phone": "(205) 555-1234",
    "email": "tyler@armistead.re",
    "brokerage": "Armistead Real Estate"
  },
  "is_archive_mode": false
      // true when transaction is closed but within 90-day window
}

Cache: 60 seconds (Redis key: portal:{token_id}:overview)
Cache bust: transaction update, party update, branding change
```

**`GET /api/portal/{token}/milestones`**

Role-scoped milestones for the portal timeline.

```
Response 200:
{
  "milestones": [
    {
      "id": "uuid",
      "title": "Earnest Money Delivery",
      "due_date": "2026-02-15",
      "status": "completed",
      "completed_at": "2026-02-14T10:00:00Z",
      "days_remaining": null,
      "is_overdue": false
    },
    {
      "id": "uuid",
      "title": "Home Inspection",
      "due_date": "2026-02-22",
      "status": "completed",
      "completed_at": "2026-02-21T14:00:00Z",
      "days_remaining": null,
      "is_overdue": false
    },
    {
      "id": "uuid",
      "title": "Appraisal",
      "due_date": "2026-03-01",
      "status": "pending",
      "completed_at": null,
      "days_remaining": 5,
      "is_overdue": false
    }
  ]
}

Cache: 30 seconds (Redis key: portal:{token_id}:milestones)
Cache bust: milestone status change, new milestone created, milestone date changed
```

**`GET /api/portal/{token}/action-items`**

Action items assigned to this party.

```
Response 200:
{
  "items": [
    {
      "id": "uuid",
      "title": "Upload Pre-Approval Letter",
      "description": "Please upload a copy of your pre-approval letter from your lender.",
      "action_type": "upload_request",
      "status": "pending",
      "due_date": "2026-02-20",
      "is_overdue": true,
      "days_overdue": 4
    },
    {
      "id": "uuid",
      "title": "Schedule Final Walkthrough",
      "description": "Contact your agent to schedule the final walkthrough before closing.",
      "action_type": "acknowledgment",
      "status": "pending",
      "due_date": "2026-03-05",
      "is_overdue": false,
      "days_remaining": 9
    }
  ],
  "completed": [
    {
      "id": "uuid",
      "title": "Deliver Earnest Money",
      "action_type": "acknowledgment",
      "status": "completed",
      "completed_at": "2026-02-14T10:00:00Z"
    }
  ]
}

Cache: 15 seconds (Redis key: portal:{token_id}:actions)
Cache bust: action item create, update, complete
```

**`PATCH /api/portal/{token}/action-items/{item_id}/complete`**

Mark an action item as completed by the party.

```
Request Body: (empty)

Response 200:
{
  "id": "uuid",
  "status": "completed",
  "completed_at": "2026-03-10T14:30:00Z"
}

Errors:
  400 - Action item is not assigned to this party
  400 - Action item is already completed
  400 - Transaction is in archive mode (read-only after close)
  404 - Action item not found

Side effects:
  - Agent notification created: "[Party Name] completed: [Title]"
  - Portal activity logged
  - Cache busted for action items
```

**`GET /api/portal/{token}/documents`**

Role-scoped documents available to this party.

```
Response 200:
{
  "documents": [
    {
      "id": "uuid",
      "name": "Purchase_Agreement.pdf",
      "content_type": "application/pdf",
      "size_bytes": 1245678,
      "size_display": "1.2 MB",
      "created_at": "2026-02-10T09:00:00Z"
    }
  ]
}

Cache: 120 seconds (Redis key: portal:{token_id}:documents)
Cache bust: file upload, visibility change, review status change
```

**`GET /api/portal/{token}/documents/{doc_id}/view`**

Generate a signed S3 URL for viewing a document.

```
Response 302: Redirect to signed S3 URL

Headers:
  Location: https://s3.amazonaws.com/bucket/path?X-Amz-Signature=...&X-Amz-Expires=900

Notes:
  - Signed URL expires in 15 minutes (900 seconds).
  - The document must be in the party's role visibility array.
  - Quarantined files (quarantine = TRUE) are never accessible via this endpoint.
```

**`POST /api/portal/{token}/upload`**

Upload a file from the portal.

```
Request: multipart/form-data
  - file: binary file data (required)
  - action_item_id: UUID (optional, links upload to specific action item)

Response 201:
{
  "file_id": "uuid",
  "name": "pre_approval_letter.pdf",
  "content_type": "application/pdf",
  "size_bytes": 524288,
  "review_status": "pending_review",
  "message": "Your file has been uploaded and is being reviewed by your agent."
}

Errors:
  400 - File type not allowed (only PDF, JPG, PNG, DOCX)
  400 - File MIME type does not match extension
  413 - File size exceeds 25 MB limit
  400 - Transaction is in archive mode (uploads disabled after close)
  429 - Rate limit exceeded

Validation steps (server-side):
  1. Check file extension against whitelist
  2. Check Content-Length <= 25 MB
  3. Read file, inspect magic bytes via python-magic
  4. Verify magic bytes match expected MIME for the file extension
  5. Upload to S3 quarantine prefix
  6. Create files record with quarantine=TRUE, review_status='pending_review'
  7. If action_item_id provided, link file and complete the action item
  8. Create agent notification
```

**`GET /api/portal/{token}/contacts`**

Role-scoped contact information.

```
Response 200:
{
  "contacts": [
    {
      "name": "Tyler Pettis",
      "role": "buyer_agent",
      "role_display": "Your Agent",
      "phone": "(205) 555-1234",
      "email": "tyler@armistead.re",
      "company": "Armistead Real Estate"
    }
  ]
}

Cache: 300 seconds (Redis key: portal:{token_id}:contacts)
Cache bust: party added, removed, or updated on the transaction
```

### 5.3 Portal Caching Strategy

All portal responses are cached in Redis to minimize database load and improve response times. Cache keys are namespaced with `portal:` to isolate them from other Redis usage.

| Endpoint | Cache TTL | Cache Key Pattern | Bust Triggers |
|----------|-----------|-------------------|---------------|
| GET `/api/portal/{token}` | 60 seconds | `portal:{token_id}:overview` | Transaction status/field update, party name/role update, branding change |
| GET `/api/portal/{token}/milestones` | 30 seconds | `portal:{token_id}:milestones` | Milestone create, status change, date change, deletion |
| GET `/api/portal/{token}/action-items` | 15 seconds | `portal:{token_id}:actions` | Action item create, update, complete, delete |
| GET `/api/portal/{token}/documents` | 120 seconds | `portal:{token_id}:documents` | File upload (agent or party), visibility change, review status change, file deletion |
| GET `/api/portal/{token}/contacts` | 300 seconds | `portal:{token_id}:contacts` | Party added, removed, updated on the transaction |

**Cache Busting Implementation:**

When an agent-side endpoint modifies data that affects portal views, the endpoint handler calls `bust_portal_cache(transaction_id, cache_types)`. This function:
1. Queries all active portal tokens for the transaction.
2. For each token, deletes the specified Redis cache keys (e.g., `portal:{token_id}:milestones`).
3. This is a synchronous operation to ensure consistency -- the next portal request gets fresh data.

**Memory Estimation:**

Each portal token has up to 5 cache keys. Each key stores approximately 200-500 bytes of JSON. With 300 active portal tokens: ~750 KB total Redis memory. This is negligible and well within the existing Redis instance capacity.

---

## 6. Frontend Components

### 6.1 Agent Interface Components (Inside Authenticated App)

These components are added to the existing agent-side React application within the transaction detail view. They give the agent full control over portal token management, action items, file review, and document visibility.

| Component | Location | Description | Key Props / State |
|-----------|----------|-------------|-------------------|
| `PortalLinksPanel` | Transaction Detail page, new "Portal" tab | Shows all parties with their portal link status (active / not generated / revoked). Bulk generate button at the top. Per-party rows with actions. | `transactionId: string`, fetches `/api/transactions/{id}/portal/tokens` |
| `PortalLinkRow` | Child of `PortalLinksPanel`, one per party | Party name, role badge, link status badge (green "Active" / gray "Not Generated" / red "Revoked"), last accessed timestamp ("3 hours ago" / "Never"), and action buttons: [Copy Link] (copies to clipboard with toast), [Regenerate] (revoke + new), [Revoke] (removes access). | `party: Party`, `token: PortalToken \| null` |
| `ActionItemManager` | Transaction Detail page, within "Portal" tab or separate "Tasks" tab | Table of all action items across all parties. Create button opens `ActionItemForm`. Filterable by party, status, and action_type. Shows completion status, due date, overdue badges, and linked uploaded files. | `transactionId: string`, fetches `/api/transactions/{id}/action-items?portal_only=true` |
| `ActionItemForm` | Modal, triggered from `ActionItemManager` | Form to create or edit a portal action item. Fields: select party (dropdown), title (text), description (textarea), action_type (select: upload_request, acknowledgment, information, custom), due date (date picker). | `transactionId: string`, `parties: Party[]`, `existingItem?: ActionItem` |
| `FileReviewQueue` | Transaction Detail page, within "Portal" tab | List of party-uploaded files with `review_status = "pending_review"`. Each row: file name, uploaded by (party name + role), upload date, file size, [Preview] button (opens signed URL in new tab), [Approve] button (opens visibility selector), [Reject] button (opens rejection reason dialog). | `transactionId: string`, fetches `/api/transactions/{id}/files?review_status=pending_review` |
| `DocumentVisibilityEditor` | Inline in file list or modal triggered from file row | Checkbox grid: rows = roles (buyer, seller, lender, attorney, inspector, other_agent), all checkable. Shows current visibility state. Save button updates via PATCH. | `file: File`, `onUpdate: (visibility: string[]) => void` |
| `PortalAccessLog` | Transaction Detail page, collapsible section within "Portal" tab | Paginated table showing recent portal access: party name, role, IP address, user agent (truncated), action description, timestamp. Load more button for pagination. | `transactionId: string`, fetches `/api/transactions/{id}/portal/access-logs` |
| `PortalPreviewButton` | Inside `PortalLinkRow` per party | Opens the party's portal URL in a new browser tab so the agent can preview what the party sees. Shows a tooltip: "Preview what [Party Name] sees". | `tokenUrl: string` |
| `SendPortalLinkButton` | Inside `PortalLinkRow` per party | Triggers an email send (via Phase 2 email system) containing the portal link to the party's email. Uses the Phase 2 `EmailDeliveryService` with a portal-link-specific template. | `party: Party`, `tokenUrl: string` |

### 6.2 Portal Interface Components (Public, No Auth)

The portal is a **separate route tree** at `/portal/:token` with its own layout. It does NOT share the authenticated app's sidebar, header, or navigation. It has its own minimal, branded layout. The portal frontend is a separate code-split chunk to minimize bundle size.

| Component | Description | Key Behavior |
|-----------|-------------|-------------|
| `PortalLayout` | Root layout for all portal pages. No sidebar. Branded header (agent name, brokerage, optional logo). Footer with privacy notice. Max-width 640px centered container. Full-width on mobile with 16px padding. | Wraps all portal content. Fetches branding data from the main portal endpoint. |
| `PortalHeader` | Agent/brokerage branding bar at top. Shows agent name, brokerage name, optional brokerage logo. Background in primary branding color or white with primary color accent. | Uses `branding.primary_color` for accent. Logo loaded from `branding.logo_url` if present. |
| `PortalFooter` | Privacy notice: "This link is unique to you. Do not share it with others." Optional brokerage disclaimer text. Powered by Armistead RE link. | Fixed at page bottom (not sticky -- scrolls with content). |
| `PortalErrorPage` | Shown for invalid, revoked, and expired tokens. Generic message: "This portal link is not active. Please contact your agent for an updated link." Shows agent contact info if available (from URL query param fallback), otherwise a generic message. | No indication of whether the token was invalid vs. revoked vs. expired. Same page for all failure modes. |
| `PortalLoadingPage` | Full-page loading skeleton shown while portal data loads. Matches the portal layout structure (header skeleton, progress bar skeleton, cards skeleton) to prevent layout shift. | Animated pulse effect on skeleton elements. Shows for 0-2 seconds on initial load. |
| `ProgressBar` | Horizontal progress bar showing transaction completion percentage. On desktop (>768px): milestone labels below the bar at proportional positions, connected by tick marks. On mobile: compact bar with percentage label only. | Uses `transaction.progress_percent`. Colors: filled in primary color, unfilled in slate-200. |
| `ActionItemsList` | "Your Tasks" section. Prominent placement at top of portal (after progress bar). Shows pending items first, then recently completed items (last 7 days). Section header shows count: "Your Tasks (2 remaining)". | Fetches from `/api/portal/{token}/action-items`. Empty state: "You're all caught up! No tasks right now." |
| `ActionItemCard` | Individual action item card. Shows title (bold), description (expandable on tap/click), due date, status. Overdue items: red left border, "Overdue by X days" badge. For `upload_request`: inline `FileUploadInline` component. For `acknowledgment`: "Mark as Done" button. For `information`: read-only with info icon. Completed items: green checkmark, completion date, grayed-out styling. | Handles state transitions optimistically (update UI immediately, revert on error). |
| `FileUploadInline` | Inline file upload within `ActionItemCard`. File picker (accepts `.pdf,.jpg,.jpeg,.png,.docx`). Shows selected file name and size before upload. Upload button with animated progress bar. Success state: "Uploaded! Pending review." Error state: clear message ("File too large" or "File type not allowed"). | Max file size 25 MB. MIME validation on frontend as first pass (backend validates again). |
| `MilestoneTimeline` | Vertical timeline of role-scoped milestones. Each milestone is a `MilestoneItem`. Dots connected by a vertical line. Compact layout on mobile (less padding). | Fetches from `/api/portal/{token}/milestones`. |
| `MilestoneItem` | Single milestone in the timeline. Status dot (green = complete, blue = in progress, gray = pending, red = overdue). Title, date, status text ("Completed Feb 14" / "Due in 5 days" / "3 days overdue"). | Uses `RelativeDate` for human-friendly date display. |
| `DocumentList` | "Documents" section. Lists available documents with file type icon, name, date, size, and "View" button. "View" opens the signed S3 URL in a new tab. | Fetches from `/api/portal/{token}/documents`. Empty state: "No documents available yet." |
| `DocumentRow` | Single document row. File type icon (PDF icon in red, image icon in blue, DOCX icon in blue, generic icon in gray). File name (truncated at 35 chars). File size. "View" button in primary color. | Clicking "View" calls `/api/portal/{token}/documents/{id}/view` and opens the redirect in a new tab. |
| `ContactCard` | "Need Help? Contact Your Agent" section at bottom. Shows agent name, phone (clickable `tel:` link), email (clickable `mailto:` link), company name. On mobile: full-width "Call" and "Email" buttons side by side. | Uses data from `/api/portal/{token}/contacts`. Multiple contacts shown if the role warrants it (e.g., attorney sees all contacts). |
| `PortalPage` | Main portal page component. Orchestrator that fetches data from all portal endpoints and assembles the sections: PortalHeader > ProgressBar > ActionItemsList > MilestoneTimeline > DocumentList > ContactCard > PortalFooter. Handles loading (shows `PortalLoadingPage`) and error states (shows `PortalErrorPage`). | Single-page architecture. All data fetched in parallel on mount. React Query for caching and refetching. |

### 6.3 Portal Route Structure

```
/portal/:token              -> PortalPage (main portal view, all sections)
/portal/error               -> PortalErrorPage (fallback for invalid tokens)
```

The portal uses its own React Router outlet with `PortalLayout` as the wrapper. It does NOT use the authenticated app's `Layout` component, `Sidebar`, or any auth-dependent components. The route is defined at the top level of the React Router configuration, outside the authenticated route group.

```typescript
// In App.tsx route configuration
<Route path="/portal/:token" element={<PortalLayout />}>
  <Route index element={<PortalPage />} />
</Route>
<Route path="/portal/error" element={<PortalErrorPage />} />
```

### 6.4 Shared / Utility Components

| Component | Description | Usage |
|-----------|-------------|-------|
| `StatusDot` | Small colored circle (12px) for timelines and status indicators. Variants: `success` (green #16a34a), `info` (blue #3b82f6), `neutral` (gray #9ca3af), `danger` (red #dc2626), `warning` (amber #eab308). | Used in `MilestoneItem`, `PortalLinkRow`, `ActionItemCard`. |
| `Badge` | Small pill-shaped label. Variants: success, warning, danger, info, neutral. Text inside the pill. | Used for "Overdue", "Active", "Pending Review", "Completed" labels. |
| `FileIcon` | Icon component that renders the appropriate icon based on MIME type. PDF = red document icon, image = blue image icon, DOCX = blue document icon, generic = gray file icon. | Used in `DocumentRow`, `FileReviewQueue`, `FileUploadInline`. |
| `RelativeDate` | Displays dates in human-friendly relative text. "Due in 3 days", "2 days overdue", "Completed Feb 10", "Due today". Falls back to absolute date format for items > 30 days away. | Used throughout the portal timeline and action items. |
| `CopyToClipboard` | Button that copies a string to the clipboard and shows a brief toast confirmation ("Link copied!"). Uses the Clipboard API with a fallback for older browsers. | Used in `PortalLinkRow` for copying portal URLs. |
| `UploadProgress` | Animated progress bar for file uploads. Shows percentage, filename, and estimated time remaining. Transitions to success (green checkmark) or error (red X with message) state on completion. | Used in `FileUploadInline`. |

---

## 7. Definition of Success

Phase 3 is COMPLETE when ALL of the following criteria are met:

| # | Criterion | Verification Method | Target |
|---|-----------|-------------------|--------|
| 1 | Portal link loads within 2 seconds on a 4G mobile connection | Lighthouse performance audit with throttled network simulation (Regular 4G: 9 Mbps down, 1.5 Mbps up, 170ms RTT). Measure Largest Contentful Paint (LCP). | LCP < 2.0 seconds on simulated Regular 4G |
| 2 | Agent can generate portal links for all parties on a transaction in one click | E2E test: create transaction with 6 parties, click "Generate All Portal Links", verify 6 tokens created and returned with correct party associations | All eligible parties receive tokens in < 3 seconds total |
| 3 | Invalid, revoked, and expired tokens all return identical 404 responses with no information leakage | Integration test: hit `/api/portal/{token}` with (a) random UUID, (b) revoked token, (c) expired token. Compare response body, status code, and response headers. | Byte-identical 404 response body for all three cases. No timing difference > 50ms. |
| 4 | Buyer cannot see seller's contact information, financial data, or seller-side milestones via the portal API | Integration test: create full transaction with all party types. Fetch all portal endpoints with buyer token. Assert zero seller PII, zero seller contact data, zero seller-side milestone data in any response. | Zero seller data in buyer's portal responses across all endpoints |
| 5 | Seller cannot see buyer's financial information, lender details, or buyer-side milestones via the portal API | Integration test: same setup as #4. Fetch all portal endpoints with seller token. Assert no buyer financial data, no lender data, no buyer-side milestones. | Zero buyer financial or lender data in seller's portal responses |
| 6 | Inspector can only see inspection-related data (minimal scope) | Integration test: fetch all portal endpoints with inspector token. Verify only inspection milestone visible, only property address visible, only upload capability available. No purchase price, no other milestones, no other party data. | Inspector sees exactly 1 milestone, 0 documents, 1 contact (listing agent), upload area only |
| 7 | Attorney can see all milestones and all party contact info needed for closing coordination | Integration test: fetch portal data with attorney token. Verify full milestone list present. Verify all party contacts present (names, emails, phones). | Complete milestone list and all party contacts in attorney's portal response |
| 8 | Party can upload a file through the portal and agent receives notification within 5 seconds | E2E test: upload a valid PDF via `POST /api/portal/{token}/upload`. Verify file exists in S3 quarantine prefix. Verify `files` record created with `quarantine=TRUE`, `review_status='pending_review'`. Verify agent notification created. | File in quarantine + notification created within 5 seconds of upload |
| 9 | Party-uploaded files are quarantined and invisible to all portal users until agent approves | Integration test: upload file via portal. Attempt to fetch documents list via same party's token and other parties' tokens. Verify the uploaded file does NOT appear in any portal document list. Agent approves file. Re-fetch documents. Verify file now appears for roles in the visibility array. | File invisible via all portal tokens until review_status = "approved" |
| 10 | Portal is fully functional on a 375px-wide mobile viewport with no horizontal scrolling | Manual testing on iOS Safari (iPhone 13) and Android Chrome (Pixel 7). Automated test using Playwright with 375px viewport. | Zero horizontal scrolling. All tap targets >= 44px. All text readable at 16px minimum. No overlapping elements. |
| 11 | Agent can revoke a token and the party immediately loses access with zero delay | Integration test: access portal with valid token (200). Agent revokes token. Immediately access portal with same token. Verify 404 response. | Zero requests succeed after revocation. No stale cached responses. |
| 12 | Portal action item completion triggers agent notification within 1 second | Integration test: mark action item complete via `PATCH /api/portal/{token}/action-items/{id}/complete`. Query notification system. Verify notification record created with correct party name and action item title. | Notification record exists within 1 second of completion |
| 13 | Rate limiting prevents abuse of portal endpoints | Load test: send 50 requests per second to `/api/portal/{token}` from a single IP. Verify that requests beyond 30/minute per token return 429. Verify that requests beyond 100/minute per IP return 429. | 429 responses for requests exceeding rate limits. No server degradation. |
| 14 | Document visibility rules are enforced server-side (not just hidden in frontend) | Integration test: directly call `GET /api/portal/{token}/documents/{doc_id}/view` with a token for a role NOT in the document's visibility array. Verify 404 response (not 403, to avoid confirming the document exists). | 404 for documents outside the party's role visibility |
| 15 | File upload validation rejects malicious files (wrong MIME type, oversized, executable) | Integration test: attempt uploads of (a) a .exe renamed to .pdf, (b) a 30 MB file, (c) a file with .pdf extension but executable magic bytes. Verify all are rejected with appropriate 400/413 errors. | All three malicious upload attempts rejected with clear error messages |
| 16 | Portal progress bar accurately reflects milestone completion percentage | Integration test: create transaction with 10 milestones visible to buyer. Complete 3 milestones. Fetch portal overview with buyer token. Verify `progress_percent = 30`. | Progress percentage matches (completed visible milestones / total visible milestones) * 100 |
| 17 | Portal links can be sent via Phase 2 email system and are clickable in delivered emails | E2E test: generate portal link, trigger email send via Phase 2 Resend integration. Verify portal URL is present in the email body. Load the URL. Verify portal renders correctly. | End-to-end flow from email generation to portal rendering |

---

## 8. Regression Test Plan

### 8.1 Phase 3 New Tests

| Test ID | Type | Description | Expected Result |
|---------|------|-------------|-----------------|
| T3-01 | Unit | Token generation produces valid UUID v4 values | 1000 generated tokens all match UUID v4 format, all unique |
| T3-02 | Integration | Token lookup returns correct party and transaction data | GET `/api/portal/{token}` returns matching party name, role, transaction address, status |
| T3-03 | Integration | Revoked token returns generic 404 | Create token, revoke it, GET portal returns `404 {"error": "Portal not found"}` |
| T3-04 | Integration | Expired token returns generic 404 | Create token, set `expires_at` to 1 hour ago, GET portal returns 404 |
| T3-05 | Integration | Role-based milestone scoping for buyer | Create transaction with 15 milestones of various types. GET milestones with buyer token returns only buyer-visible milestones (earnest money, inspection, appraisal status, financing, walkthrough, closing). |
| T3-06 | Integration | Role-based milestone scoping for lender | Same transaction. GET milestones with lender token returns only loan-related milestones (appraisal, financing contingency, clear to close, closing). |
| T3-07 | Integration | Role-based milestone scoping for inspector | Same transaction. GET milestones with inspector token returns only the inspection milestone. |
| T3-08 | Integration | Role-based milestone scoping for attorney | Same transaction. GET milestones with attorney token returns ALL milestones (attorney sees everything). |
| T3-09 | Integration | Role-based document scoping | Create 5 documents with various visibility arrays. GET documents with each role's token. Verify each role sees only documents where their role is in the visibility array. |
| T3-10 | Integration | Contact info scoping -- buyer sees only agent | GET contacts with buyer token returns only the agent's info. Zero seller, lender, attorney contacts. |
| T3-11 | Integration | Contact info scoping -- attorney sees all | GET contacts with attorney token returns all parties' contact information. |
| T3-12 | Integration | Contact info scoping -- inspector sees only listing agent | GET contacts with inspector token returns only listing agent name and phone. |
| T3-13 | Integration | Action item completion via portal | Create upload_request action item for party. PATCH complete via portal token. Verify status = "completed", completed_at set, agent notification created. |
| T3-14 | Integration | File upload via portal (happy path - PDF) | POST valid 2 MB PDF via portal upload endpoint. Verify file in S3 quarantine prefix, `review_status = "pending_review"`, file NOT visible to any portal user. |
| T3-15 | Integration | File upload via portal (happy path - JPG) | POST valid 500 KB JPG via portal upload endpoint. Same verification as T3-14. |
| T3-16 | Integration | File upload validation -- reject .exe file | POST .exe file via portal upload. Verify 400 response with error message about disallowed file type. |
| T3-17 | Integration | File upload validation -- reject oversized file | POST 30 MB file via portal upload. Verify 413 response with error about file size limit. |
| T3-18 | Integration | File upload validation -- reject MIME mismatch | POST file with .pdf extension but executable magic bytes. Verify 400 response about MIME type mismatch. |
| T3-19 | Integration | Bulk token generation | Create transaction with 6 parties. POST bulk generate. Verify 6 tokens created, each linked to correct party_id, each with unique token value. |
| T3-20 | Integration | Token regeneration revokes old, creates new | Create token for party. POST regenerate. Verify old token has `revoked_at` set and returns 404. New token is active and returns 200. |
| T3-21 | Integration | Party removal cascades to token revocation | Create party with active portal token. Delete the party. Verify the token has `revoked_at` set and returns 404. |
| T3-22 | Integration | Transaction closure sets 90-day token expiry | Create transaction with 3 active tokens. Update transaction status to "closed". Verify all 3 tokens have `expires_at` set to approximately now + 90 days. Verify tokens still work (archive mode). |
| T3-23 | Integration | Archive mode disables uploads and task completion | Set transaction to closed (archive mode). Attempt file upload via portal. Verify 400 with "archive mode" error. Attempt action item completion. Verify 400. GET endpoints still return data (read-only). |
| T3-24 | Integration | Rate limiting on portal endpoints | Send 35 requests in 60 seconds with same token. Verify first 30 succeed (200). Last 5 return 429. |
| T3-25 | Integration | Portal access logging | Access portal 5 times from different endpoints. GET access logs as agent. Verify 5 log entries with correct IP, user_agent, endpoint, and timestamps. |
| T3-26 | Integration | Duplicate email handling (same email, two buyer parties) | Create two buyer parties with same email. Generate tokens for both. Verify two separate tokens, both independently accessible, returning correct party data for each. |
| T3-27 | Integration | Agent file review -- approve flow | Party uploads file. Agent calls PATCH review with `review_status = "approved"` and `visibility = ["buyer", "lender"]`. Verify file `quarantine = FALSE`, visibility set, file now appears in buyer's and lender's document list but NOT seller's. |
| T3-28 | Integration | Agent file review -- reject flow | Party uploads file. Agent calls PATCH review with `review_status = "rejected"`. Verify file remains in quarantine, `review_status = "rejected"`, file not visible to any portal user. |
| T3-29 | Integration | Portal response caching | GET milestones. Update a milestone via agent API. GET milestones within cache TTL (30 seconds) -- may return stale data. Wait for cache TTL. GET milestones -- verify fresh data returned. |
| T3-30 | Integration | Cache busting on agent action | GET milestones (cached). Agent updates milestone status. System busts cache. Immediately GET milestones. Verify fresh data (not stale cached response). |
| T3-31 | Unit | Portal scope service -- all 6 roles | Unit test `get_visible_milestone_types`, `get_visible_document_filter`, `get_visible_contacts` for buyer, seller, lender, attorney, inspector, and other_agent roles. |
| T3-32 | Integration | portal_enabled = FALSE blocks portal access | Set party's `portal_enabled = FALSE`. Attempt to access portal with existing token. Verify 404. Attempt to generate new token. Verify 400. |
| T3-33 | Integration | Action item auto-generation for portal parties | Create a transaction with a buyer party, apply milestone template. Verify that portal-specific action items (upload pre-approval, deliver earnest money) are auto-generated with correct `party_id` and `action_type`. |

### 8.2 Phase 1 Regression Tests

All Phase 1 tests must continue to pass after Phase 3 changes. Key regression risk areas:

| Test ID | Original Feature | Regression Risk | Verification |
|---------|-----------------|-----------------|--------------|
| R1-01 | Transaction CRUD | New columns (`portal_branding_color`, `portal_branding_logo_url`) added to `transactions` table could break serialization or default behavior | Run all transaction create/read/update/list tests. Verify new columns default to NULL and do not appear in responses unless explicitly set. |
| R1-02 | Party CRUD | New column (`portal_enabled`) and new relationship (`portal_tokens`) on `parties` table could affect party queries or serialization | Run all party create/read/update/delete tests. Verify `portal_enabled` defaults to TRUE. Verify party deletion still works (token cascade tested separately in T3-21). |
| R1-03 | File upload and retrieval | New columns (`visibility`, `uploaded_by_party_id`, `review_status`, `reviewed_at`, `review_notes`, `quarantine`) on `files` table could break existing agent-side file operations | Run all file upload/download/list tests. Verify new columns default to appropriate values (visibility=NULL, quarantine=FALSE). Verify agent-uploaded files are unaffected by quarantine logic. |
| R1-04 | Milestone CRUD | No direct changes to milestones table, but portal queries read milestones. Verify existing milestone create/edit/delete operations are unaffected. | Run all milestone CRUD tests. Verify no performance regression from new portal-related indexes. |
| R1-05 | AI contract parsing | No changes to parsing logic. Verify parser output still populates transaction fields correctly after model changes. | Run 3 sample contract parsing tests. Verify confidence scores and extracted fields match expectations. |
| R1-06 | Today View dashboard | Action items table has new columns. Verify Today View still correctly groups and displays agent-only action items. Portal action items (with `party_id` set) should NOT appear in the Today View. | Run Today View endpoint test. Verify only `party_id IS NULL` action items appear. Verify grouping and sorting unchanged. |
| R1-07 | Health score calculation | No changes to health score algorithm, but verify it still works correctly after transaction table modifications. | Run health score tests for green, yellow, and red scenarios. Verify scores unchanged. |
| R1-08 | Transaction detail view | New "Portal" tab added to transaction detail. Verify all existing tabs (Overview, Milestones, Parties, Files, Amendments) still render correctly. | E2E navigation test: visit each tab on transaction detail, verify no rendering errors. |
| R1-09 | Milestone templates | No changes to template system. Verify template application still creates milestones with correct dates. | Run template application test with GA Conventional Buyer template. Verify 18 milestones created. |
| R1-10 | Action items (agent-only) | New columns on action_items table. Verify agent-only action items (Phase 1) still work: create, snooze, dismiss, complete. Verify portal columns are NULL for agent-only items. | Run full action item CRUD test cycle for agent-only items. |

### 8.3 Phase 2 Regression Tests

All Phase 2 tests must continue to pass. Key regression areas:

| Test ID | Original Feature | Regression Risk | Verification |
|---------|-----------------|-----------------|--------------|
| R2-01 | Email generation via Resend | Portal link inclusion in emails modifies email templates. Verify email generation still works, portal link section is added correctly, and no formatting breaks in existing email content. | Generate 3 different email types. Verify portal link section present when token exists. Verify email renders correctly in HTML preview. |
| R2-02 | Email delivery | Portal links in email body could affect spam scoring or link tracking. Verify Resend delivery succeeds with portal URLs in the body. | Send test email with portal link via Resend. Verify delivery webhook fires. Verify portal URL is clickable in delivered email. |
| R2-03 | Escalation chains | No direct changes to escalation logic. Verify escalation still fires at correct thresholds. | Run escalation chain test: milestone goes overdue, verify L0-L3 fire at correct intervals. |
| R2-04 | Notification preferences | No changes to preference storage or behavior. Verify agent can still read and update notification preferences. | GET and PATCH notification preferences. Verify round-trip correctness. |
| R2-05 | Celery beat tasks | New Celery tasks added for portal (access log cleanup, token expiration). Verify existing tasks (check_milestone_reminders, send_queued_emails, generate_daily_digest) still run on schedule without interference. | Verify Celery beat schedule includes both existing and new tasks. Run existing tasks manually and verify correct behavior. |
| R2-06 | Draft approval flow | Portal action item completions create notifications via the same notification system. Verify existing draft approval flow is unaffected. | Create email draft. Approve. Verify email queued and sent. |
| R2-07 | Communication log | Portal-related events (action item completions, file uploads) may create communication records. Verify the communication log on transaction detail still renders correctly with mixed email and portal event entries. | View communication log for transaction with both email and portal activity. Verify all entries display correctly. |
| R2-08 | Bounce handling | No changes to bounce logic. Verify hard bounces still mark party email as bounced and stop future sends. | Simulate bounce webhook. Verify party marked bounced. Verify no portal-related interference. |
| R2-09 | Double-send prevention | No changes to idempotency logic. Verify duplicate send prevention still works. | Trigger duplicate email send. Verify idempotency check prevents second send. |
| R2-10 | Authentication isolation | Portal endpoints are public. Verify authenticated endpoints remain protected. Verify portal tokens cannot access authenticated endpoints. | Attempt to call `GET /api/transactions` with a portal token in the Authorization header. Verify 401. Attempt to call `POST /api/transactions/{id}/portal/tokens` without auth. Verify 401. |

---

## 9. Implementation Order

### Week 7: Backend Foundation -- Data Model, Services, and API

| Day | Tasks | Files Created/Modified | Deliverable |
|-----|-------|----------------------|-------------|
| **Day 1** | **Database migration.** Create Alembic migration for: (a) new `portal_tokens` table with all columns and indexes, (b) new `portal_access_logs` table with all columns and indexes, (c) new columns on `action_items` table (`party_id`, `action_type`, `file_id`, `created_by`), (d) new columns on `files` table (`visibility`, `uploaded_by_party_id`, `review_status`, `reviewed_at`, `review_notes`, `quarantine`), (e) new column on `parties` table (`portal_enabled`), (f) new columns on `transactions` table (`portal_branding_color`, `portal_branding_logo_url`). Run migration. Verify all existing tests still pass. | `backend/alembic/versions/xxx_phase3_portal_tables.py` | Migration runs cleanly on fresh and existing databases. All Phase 1 and 2 tests pass. |
| **Day 2** | **SQLAlchemy models and Pydantic schemas.** Create `PortalToken` model with relationships to Party and Transaction. Create `PortalAccessLog` model. Update `ActionItem` model with new columns. Update `File` model with new columns. Update `Party` model with `portal_enabled`. Update `Transaction` model with branding columns. Create Pydantic schemas: `PortalTokenCreate`, `PortalTokenResponse`, `PortalOverview`, `PortalMilestone`, `PortalActionItem`, `PortalDocument`, `PortalContact`, `FileReviewUpdate`, `VisibilityUpdate`. | `backend/app/models/portal_token.py`, `backend/app/models/portal_access_log.py`, `backend/app/schemas/portal.py`, modifications to existing model and schema files | Models and schemas in place. Import tests pass. Pydantic validation tests pass. |
| **Day 3** | **Portal token service.** Implement `portal_token_service.py`: create token, revoke token, regenerate token, bulk generate, lookup (with validation for revoked/expired/disabled), update `last_accessed_at`, token lifecycle management (party removal cascade, transaction closure cascade). Unit tests for all token lifecycle scenarios. | `backend/app/services/portal_token_service.py`, `backend/tests/test_portal_token_service.py` | All token CRUD operations functional. 15+ unit tests passing. |
| **Day 4** | **Role-based scope service.** Implement `portal_scope_service.py`: functions that filter milestones, documents, contacts, and action items by party role. This is the security-critical layer. Functions: `get_visible_milestones(role, all_milestones)`, `get_visible_documents(role, all_files)`, `get_visible_contacts(role, all_parties, agent)`, `get_visible_action_items(party_id, all_items)`. Comprehensive unit tests for ALL 6 party roles with edge cases (empty data, null fields, mixed roles, documents with NULL visibility). | `backend/app/services/portal_scope_service.py`, `backend/tests/test_portal_scope_service.py` | Scoping functions with 30+ unit tests. 100% branch coverage for all 6 roles. |
| **Day 5** | **Authenticated API endpoints (agent-side).** Implement all endpoints from Section 5.1: token management (create, bulk, list, regenerate, revoke), access logs, portal action item CRUD (extending Phase 1 action items endpoint), file review (approve/reject), document visibility update. Rate limiting middleware setup for portal endpoints (Redis sliding window). Integration tests for all agent-side endpoints. | `backend/app/api/portal.py`, `backend/app/api/portal_admin.py`, modifications to `backend/app/api/files.py`, `backend/tests/test_portal_admin_api.py` | All agent-side endpoints functional with integration tests. Rate limiting configured. |

### Week 8: Portal Frontend and Public API

| Day | Tasks | Files Created/Modified | Deliverable |
|-----|-------|----------------------|-------------|
| **Day 1** | **Public API endpoints (portal-side).** Implement all endpoints from Section 5.2: main portal overview, milestones, action items, documents, document view (signed URL), contacts. Implement token validation middleware (shared across all portal endpoints). Implement Redis caching layer with cache key patterns and TTLs from Section 5.3. Integration tests for all public endpoints with role-based scoping verification. | `backend/app/api/portal_public.py`, `backend/app/middleware/portal_auth.py`, `backend/app/services/portal_cache_service.py`, `backend/tests/test_portal_public_api.py` | All public endpoints functional. Rate limiting active. Caching working. Role scoping verified. |
| **Day 2** | **Portal upload endpoint.** Implement `POST /api/portal/{token}/upload` with full file validation pipeline: extension whitelist, size check, magic byte inspection via `python-magic`, S3 quarantine upload, action item linking, agent notification creation. Add `python-magic` to requirements.txt. Integration tests for happy path and all rejection scenarios (wrong type, oversized, MIME mismatch). | `backend/app/services/portal_upload_service.py`, modifications to `backend/app/api/portal_public.py`, `backend/tests/test_portal_upload.py` | Upload endpoint functional with all validation. Quarantine flow working. Agent notifications created. |
| **Day 3** | **Portal frontend shell.** Create portal route configuration in App.tsx. Build `PortalLayout`, `PortalHeader`, `PortalFooter`, `PortalErrorPage`, `PortalLoadingPage`. Configure React Router for `/portal/:token` route tree. Set up API client functions for portal endpoints (separate from authenticated API client -- no auth headers). Verify portal shell renders, error states work, route tree configured. | `frontend/src/pages/Portal/PortalLayout.tsx`, `frontend/src/pages/Portal/PortalHeader.tsx`, `frontend/src/pages/Portal/PortalFooter.tsx`, `frontend/src/pages/Portal/PortalErrorPage.tsx`, `frontend/src/pages/Portal/PortalLoadingPage.tsx`, `frontend/src/lib/portalApi.ts`, modifications to `frontend/src/App.tsx` | Portal shell renders at `/portal/:token`. Error page works for invalid tokens. Loading skeleton displays during fetch. |
| **Day 4** | **Portal core components.** Build `ProgressBar`, `MilestoneTimeline`, `MilestoneItem`, `ActionItemsList`, `ActionItemCard`, `StatusDot`, `Badge`, `RelativeDate`. Wire components to portal API endpoints. Implement optimistic updates for action item completion. Implement basic responsive layout (mobile-first). | `frontend/src/pages/Portal/ProgressBar.tsx`, `frontend/src/pages/Portal/MilestoneTimeline.tsx`, `frontend/src/pages/Portal/MilestoneItem.tsx`, `frontend/src/pages/Portal/ActionItemsList.tsx`, `frontend/src/pages/Portal/ActionItemCard.tsx`, `frontend/src/components/ui/StatusDot.tsx`, `frontend/src/components/ui/RelativeDate.tsx` | Core portal page renders with live data. Progress bar, milestones, and action items display correctly. |
| **Day 5** | **Portal remaining components.** Build `DocumentList`, `DocumentRow`, `FileUploadInline`, `UploadProgress`, `ContactCard`, `FileIcon`. Assemble complete `PortalPage` component with all sections. Test full portal rendering with mock data and live API. Verify document view opens signed URL. Verify file upload works end-to-end from frontend to S3 quarantine. | `frontend/src/pages/Portal/DocumentList.tsx`, `frontend/src/pages/Portal/DocumentRow.tsx`, `frontend/src/pages/Portal/FileUploadInline.tsx`, `frontend/src/pages/Portal/ContactCard.tsx`, `frontend/src/pages/Portal/PortalPage.tsx`, `frontend/src/components/ui/FileIcon.tsx`, `frontend/src/components/ui/UploadProgress.tsx` | Full portal page functional: view milestones, view documents, upload files, complete tasks, see contacts. |

### Week 9: Agent UI, Email Integration, Polish, and Testing

| Day | Tasks | Files Created/Modified | Deliverable |
|-----|-------|----------------------|-------------|
| **Day 1** | **Agent-side portal management UI.** Build `PortalLinksPanel`, `PortalLinkRow`, `CopyToClipboard`, `PortalPreviewButton`, `SendPortalLinkButton`. Add "Portal" tab to transaction detail page. Generate, copy, regenerate, revoke actions all functional. | `frontend/src/pages/TransactionDetail/PortalLinksPanel.tsx`, `frontend/src/pages/TransactionDetail/PortalLinkRow.tsx`, `frontend/src/components/ui/CopyToClipboard.tsx`, modifications to `frontend/src/pages/TransactionDetail/index.tsx` | Agent can manage portal links from transaction detail page. All CRUD actions work. |
| **Day 2** | **Agent-side action item and file review UI.** Build `ActionItemManager`, `ActionItemForm`, `FileReviewQueue`, `DocumentVisibilityEditor`, `PortalAccessLog`. Wire to API endpoints. Agent can create/edit/delete action items, review uploaded files (approve/reject), control document visibility, view portal access history. | `frontend/src/pages/TransactionDetail/ActionItemManager.tsx`, `frontend/src/pages/TransactionDetail/ActionItemForm.tsx`, `frontend/src/pages/TransactionDetail/FileReviewQueue.tsx`, `frontend/src/pages/TransactionDetail/DocumentVisibilityEditor.tsx`, `frontend/src/pages/TransactionDetail/PortalAccessLog.tsx` | Agent can manage action items, review uploads, control document visibility. Full management UI functional. |
| **Day 3** | **Email template integration.** Modify Phase 2 email templates to include portal links. When generating an email for a party who has an active portal token, include a "View Your Transaction Portal" section with the portal URL. Handle the duplicate-email party case (one email with multiple portal links). Add `SendPortalLinkButton` to the `PortalLinkRow` component (standalone email just for the portal link). Test email rendering with portal links. | Modifications to Phase 2 email template files, `backend/app/services/email_template_service.py`, `backend/app/templates/email/portal_link.html` | Portal links automatically included in transaction emails. Duplicate-email case handled. Standalone "Send Portal Link" email works. |
| **Day 4** | **Mobile optimization and accessibility.** Responsive testing on iOS Safari (iPhone 13) and Android Chrome (Pixel 7). Fix layout issues, ensure 44px minimum tap targets, verify no horizontal scrolling at 375px. Accessibility audit: check color contrast (WCAG AA), heading hierarchy, ARIA labels, focus states, screen reader compatibility. Add Celery tasks for portal maintenance: access log cleanup (180-day retention), expired token cleanup. | Modifications to all portal frontend components for responsive fixes, `backend/app/tasks/portal_maintenance.py` | Portal passes mobile usability testing. WCAG AA automated checks pass. Maintenance tasks scheduled. |
| **Day 5** | **Full test suite execution and bug fixes.** Run all 33 Phase 3 new tests. Run all 10 Phase 1 regression tests. Run all 10 Phase 2 regression tests. Performance testing: portal load time on simulated 4G (target < 2s LCP). Load testing: 50 concurrent portal accesses. Fix any failures. Final code review and cleanup. | All test files, potential bug fix commits | All tests pass. Portal loads in < 2 seconds on 4G. Zero critical bugs. Zero high-severity bugs. |

---

## 10. Dependencies

### Required from Previous Phases

| Dependency | Phase | What It Provides | Used By (Phase 3) |
|------------|-------|-----------------|---------------------|
| Transaction data model | Phase 1 | `transactions` table with `status`, `property_address`, `property_city`, `property_state`, `property_zip`, `closing_date`, `financing_type`, `representation_side` | Portal overview display, progress calculation, archive mode detection |
| Party data model | Phase 1 | `parties` table with `role`, `name`, `email`, `phone`, `company`, `is_primary` | Token generation (one token per party), role-based scoping, contact visibility, duplicate-email detection |
| Milestone data model | Phase 1 | `milestones` table with `type`, `title`, `due_date`, `status`, `responsible_party_role`, `completed_at`, `sort_order` | Portal milestone timeline, progress percentage calculation, role-based milestone scoping, action item auto-generation triggers |
| File data model | Phase 1 | `files` table with `name`, `content_type`, `url`, `transaction_id` | Portal document list, file upload and quarantine system, signed URL generation for document viewing |
| Health score / progress calculation | Phase 1 | Algorithm that computes transaction progress percentage from milestone completion ratios | Portal progress bar (`progress_percent` field in overview response) |
| Action items system | Phase 1 | `action_items` table with `transaction_id`, `milestone_id`, `type`, `title`, `status`, `due_date`, `completed_at`, `agent_id` | Extended with `party_id`, `action_type`, `file_id`, `created_by` for portal action items. Same table, new columns. |
| S3 storage service | Phase 1 | Configured S3/MinIO integration for file upload, signed URL generation | Portal file uploads (quarantine prefix), document viewing (signed URLs) |
| Email delivery (Resend) | Phase 2 | Configured Resend integration with template rendering and delivery tracking | Sending portal links to parties via email, standalone "Send Portal Link" emails |
| Email template system | Phase 2 | Role-specific email templates with variable interpolation | Adding portal link section to existing email templates, handling duplicate-email party case |
| Agent notification system | Phase 2 | In-app notification creation and display | Notifying agent when party completes an action item, uploads a file, or when suspicious portal access patterns are detected |
| Celery beat infrastructure | Phase 2 | Celery worker and beat services running in Docker, Redis as broker | Portal maintenance tasks (access log cleanup, expired token cleanup) |
| Redis caching | Phase 1/2 | Redis instance running in Docker, used for caching and Celery broker | Portal response caching with `portal:` key prefix, rate limiting with sliding window counters |

### No New External Services Required

Phase 3 builds entirely on the existing infrastructure stack. No new API keys, no new third-party integrations, no new Docker services.

- **S3/MinIO:** Already configured in Phase 1. Portal uploads use the same S3 bucket with a new `/quarantine/` prefix path. Add an S3 lifecycle policy to auto-delete objects in the quarantine prefix older than 30 days.
- **Redis:** Already configured in Phases 1 and 2. Portal caching uses the same Redis instance with `portal:` key prefix. Rate limiting uses Redis sliding window counters. Additional memory: ~750 KB for 300 active portal tokens (negligible).
- **Resend:** Already configured in Phase 2. Portal links are added to existing email templates. No new Resend API calls beyond what Phase 2 already supports.
- **PostgreSQL:** Already running. Phase 3 adds 2 new tables and modifies 4 existing tables via Alembic migration.

### New Python Dependencies

```
python-magic>=0.4.27    # For file magic byte inspection (MIME type validation)
```

No other new Python packages. `python-magic` requires `libmagic` to be installed in the Docker image. Add to the backend Dockerfile:

```dockerfile
RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*
```

### Infrastructure Considerations

| Consideration | Details | Action Required |
|---------------|---------|-----------------|
| S3 quarantine prefix | Party-uploaded files are stored at `quarantine/{transaction_id}/{uuid}_{filename}`. Files may accumulate if agents do not review them. | Add S3 lifecycle policy: auto-delete objects in `quarantine/` prefix older than 30 days. |
| Redis memory for portal caching | Each portal token has up to 5 cache keys, each ~200-500 bytes. With 300 active portals: ~750 KB. | No action needed. Well within existing Redis memory allocation. |
| `portal_access_logs` table growth | Estimated volume: 10 portal visits/day/party across 50 transactions with 6 parties each = ~3,000 rows/day = ~540,000 rows over 180 days. | Implement 180-day retention policy via daily Celery task. Add `accessed_at` index for efficient cleanup queries. |
| Rate limiting state | Redis sliding window counters for token-based and IP-based rate limits. Each counter is a sorted set with timestamps. | No action needed. Memory impact: ~100 bytes per active counter. Counters auto-expire after the rate limit window. |
| Portal frontend bundle size | Portal components should be code-split from the authenticated app to keep initial load small. Target: < 100 KB gzipped for portal-specific JS. | Use React.lazy() and dynamic import for the portal route tree. Verify with `npm run build` output analysis. |
| `python-magic` system dependency | Requires `libmagic1` system library in the Docker container. | Add `apt-get install libmagic1` to the backend Dockerfile. Verify in CI/CD pipeline. |
| CORS configuration | Portal endpoints must accept requests from the portal's origin. If the portal is served from the same domain as the API, this is already handled. If they are on different subdomains, CORS must be configured. | Verify CORS settings in FastAPI middleware. Add portal domain to allowed origins if needed. |

---

*Phase 3 Complete -> Proceed to Phase 4: AI Advisor*
