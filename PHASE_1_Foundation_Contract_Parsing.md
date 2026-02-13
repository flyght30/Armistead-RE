# Phase 1: Foundation & Contract Parsing

**Timeline:** Weeks 1-4  
**Status:** Not Started  
**CoV Status:** Verified (see below)

---

## 1. Phase Objective

Build the project foundation (frontend, backend, database, auth, file storage) and deliver the core differentiator: AI-powered contract parsing that extracts all transaction data from an uploaded purchase agreement.

**Deliverable:** An agent can sign up, upload an executed contract, see AI-extracted data, edit/confirm it, and have a transaction record created.

---

## 2. Scope

### In Scope
- Project scaffolding (React + FastAPI + PostgreSQL + Redis + S3)
- User authentication and account creation
- File upload infrastructure
- Contract Parser AI Agent (Claude API integration)
- Transaction CRUD (create, read, update, delete)
- Party management (add, edit, remove parties)
- Representation side selection (buyer/seller/dual)
- Basic dashboard showing all transactions
- Transaction detail view with extracted data

### Out of Scope (This Phase)
- Email generation or sending
- Milestone tracking
- Inspection analysis
- Follow-up automation
- State-specific configuration (use Alabama defaults)

---

## 3. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-1.1 | As an agent, I can create an account so I can use the platform | Account created via Clerk; agent can log in; profile includes name, email, phone, brokerage, license number, state |
| US-1.2 | As an agent, I can upload a PDF of an executed purchase agreement | File accepted (PDF, JPG, PNG); stored in S3; preview visible in UI; max file size 25MB |
| US-1.3 | As an agent, I see AI-extracted data from my uploaded contract | All fields populated within 30 seconds; confidence scores shown; low-confidence fields highlighted |
| US-1.4 | As an agent, I can review and correct extracted data | Every field is editable; agent can add missing parties; agent can change representation side |
| US-1.5 | As an agent, I can confirm the data and create a transaction | Confirmation saves transaction to database; status set to "active"; dashboard shows new transaction |
| US-1.6 | As an agent, I can view all my transactions on a dashboard | Dashboard lists all transactions with property address, status, closing date, and representation side |
| US-1.7 | As an agent, I can view full details of any transaction | Detail page shows all extracted data, all parties, uploaded contract, and transaction status |
| US-1.8 | As an agent, I can edit transaction details after creation | All fields remain editable; changes logged in amendments table |
| US-1.9 | As an agent, I can delete/archive a transaction | Soft delete; transaction hidden from dashboard but data retained |

---

## 4. Technical Tasks

### 4.1 Backend Setup (Week 1)

| Task | Description | Estimate |
|------|-------------|----------|
| T-1.1 | Initialize FastAPI project with project structure | 2h |
| T-1.2 | Set up PostgreSQL with Docker Compose | 2h |
| T-1.3 | Configure SQLAlchemy 2.0 + Alembic migrations | 3h |
| T-1.4 | Create database models (users, transactions, parties, amendments) | 4h |
| T-1.5 | Set up Redis for caching | 1h |
| T-1.6 | Configure AWS S3 (or MinIO for local dev) for document storage | 3h |
| T-1.7 | Implement Clerk authentication middleware | 4h |
| T-1.8 | Set up logging, error handling, and CORS | 2h |
| T-1.9 | Docker Compose for full local dev environment | 3h |

### 4.2 API Development (Week 2)

| Task | Description | Estimate |
|------|-------------|----------|
| T-1.10 | POST /api/transactions — create with file upload | 4h |
| T-1.11 | GET /api/transactions — list with pagination/filtering | 3h |
| T-1.12 | GET /api/transactions/:id — full detail with parties | 2h |
| T-1.13 | PATCH /api/transactions/:id — update fields (with amendment logging) | 3h |
| T-1.14 | DELETE /api/transactions/:id — soft delete | 1h |
| T-1.15 | CRUD endpoints for parties (nested under transaction) | 3h |
| T-1.16 | POST /api/transactions/:id/parse — trigger AI parsing | 4h |
| T-1.17 | POST /api/transactions/:id/confirm — confirm and activate | 2h |
| T-1.18 | File upload endpoint with S3 integration | 3h |

### 4.3 AI Integration (Week 2-3)

| Task | Description | Estimate |
|------|-------------|----------|
| T-1.19 | Claude API client wrapper with retry/error handling | 4h |
| T-1.20 | Contract Parser prompt engineering and schema design | 8h |
| T-1.21 | PDF text extraction pipeline (PyMuPDF) | 4h |
| T-1.22 | Image-based contract handling (send as vision input) | 3h |
| T-1.23 | Confidence score calculation and low-confidence flagging | 3h |
| T-1.24 | Cash transaction detection (no lender workflow) | 2h |
| T-1.25 | Multi-party detection (multiple buyers/sellers) | 2h |
| T-1.26 | Non-standard contract detection and flagging | 2h |
| T-1.27 | Parser response validation (Pydantic schema) | 3h |

### 4.4 Frontend Development (Weeks 3-4)

| Task | Description | Estimate |
|------|-------------|----------|
| T-1.28 | Initialize React + TypeScript + Tailwind project | 2h |
| T-1.29 | Clerk authentication integration (login, signup, profile) | 4h |
| T-1.30 | Dashboard page — transaction list with status badges | 6h |
| T-1.31 | New Transaction page — file upload with drag-and-drop | 4h |
| T-1.32 | Parsing progress indicator (loading state while AI works) | 2h |
| T-1.33 | Data Review page — all extracted fields, editable, confidence indicators | 8h |
| T-1.34 | Party management UI — add/edit/remove parties, role selection | 4h |
| T-1.35 | Representation side selector (buyer/seller/dual) with workflow explanation | 2h |
| T-1.36 | Transaction detail page — full read view with all data | 6h |
| T-1.37 | Basic responsive layout and navigation | 4h |
| T-1.38 | API integration layer (React Query + API client) | 4h |

### 4.5 Testing & DevOps (Week 4)

| Task | Description | Estimate |
|------|-------------|----------|
| T-1.39 | Backend unit tests (services, models) | 6h |
| T-1.40 | API integration tests (all endpoints) | 6h |
| T-1.41 | AI parser accuracy tests (5+ sample contracts) | 4h |
| T-1.42 | Frontend component tests (React Testing Library) | 4h |
| T-1.43 | E2E test: upload → parse → review → confirm flow | 4h |
| T-1.44 | GitHub Actions CI pipeline | 3h |
| T-1.45 | Environment configuration (dev, staging, prod) | 3h |

---

## 5. AI Contract Parser Specification

### 5.1 Extraction Schema

```json
{
  "property": {
    "address": { "value": "string", "confidence": 0.0-1.0 },
    "city": { "value": "string", "confidence": 0.0-1.0 },
    "state": { "value": "string", "confidence": 0.0-1.0 },
    "zip": { "value": "string", "confidence": 0.0-1.0 },
    "legal_description": { "value": "string", "confidence": 0.0-1.0 }
  },
  "financial": {
    "purchase_price": { "value": "number", "confidence": 0.0-1.0 },
    "earnest_money": { "value": "number", "confidence": 0.0-1.0 },
    "financing_type": { "value": "conventional|fha|va|usda|cash|owner_financing", "confidence": 0.0-1.0 }
  },
  "parties": {
    "buyers": [
      { "name": "string", "email": "string|null", "phone": "string|null", "confidence": 0.0-1.0 }
    ],
    "sellers": [
      { "name": "string", "email": "string|null", "phone": "string|null", "confidence": 0.0-1.0 }
    ],
    "buyer_agent": { "name": "string", "email": "string|null", "phone": "string|null", "brokerage": "string|null", "confidence": 0.0-1.0 },
    "seller_agent": { "name": "string", "email": "string|null", "phone": "string|null", "brokerage": "string|null", "confidence": 0.0-1.0 },
    "lender": { "name": "string|null", "company": "string|null", "email": "string|null", "phone": "string|null", "confidence": 0.0-1.0 },
    "attorney_or_title": { "name": "string|null", "company": "string|null", "email": "string|null", "phone": "string|null", "confidence": 0.0-1.0 }
  },
  "dates": {
    "contract_date": { "value": "date", "confidence": 0.0-1.0 },
    "closing_date": { "value": "date", "confidence": 0.0-1.0 },
    "earnest_money_deadline": { "value": "date|null", "confidence": 0.0-1.0 },
    "inspection_deadline": { "value": "date|null", "confidence": 0.0-1.0 },
    "appraisal_contingency_deadline": { "value": "date|null", "confidence": 0.0-1.0 },
    "financing_contingency_deadline": { "value": "date|null", "confidence": 0.0-1.0 }
  },
  "special_stipulations": { "value": "string|null", "confidence": 0.0-1.0 },
  "contract_type": "standard_residential|non_standard|unrecognized",
  "detected_representation_side": "buyer|seller|dual|unknown"
}
```

### 5.2 System Prompt (Contract Parser Agent)

```
You are a real estate contract parsing agent specializing in residential 
purchase agreements. Your job is to extract all structured data from 
executed contracts with high accuracy.

RULES:
1. Extract ONLY what is explicitly stated in the document
2. For fields not found, return null with confidence 0.0
3. For fields found but ambiguous, return best guess with confidence 0.3-0.6
4. For clearly stated fields, return with confidence 0.8-1.0
5. If the document is not a standard residential purchase agreement, 
   set contract_type to "non_standard" or "unrecognized"
6. Detect financing type from loan type, down payment, or explicit statements
7. If no lender is mentioned and terms suggest cash, set financing_type to "cash"
8. Return all dates in ISO 8601 format (YYYY-MM-DD)
9. For multiple buyers/sellers, include all in their respective arrays

Return your response as valid JSON matching the provided schema exactly.
```

---

## 6. Chain-of-Verification: Phase 1

### Step 1: Baseline
Phase 1 delivers project scaffolding, auth, file upload, AI contract parsing, and a basic dashboard.

### Step 2: Self-Questioning

**Q1:** What happens if the uploaded PDF is a scanned image (no selectable text)?
**Q2:** How does the system handle a contract that is partially executed (missing signatures)?
**Q3:** What if the Claude API is down or returns an error during parsing?
**Q4:** Are there rate limit concerns with Claude API for the parsing operation?
**Q5:** What if the agent uploads a multi-file contract (addendums, amendments as separate files)?

### Step 3: Independent Verification

**A1 — Scanned PDFs:** PyMuPDF can extract text from text-based PDFs, but scanned contracts are essentially images. The system must detect when extracted text is empty/minimal and fall back to sending the document as images to Claude's vision capability. This is already partially addressed in T-1.22 but should be the PRIMARY path for any contract with < 100 characters of extracted text.
**Resolution:** Text extraction first; if insufficient, fall back to vision input. Both paths tested.

**A2 — Partially Executed Contracts:** The AI parser should detect whether all signature blocks are filled. If the contract appears unsigned or partially signed, flag it with a warning but still extract available data. The agent can override and proceed.
**Resolution:** Add a `fully_executed` boolean to the extraction schema. Show warning if false.

**A3 — API Failures:** Claude API outages or errors need graceful handling. The parse endpoint should return a clear error state. The UI should show "Parsing failed — try again" with a retry button. Implement exponential backoff (3 retries, 2/4/8 second delays).
**Resolution:** Retry logic in Claude client wrapper (T-1.19). Error state in UI.

**A4 — Rate Limits:** Claude API has rate limits per minute/hour. For a single agent uploading one contract at a time, this is unlikely to be an issue. At scale (many agents simultaneously), implement a queue. For Phase 1, simple retry-on-429 is sufficient.
**Resolution:** Handle 429 status codes with backoff in client wrapper.

**A5 — Multi-File Contracts:** Real transactions often have addendums, amendments, and counter-offers as separate documents. Phase 1 should accept the primary purchase agreement only. Multi-document support (upload multiple files per transaction) is a Phase 2+ enhancement.
**Resolution:** Accept single file in Phase 1. Document multi-file as future enhancement.

### Step 4: Confidence Check
**Confidence: 96%** — All edge cases addressed with clear resolutions.

### Step 5: Implement
Proceed with Phase 1 as specified. Incorporate scanned PDF handling, API error recovery, and execution detection.

---

## 7. Definition of Done (Phase 1)

| Criteria | Verification |
|----------|-------------|
| Agent can create account and log in | Manual test + E2E test |
| Agent can upload PDF/image contract | Manual test + E2E test |
| AI extracts all fields within 30 seconds | Performance test (5 contracts) |
| Confidence scores displayed per field | Manual test |
| Low-confidence fields visually highlighted | Manual test |
| Agent can edit all extracted fields | Manual test + E2E test |
| Agent can add/remove/edit parties | Manual test + component test |
| Agent can select buyer/seller/dual representation | Manual test |
| Cash transactions detected (no lender fields) | Test with cash contract |
| Multi-party contracts handled (2+ buyers) | Test with multi-buyer contract |
| Non-standard contracts flagged | Test with commercial contract |
| Transaction saved to database on confirmation | Integration test |
| Dashboard shows all transactions | Manual test + E2E test |
| Transaction detail shows all data | Manual test |
| Edit after creation works with amendment logging | Integration test |
| Soft delete/archive works | Integration test |
| All API endpoints have tests | CI pipeline passes |
| Scanned PDF (image) contracts parse correctly | Test with scanned contract |
| API errors handled gracefully (retry + user message) | Integration test |

---

## 8. Test Plan

### 8.1 Unit Tests

| Test Area | Tests | Framework |
|-----------|-------|-----------|
| Transaction service | Create, read, update, soft-delete, list with filters | pytest |
| Party service | CRUD operations, role validation | pytest |
| Amendment service | Change logging, field tracking | pytest |
| AI client wrapper | Retry logic, error handling, timeout handling | pytest + mocks |
| Pydantic schemas | Validation of all request/response models | pytest |
| S3 service | Upload, signed URL generation | pytest + mocks |

### 8.2 Integration Tests

| Test | Steps | Expected Result |
|------|-------|----------------|
| Full parse flow | Upload PDF → trigger parse → validate response schema | All fields populated, valid JSON |
| Cash transaction detection | Upload cash contract → parse | financing_type = "cash", no lender party |
| Multi-buyer contract | Upload contract with 2 buyers → parse | 2 buyer parties extracted |
| Scanned PDF | Upload image-based PDF → parse | Falls back to vision, extracts successfully |
| Non-standard contract | Upload commercial contract → parse | contract_type = "non_standard", warning shown |
| Amendment logging | Create transaction → edit price → check amendments | Amendment record with old/new values |
| Auth protection | Call API without token | 401 Unauthorized |
| Auth isolation | Agent A tries to access Agent B's transaction | 403 Forbidden |

### 8.3 AI Accuracy Tests

| Contract Type | Min Accuracy | Test Count |
|--------------|-------------|-----------|
| Alabama standard residential (text PDF) | 90% of fields | 3 contracts |
| Alabama standard residential (scanned) | 85% of fields | 2 contracts |
| Cash transaction | Financing type correct | 1 contract |
| Multi-buyer | All buyers extracted | 1 contract |
| Non-standard | Correctly flagged | 1 contract |

**Accuracy measurement:** (fields correctly extracted without agent edit) / (total fields present in contract) × 100

### 8.4 E2E Tests (Cypress or Playwright)

| Test | Flow |
|------|------|
| Happy path | Sign up → Upload contract → Wait for parse → Review data → Confirm → See on dashboard |
| Edit and save | Open transaction → Edit price → Save → Verify amendment logged |
| Parse failure recovery | Upload → Simulate API error → See error message → Retry → Success |
| Empty dashboard | New user → See empty state with "Upload your first contract" CTA |

### 8.5 Performance Tests

| Test | Target |
|------|--------|
| Contract parse time (text PDF) | < 30 seconds |
| Contract parse time (scanned PDF) | < 45 seconds |
| Dashboard load (100 transactions) | < 2 seconds |
| File upload (10MB PDF) | < 5 seconds |
| API response (transaction detail) | < 500ms |

---

## 9. Phase 1 Success Criteria

| Metric | Target | How Measured |
|--------|--------|-------------|
| All user stories completed | 9/9 | Story acceptance criteria verified |
| AI extraction accuracy (text PDFs) | ≥ 90% | Accuracy tests on 3+ contracts |
| AI extraction accuracy (scanned PDFs) | ≥ 85% | Accuracy tests on 2+ contracts |
| Parse completes in < 30 seconds | 100% of text PDFs | Performance tests |
| All integration tests pass | 100% | CI pipeline |
| All E2E tests pass | 100% | CI pipeline |
| Zero critical security issues | 0 | Auth isolation tests |
| Agent can go from upload to confirmed transaction in < 5 minutes | Verified | Manual test timing |

---

*Phase 1 Complete → Proceed to Phase 2: Communications Engine*
