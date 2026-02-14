# Phase 6: Document Generation -- Templates, Repair Letters, Amendment Forms & Closing Checklists

**Timeline:** Weeks 15--17
**Status:** Not Started
**Depends On:** Phase 5 Complete
**CoV Status:** Verified (see Section 2)

---

## 1. Phase Overview

### Goal

Transform Armistead RE from a system that merely stores documents into one that generates them. Agents should be able to produce professional, branded PDF documents directly from transaction data -- repair request letters built from inspection findings, amendment forms pre-filled from price or date changes, milestone-based status update emails, closing prep checklists tailored to financing type and representation side, and post-closing summaries that capture the full arc of a deal. Every generated document flows through a preview-and-edit step so the agent retains full control, then exports as a clean PDF stored in MinIO alongside uploaded files.

### Timeline

| Week | Focus |
|------|-------|
| Week 15 | Data model, template engine (Jinja2 + WeasyPrint pipeline), seed templates, document generation API, agent branding API |
| Week 16 | Document-type-specific services (repair letter, amendment form, status update, closing checklist, post-closing summary), frontend document panel, preview/editor |
| Week 17 | Branding settings UI, email-send integration, PDF quality assurance, regression testing, performance tuning |

### Key Deliverables

1. **Template Engine** -- Jinja2 renders HTML from transaction data; WeasyPrint converts HTML to PDF. Operates as a reusable pipeline for any document type.
2. **Repair Request Letter** -- Auto-generated from inspection analysis items. The buyer's agent selects which findings to include, Claude writes a professional narrative, and the system produces a formatted letter addressed to the seller or seller's agent with itemized repair requests and cost estimates.
3. **Amendment Form** -- Pre-filled structured form showing old values, new values, effective date, and reason. No AI narrative needed; purely data-driven.
4. **Status Update Letter** -- AI-enhanced letter summarizing milestone progress, upcoming deadlines, and action items. Tone adjusts based on recipient role (client vs. lender vs. attorney).
5. **Closing Prep Checklist** -- Generated checklist of everything needed before closing day, conditioned on transaction type (cash vs. conventional vs. FHA/VA), representation side, and current milestone status. Items already completed are checked off.
6. **Post-Closing Summary** -- Comprehensive transaction record for the agent's files: property details, financial summary, full timeline, all parties, key documents, and an AI-written executive narrative.
7. **Agent Branding** -- Configurable letterhead with name, brokerage, license number, contact info, optional logo, and accent color. Injected into every generated document header.
8. **Preview and Edit Workflow** -- Agents see a full HTML preview identical to the PDF layout, can edit text sections, then finalize to produce the PDF.

---

## 2. Chain of Verification (CoV)

### Step 1: Baseline

Phase 6 introduces a document generation pipeline using Jinja2 templates and WeasyPrint PDF conversion. The system assembles transaction data, optionally generates AI narrative content via Claude, renders HTML, allows agent preview and editing, converts to PDF, and stores in MinIO. Five document types are supported: repair request letter, amendment form, status update letter, closing prep checklist, and post-closing summary.

### Step 2: Critical Questions

| # | Question | Risk Level | Resolution |
|---|----------|-----------|------------|
| 1 | What happens if WeasyPrint fails mid-render (memory, timeout, malformed CSS)? | High | Wrap all PDF conversion in try/except. On failure: log full traceback with template ID and transaction ID, return a user-friendly error ("Document generation failed -- please try again"), and never persist a partial or corrupt PDF. Set a 60-second timeout on the WeasyPrint call. Add a startup health check that renders a minimal test template to verify the pipeline works before accepting requests. |
| 2 | How do we handle template versioning when templates are updated or fixed? | Medium | Each `DocumentTemplate` row carries an integer `version` field. Only the row with `is_active = True` is used for new generations. When a template is updated, the old row is set `is_active = False` and a new row is inserted with `version = old_version + 1`. Each `GeneratedDocument` records the `template_version` used at generation time. Previously generated documents are never retroactively re-rendered. Regeneration always uses the current active template. |
| 3 | Do generated documents carry legal weight? What disclaimers are needed? | High | Generated documents are professional communications, not legal instruments. Repair request letters are negotiation tools. Amendment forms capture proposed changes but require formal legal execution via state-specific addenda. Every generated document includes a footer disclaimer: "This document is for informational purposes and does not constitute legal advice. Consult your attorney for legal questions." The repair letter is framed as a "request," not a "demand." The amendment form is labeled "Proposed Amendment" and references the need for formal legal execution. |
| 4 | How do we ensure repair letter data matches the actual inspection analysis? | Medium | Repair letter content is assembled by querying `inspection_items` directly from the database using the `analysis_id`. The service never re-interprets or summarizes raw data -- it passes exact `description`, `location`, `severity`, `estimated_cost_low`, `estimated_cost_high`, and `recommendation` values from the database into the template context. Claude generates only the narrative wrapper (introduction, closing paragraph), not the finding details themselves. The agent reviews and edits every word before finalizing. |
| 5 | What about state-specific legal requirements for repair requests and amendments? | High | Armistead does not generate state-mandated legal forms (GAR forms, TAR addenda, etc.). Those are produced by the state Realtor association or by attorneys. Our documents are agent-branded professional correspondence that accompanies or precedes formal legal paperwork. The system does not claim to produce legally binding documents. If a future phase adds state-form generation, it would require partnership with state associations for licensed form data. |
| 6 | How do we handle large documents (20+ page post-closing summary)? | Low | WeasyPrint handles multi-page output natively. Templates use CSS `page-break-before`, `page-break-after`, and `page-break-inside: avoid` directives to control pagination. A memory limit of 512 MB is set on the generation process. If rendering exceeds 60 seconds, the task times out. For documents exceeding 50 pages, the system warns the agent and suggests a summary version. In practice, even comprehensive post-closing summaries should stay under 15 pages. |
| 7 | What if Claude's AI-generated narrative contains factual errors or unprofessional language? | Medium | The AI prompt is tightly scoped with explicit rules: never fabricate data, reference only provided input values, use professional real estate language, and never make legal claims. The prompt includes few-shot examples of acceptable output. Critically, the agent always previews and can edit every AI-generated section before finalization. The `ai_generated_content` field in `generated_documents` stores the raw AI output for audit. If the AI call fails, the system generates the document with placeholder text ("AI content unavailable -- please write this section manually") rather than blocking the entire workflow. |
| 8 | How does the system handle concurrent generation requests (multiple agents, multiple documents)? | Low | Document generation is stateless per request. Each generation call assembles its own data context, renders its own template, and writes its own PDF. No shared mutable state exists between generation calls. WeasyPrint is invoked synchronously within the API request handler (not via Celery), because generation typically completes in under 5 seconds. If future load requires it, generation can be moved to a Celery task with a polling or WebSocket notification pattern. |
| 9 | What about the WeasyPrint system dependency chain (cairo, pango, GDK-pixbuf)? | Medium | WeasyPrint requires native libraries: `libcairo2`, `libpango-1.0`, `libgdk-pixbuf-2.0`, and `libffi`. These must be installed in the Docker image. The backend Dockerfile will add `apt-get install -y libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev` before `pip install weasyprint`. The Docker build should be tested on a clean image to verify all dependencies resolve. A CI step should render a test PDF to catch dependency issues before deployment. |
| 10 | How do we ensure branding (logo, colors) renders consistently across generated documents? | Low | Agent logos are stored in MinIO and referenced by absolute URL in the template context. The Jinja2 template uses an `<img>` tag with a fixed max-height (60px) and max-width (200px) to prevent oversized logos from breaking layout. The accent color is applied via a CSS variable (`--agent-accent`) injected into the template's `<style>` block. If no branding is configured, templates fall back to a minimal header with just the agent's name from the `users` table. Templates are tested with branding, without branding, and with only partial branding (e.g., name and phone but no logo). |
| 11 | Can the agent send generated documents as email attachments through the existing email system? | Low | Yes. The finalized PDF's MinIO URL is passed to the existing Communication/email pipeline (Phase 2). The `POST /api/transactions/:id/documents/:docId/send` endpoint accepts a `recipient_party_id`, retrieves the party's email, creates a `Communication` record with the PDF URL in the `attachments` JSON field, and dispatches via the existing Resend integration. The PDF is attached as a file, not linked. |
| 12 | How do we handle document deletion and cleanup of MinIO objects? | Low | Deleting a `GeneratedDocument` record (only allowed for `draft` status) also deletes the corresponding MinIO object if one exists. Finalized documents cannot be deleted through the API -- they are part of the transaction's permanent record. An agent can generate a new version (regenerate) but the old version is retained. A future admin cleanup job can purge orphaned MinIO objects, but this is not built in Phase 6. |

### Step 3: Confidence Check

**Confidence: 95%** -- The Jinja2 + WeasyPrint pipeline is well-established technology. Template versioning and the agent preview/edit step mitigate the two highest risks (stale templates and AI inaccuracies). The main residual risk is WeasyPrint's native dependency chain in Docker, which is addressed by explicit Dockerfile instructions and a CI render test.

---

## 3. Detailed Requirements

### 3.1 Template Engine Architecture

The document generation pipeline follows a five-stage process:

```
Stage 1: Data Assembly
  Transaction, parties, milestones, inspections, amendments, commissions
  -> filtered and structured per document type

Stage 2: AI Content Generation (conditional)
  Structured data + document-type prompt -> Claude API -> narrative HTML fragments
  (Only for: repair_request, status_update, post_closing_summary)

Stage 3: Template Rendering
  Data context + AI fragments + agent branding -> Jinja2 HTML template -> rendered HTML string

Stage 4: Agent Preview & Edit
  Rendered HTML displayed in browser -> agent edits text -> updated HTML saved

Stage 5: PDF Conversion & Storage
  Final HTML -> WeasyPrint -> PDF bytes -> MinIO upload -> URL recorded in generated_documents
```

Each stage is implemented as a distinct function so that failures are isolated and the pipeline can be resumed from any stage. For example, if WeasyPrint fails in Stage 5, the agent's edits from Stage 4 are already persisted and the agent can retry finalization without re-doing their edits.

### 3.2 Document Types -- Detailed Specifications

#### 3.2.1 Repair Request Letter

**Purpose:** A professional letter from the buyer's agent to the seller (or seller's agent) requesting repairs based on inspection findings. This is one of the most critical documents in a real estate transaction -- it sets the tone for repair negotiations.

**Source Data:**
- `InspectionAnalysis` -- executive_summary, total_estimated_cost_low/high, overall_risk_level
- `InspectionItem[]` -- agent selects a subset of items to include
- `Transaction` -- property_address, property_city, property_state, property_zip, contract_execution_date, closing_date
- `Party[]` -- buyer name, seller name, seller's agent name and company
- `AgentBranding` -- letterhead info

**AI Content (Claude):**
- Opening paragraph contextualizing the inspection and the buyer's concerns
- Per-item professional descriptions that expand on the raw finding data
- Closing paragraph stating the deadline for seller response and proposed next steps

**Template Sections:**
1. Agent letterhead (from branding)
2. Date and addressee block (seller or seller's agent)
3. Re: line with property address and contract date
4. Opening paragraph (AI-generated)
5. Itemized findings table: Description | Location | Severity | Estimated Cost Range | Requested Action
6. Total estimated repair cost range
7. Closing paragraph with response deadline (AI-generated)
8. Agent signature block
9. Disclaimer footer

**Generation Options (agent selects before generation):**
- Which inspection items to include (checkbox list of all items from the analysis)
- Response deadline date (default: 5 business days from generation date)
- Tone: "firm" | "collaborative" | "urgent" (adjusts AI prompt)
- Include cost estimates: yes/no (some agents prefer not to show costs)

#### 3.2.2 Amendment Form

**Purpose:** A structured document capturing proposed changes to the purchase agreement. Commonly used when the purchase price changes (e.g., after repair negotiations), the closing date shifts, or financing terms change.

**Source Data:**
- `Amendment` record(s) -- field_changed, old_value, new_value, reason
- `Transaction` -- all current values for context
- `Party[]` -- buyer and seller names for signature lines

**AI Content:** None. This is a purely data-driven structured form. Precision matters more than narrative.

**Template Sections:**
1. Agent letterhead
2. "PROPOSED AMENDMENT TO PURCHASE AGREEMENT" title
3. Property address and original contract date
4. Party names (buyer and seller)
5. Amendment table: Field | Current Value | Proposed New Value
6. Reason for amendment (free text from Amendment.reason)
7. Effective date
8. Impact statement (e.g., "The proposed price change results in a reduction of $X from the original purchase price")
9. Signature lines for buyer, seller, buyer's agent, seller's agent
10. Disclaimer: "This proposed amendment requires execution of the applicable state-mandated amendment form to be legally binding."
11. Disclaimer footer

**Generation Options:**
- Which amendments to include (if multiple pending amendments exist)
- Effective date (default: generation date)
- Whether to include a signature block

#### 3.2.3 Status Update Letter

**Purpose:** A professional update letter sent to any party (buyer, seller, lender, attorney, title company) summarizing the current state of the transaction. Agents use this to keep all parties informed, especially during complex transactions with many moving parts.

**Source Data:**
- `Milestone[]` -- grouped by status (completed, in_progress, upcoming, overdue)
- `Transaction` -- property details, closing date, status
- `Party` -- the specific recipient
- Recent `Amendment[]` -- any changes since last update

**AI Content (Claude):**
- Opening paragraph: professional greeting and purpose of the update
- Progress narrative: summarize what has been accomplished and what is on track
- Concern section (if any milestones are overdue): professional description of delays and mitigation steps
- Closing: next steps and expected timeline to closing

**Tone Adjustment by Recipient Role:**
- `buyer` or `seller`: Warm, reassuring, jargon-free. Emphasize progress and next steps for them specifically.
- `lender`: Professional, data-focused. Emphasize financing milestones, appraisal status, conditions to clear.
- `attorney` or `title_company`: Concise, factual. Focus on title, survey, legal milestones.
- `inspector`: Brief. Focus on repair status and any follow-up inspections needed.

**Template Sections:**
1. Agent letterhead
2. Date and recipient block
3. Re: line with property address
4. Opening paragraph (AI-generated, tone-adjusted)
5. Transaction snapshot: status, closing date, days remaining
6. Completed milestones table with completion dates
7. Upcoming milestones table with due dates and responsible parties
8. Overdue items (if any) with risk description
9. Recent amendments (if any)
10. Next steps for the recipient specifically (AI-generated)
11. Agent contact information
12. Disclaimer footer

**Generation Options:**
- Recipient party (dropdown of all parties on the transaction)
- Include financial details: yes/no (hide purchase price from non-principals)
- Date range for "recent" amendments (default: since last status update or 30 days)

#### 3.2.4 Closing Prep Checklist

**Purpose:** A comprehensive checklist of everything that must be completed before closing day. This is the agent's operational tool for ensuring nothing falls through the cracks in the final days of a transaction.

**Source Data:**
- `Transaction` -- financing_type, representation_side, status, closing_date
- `Milestone[]` -- current status of all milestones
- `Party[]` -- contacts for title company, lender, attorney
- `InspectionAnalysis` -- whether repairs were requested and their status

**AI Content:** None. This is a structured checklist. Items are determined by business logic, not AI.

**Checklist Logic (conditional items):**

| Category | Item | Condition |
|----------|------|-----------|
| Financing | Loan application submitted | financing_type != "cash" |
| Financing | Appraisal ordered | financing_type != "cash" |
| Financing | Appraisal received and satisfactory | financing_type != "cash" |
| Financing | Loan approval / clear to close | financing_type != "cash" |
| Financing | Final loan documents to title | financing_type != "cash" |
| Financing | Proof of funds verified | financing_type == "cash" |
| Due Diligence | Home inspection completed | always |
| Due Diligence | Repair request sent (if applicable) | inspection exists |
| Due Diligence | Repair negotiations complete | repair items exist |
| Due Diligence | Re-inspection completed (if applicable) | repairs were requested |
| Title & Survey | Title search ordered | always |
| Title & Survey | Title commitment received and reviewed | always |
| Title & Survey | Survey ordered (if required) | state requires survey or buyer requests |
| Title & Survey | Title insurance binder | always |
| Legal | Attorney review complete (if applicable) | attorney party exists |
| Legal | HOA documents received and reviewed | HOA party exists or property has HOA |
| Pre-Closing | Final walkthrough scheduled | always |
| Pre-Closing | Closing disclosure reviewed (3-day rule) | financing_type != "cash" |
| Pre-Closing | Homeowner's insurance bound | always |
| Pre-Closing | Utilities transfer arranged | representation_side == "buyer" |
| Pre-Closing | Certified/cashier's check obtained or wire arranged | always |
| Closing Day | Government-issued ID for all signing parties | always |
| Closing Day | Closing documents signed | always |
| Closing Day | Funds disbursed | always |
| Closing Day | Keys/access transferred | always |
| Post-Closing | Deed recorded with county | always |
| Post-Closing | Final settlement statement retained | always |
| Post-Closing | Home warranty registered (if applicable) | warranty exists |

Each item is marked as: "Complete" (if the corresponding milestone is completed), "Pending" (milestone exists but not complete), or "Not Started" (no milestone exists). Items that are overdue are highlighted in red.

**Template Sections:**
1. Agent letterhead
2. "CLOSING PREPARATION CHECKLIST" title
3. Property address and closing date (with days remaining)
4. Key contacts: title company, lender, attorney (from parties)
5. Checklist grouped by category, with status indicators
6. Notes section (agent can add custom notes)
7. Agent signature with date

#### 3.2.5 Post-Closing Summary

**Purpose:** A complete record of the transaction for the agent's files. Useful for tax preparation, annual reviews, dispute resolution, and as a reference for future transactions with the same parties.

**Source Data:**
- `Transaction` -- all fields
- `Party[]` -- all parties with roles
- `Milestone[]` -- full timeline
- `Amendment[]` -- all changes
- `InspectionAnalysis` + `InspectionItem[]` -- findings summary
- `TransactionCommission` + `CommissionSplit[]` -- financial breakdown (Phase 5)
- `Communication[]` -- count and key communications
- `GeneratedDocument[]` -- list of documents generated during the transaction
- `File[]` -- list of uploaded files

**AI Content (Claude):**
- Executive narrative (2--3 paragraphs) summarizing the transaction journey: how it started, key milestones, any challenges overcome, and the final outcome

**Template Sections:**
1. Agent letterhead
2. "POST-CLOSING TRANSACTION SUMMARY" title
3. Executive narrative (AI-generated)
4. Property details: address, type, year built (if available)
5. Key dates timeline: contract execution, due diligence deadline, closing date, actual closing date
6. Financial summary: purchase price, earnest money, commission breakdown (gross, splits, net), closing costs (if available)
7. All parties table: name, role, company, contact
8. Milestone timeline: every milestone with status and completion date
9. Amendments: each change with old/new values and dates
10. Inspection summary: risk level, total estimated cost, repair outcomes
11. Documents generated during transaction
12. Files uploaded during transaction
13. Agent notes
14. Confidentiality notice

### 3.3 AI Content Generation Prompt Structure

Each document type that uses AI content sends a structured prompt to Claude. The prompt follows this pattern:

```
System: You are a professional real estate document writer working for a licensed
real estate agent. Generate clear, professional, and accurate content for real estate
transaction documents.

RULES:
1. Use formal but warm professional tone
2. Reference ONLY the specific data provided -- never fabricate names, dates, amounts,
   or addresses
3. For repair letters: frame requests firmly but professionally. Never use the word
   "demand." Use "request" and "we respectfully ask."
4. For status updates: be reassuring and informative. Acknowledge any delays honestly
   but emphasize the path forward.
5. For post-closing summaries: be comprehensive and appropriately celebratory.
   Acknowledge the work done by all parties.
6. Never make legal claims, legal representations, or give legal advice
7. Keep client-facing language jargon-free. Lender/attorney-facing language may use
   industry terminology.
8. Output must be valid HTML fragments (use <p>, <strong>, <em>, <ul>/<li> tags)
9. Each output section should be wrapped in a <div> with a data-section attribute
   for identification

DOCUMENT TYPE: {document_type}
TONE: {tone}
RECIPIENT ROLE: {recipient_role}

TRANSACTION DATA:
{json_data}

Generate the following sections:
{section_list}
```

The response is parsed into named sections and injected into the Jinja2 template at the appropriate positions. If the Claude API call fails or times out (30-second timeout), the template renders with placeholder text: `<p class="ai-placeholder">[AI content unavailable. Please write this section manually or click Regenerate.]</p>`.

### 3.4 Agent Preview and Edit Workflow

The preview/edit workflow is central to ensuring document quality:

1. **Generate:** Agent clicks "Generate [Document Type]" from the transaction's Documents tab.
2. **Options:** A modal presents document-specific options (e.g., which inspection items to include, tone, recipient). Agent configures and clicks "Generate Preview."
3. **Data Assembly:** Backend assembles all relevant data from the database.
4. **AI Content (if applicable):** Backend calls Claude to generate narrative sections.
5. **Render:** Backend renders the Jinja2 template with assembled data + AI content + agent branding. Returns the rendered HTML string.
6. **Preview:** Frontend displays the rendered HTML in an iframe or styled container that matches the PDF layout (A4/Letter dimensions, proper margins, page breaks).
7. **Edit:** Editable sections are identified by `data-editable="true"` attributes in the HTML. The frontend enables `contenteditable` on these sections when the agent clicks them. A minimal rich-text toolbar appears (bold, italic, bullet list). Non-editable sections (dates, amounts, addresses) are visually distinguished.
8. **Save Draft:** The edited HTML is saved to `generated_documents.rendered_html` via `PATCH`.
9. **Finalize:** Agent clicks "Finalize & Export PDF." Backend passes the final `rendered_html` to WeasyPrint, generates the PDF, uploads to MinIO, and updates `pdf_storage_url` and `status = "finalized"`.
10. **Download/Send:** Agent can download the PDF or send it via email to a party.

### 3.5 Agent Branding Configuration

Agent branding is stored in the `agent_branding` table (one row per agent) and injected into every generated document's header area. The branding includes:

- **Display name:** The name as it appears on documents (may differ from login name)
- **Brokerage name:** e.g., "Keller Williams Realty"
- **License number:** State real estate license number
- **Phone and email:** Agent contact information
- **Address:** Office address (line 1 and line 2)
- **Logo:** Uploaded image (PNG, JPG, or SVG), stored in MinIO at path `branding/{agent_id}/logo.{ext}`. Constrained to max 200px wide x 60px tall in the template.
- **Accent color:** Hex color code (e.g., `#1a365d`) used for horizontal rules, section headers, and table borders in generated documents

If no branding is configured, the template header falls back to the agent's `name` and `email` from the `users` table.

---

## 4. Data Model

### 4.1 document_templates

Stores system-defined document templates. Templates are seeded at deployment and updated through migrations, not through the agent UI.

```sql
CREATE TABLE document_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR NOT NULL,          -- internal name: "repair_request_letter_v1"
    display_name    VARCHAR NOT NULL,          -- user-facing: "Repair Request Letter"
    document_type   VARCHAR NOT NULL,          -- enum: repair_request | amendment | status_update | closing_checklist | post_closing_summary
    version         INTEGER NOT NULL DEFAULT 1,
    template_html   TEXT NOT NULL,             -- Jinja2 HTML template content
    template_css    TEXT,                      -- CSS specific to this template (inlined into <style> during rendering)
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    requires_ai     BOOLEAN NOT NULL DEFAULT FALSE,
    ai_prompt       TEXT,                      -- document-type-specific AI prompt (appended to base prompt)
    description     VARCHAR,                   -- shown in template selection UI
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one active template per document_type
CREATE UNIQUE INDEX idx_active_template_per_type
    ON document_templates (document_type) WHERE is_active = TRUE;
```

### 4.2 generated_documents

Stores every document generated for a transaction, including draft and finalized states.

```sql
CREATE TABLE generated_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id      UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    agent_id            UUID NOT NULL REFERENCES users(id),
    template_id         UUID NOT NULL REFERENCES document_templates(id),
    template_version    INTEGER NOT NULL,       -- snapshot of template version at generation time
    document_type       VARCHAR NOT NULL,        -- denormalized from template for query performance
    title               VARCHAR NOT NULL,        -- e.g., "Repair Request Letter - 123 Main St"
    status              VARCHAR NOT NULL DEFAULT 'draft',  -- draft | finalized | sent
    rendered_html       TEXT NOT NULL,            -- current HTML (after agent edits)
    original_html       TEXT NOT NULL,            -- HTML as originally generated (before edits), for diff/audit
    pdf_storage_key     VARCHAR,                 -- MinIO object key (null until finalized)
    pdf_url             VARCHAR,                 -- presigned URL (null until finalized)
    ai_generated_content JSON,                   -- raw AI response sections for audit trail
    template_data       JSON,                    -- snapshot of all data fed to the template
    generation_options  JSON,                    -- options chosen by agent (e.g., selected items, tone)
    signing_status      VARCHAR,                 -- null this phase; future: pending | signed | declined
    version             INTEGER NOT NULL DEFAULT 1, -- increments on regeneration
    notes               VARCHAR,
    sent_at             TIMESTAMPTZ,             -- when document was emailed (null if not sent)
    sent_to_party_id    UUID REFERENCES parties(id), -- who it was sent to
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_generated_docs_transaction ON generated_documents(transaction_id);
CREATE INDEX idx_generated_docs_agent ON generated_documents(agent_id);
CREATE INDEX idx_generated_docs_type ON generated_documents(document_type);
```

### 4.3 agent_branding

Stores the agent's branding configuration for document letterheads.

```sql
CREATE TABLE agent_branding (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID NOT NULL UNIQUE REFERENCES users(id),
    display_name    VARCHAR,           -- name as shown on documents
    brokerage_name  VARCHAR,
    license_number  VARCHAR,
    phone           VARCHAR,
    email           VARCHAR,
    address_line_1  VARCHAR,
    address_line_2  VARCHAR,
    logo_storage_key VARCHAR,          -- MinIO object key for logo image
    logo_url        VARCHAR,           -- presigned URL for logo image
    accent_color    VARCHAR DEFAULT '#1a365d',  -- hex color for accents
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.4 Modifications to Existing Models

```sql
-- Transaction: add relationship (ORM-only, no schema change)
-- User: add relationship (ORM-only, no schema change)
```

SQLAlchemy ORM additions:

```python
# Transaction model - add:
generated_documents = relationship("GeneratedDocument", back_populates="transaction", cascade="all, delete-orphan")

# User model - add:
branding = relationship("AgentBranding", back_populates="agent", uselist=False)
generated_documents = relationship("GeneratedDocument", back_populates="agent")
```

---

## 5. API Endpoints

### 5.1 Document Templates

| Method | Path | Description | Auth | Request Body | Response |
|--------|------|-------------|------|-------------|----------|
| GET | `/api/documents/templates` | List all active templates | Agent | -- | `[{id, display_name, document_type, description, requires_ai, version}]` |
| GET | `/api/documents/templates/{template_id}` | Get template details | Agent | -- | `{id, display_name, document_type, description, requires_ai, version, template_html (if admin)}` |

### 5.2 Document Generation

| Method | Path | Description | Auth | Request Body | Response |
|--------|------|-------------|------|-------------|----------|
| POST | `/api/transactions/{txn_id}/documents/generate` | Generate a new document | Agent | `{template_id: UUID, options: {selected_item_ids?: UUID[], recipient_party_id?: UUID, tone?: string, response_deadline?: date, include_costs?: bool, include_financials?: bool, effective_date?: date}}` | `{id, title, status: "draft", rendered_html, document_type, version}` |
| GET | `/api/transactions/{txn_id}/documents` | List generated documents for transaction | Agent | -- | `[{id, title, document_type, status, version, created_at, pdf_url, sent_at}]` |
| GET | `/api/transactions/{txn_id}/documents/{doc_id}` | Get single document with full HTML | Agent | -- | `{id, title, document_type, status, rendered_html, template_version, version, generation_options, created_at, updated_at}` |
| PATCH | `/api/transactions/{txn_id}/documents/{doc_id}` | Update document content (agent edits) | Agent | `{rendered_html: string, notes?: string}` | `{id, status, updated_at}` |
| POST | `/api/transactions/{txn_id}/documents/{doc_id}/finalize` | Convert to PDF, store in MinIO | Agent | -- | `{id, status: "finalized", pdf_url}` |
| GET | `/api/transactions/{txn_id}/documents/{doc_id}/pdf` | Download finalized PDF | Agent | -- | Binary PDF response (`Content-Type: application/pdf`) |
| POST | `/api/transactions/{txn_id}/documents/{doc_id}/send` | Email document to a party | Agent | `{recipient_party_id: UUID, subject?: string, message?: string}` | `{communication_id, sent_to, status}` |
| POST | `/api/transactions/{txn_id}/documents/{doc_id}/regenerate` | Regenerate with current data | Agent | `{options?: {...}}` | `{id (new doc), title, status: "draft", version: prev+1, rendered_html}` |
| DELETE | `/api/transactions/{txn_id}/documents/{doc_id}` | Delete a draft document | Agent | -- | `204 No Content` (only allowed for status == "draft") |

### 5.3 Agent Branding

| Method | Path | Description | Auth | Request Body | Response |
|--------|------|-------------|------|-------------|----------|
| GET | `/api/branding` | Get agent's branding config | Agent | -- | `{display_name, brokerage_name, license_number, phone, email, address_line_1, address_line_2, logo_url, accent_color}` |
| PUT | `/api/branding` | Create or update branding | Agent | `{display_name?, brokerage_name?, license_number?, phone?, email?, address_line_1?, address_line_2?, accent_color?}` | `{id, ...all fields}` |
| POST | `/api/branding/logo` | Upload logo image | Agent | Multipart form: `file` (PNG/JPG/SVG, max 2 MB) | `{logo_url}` |
| DELETE | `/api/branding/logo` | Remove logo | Agent | -- | `204 No Content` |

### 5.4 Validation Rules

- `POST generate`: returns `400` if template prerequisites are not met (e.g., repair letter requires at least one `InspectionAnalysis` for the transaction; amendment form requires at least one `Amendment` record)
- `POST finalize`: returns `409` if document is already finalized
- `DELETE`: returns `409` if document status is not `draft`
- `POST send`: returns `400` if document is not finalized
- Logo upload: returns `400` if file exceeds 2 MB or is not PNG/JPG/SVG

---

## 6. Frontend Components

### 6.1 DocumentsTab (Transaction Detail)

**Location:** `frontend/src/pages/TransactionDetail/DocumentsTab.tsx` (extend existing)
**Description:** The Documents tab on the transaction detail page gains a new "Generated Documents" section alongside the existing uploaded files section.

**Layout:**
- Section header: "Generated Documents" with a "Generate New" button
- Table/list of generated documents: columns for Type (icon + label), Title, Status (badge: draft/finalized/sent), Version, Date, Actions (View, Download PDF, Send, Delete)
- Empty state: "No documents generated yet. Click 'Generate New' to create a document from your transaction data."
- "Generate New" button opens the TemplateSelectionModal

**Props:**
```typescript
interface DocumentsTabProps {
  transactionId: string;
  documents: GeneratedDocument[];
  inspectionExists: boolean;
  amendmentsExist: boolean;
  onGenerate: (templateId: string, options: GenerationOptions) => Promise<void>;
  onRefresh: () => void;
}
```

### 6.2 TemplateSelectionModal

**Location:** `frontend/src/components/TemplateSelectionModal.tsx`
**Description:** Modal that presents available document templates as selectable cards. Templates whose prerequisites are not met are shown as disabled with an explanation.

**Layout:**
- Modal title: "Generate Document"
- Grid of template cards (2 columns):
  - Icon per document type (file-text, edit, mail, clipboard-check, archive)
  - Display name, description, "Requires AI" badge
  - Disabled state with tooltip: "Requires inspection analysis" or "Requires at least one amendment"
- Clicking an enabled card proceeds to the OptionsStep for that document type

**Props:**
```typescript
interface TemplateSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  templates: DocumentTemplate[];
  transactionContext: {
    hasInspection: boolean;
    hasAmendments: boolean;
    isClosed: boolean;
    parties: Party[];
    inspectionItems: InspectionItem[];
  };
  onSelectTemplate: (templateId: string) => void;
}
```

### 6.3 GenerationOptionsPanel

**Location:** `frontend/src/components/GenerationOptionsPanel.tsx`
**Description:** Document-type-specific options form shown after template selection and before generation begins.

**Variants by document type:**
- **Repair Request:** Checkbox list of inspection items (with severity and cost), response deadline date picker, tone selector (firm/collaborative/urgent), include costs toggle
- **Amendment:** Checkbox list of pending amendments, effective date picker
- **Status Update:** Recipient party dropdown, include financials toggle
- **Closing Checklist:** No options (generated directly from transaction state)
- **Post-Closing Summary:** No options (generated directly from full transaction data)

**Props:**
```typescript
interface GenerationOptionsPanelProps {
  documentType: string;
  transactionId: string;
  onGenerate: (options: GenerationOptions) => void;
  onCancel: () => void;
  isGenerating: boolean;
}
```

### 6.4 DocumentPreviewEditor

**Location:** `frontend/src/components/DocumentPreviewEditor.tsx`
**Description:** Full-page (or large modal) component that displays the generated HTML in a print-faithful layout and enables inline editing of designated sections.

**Layout:**
- Top toolbar: "Back to Documents", document title, status badge, "Save Draft" button, "Finalize & Export PDF" button, "Send via Email" button
- Main area: A4/Letter-sized container (794px wide, simulating print layout) displaying the rendered HTML
- Editable regions: sections with `data-editable="true"` get a light blue border on hover. Clicking activates a floating rich-text toolbar (bold, italic, underline, bullet list, numbered list)
- Side panel (collapsible): shows the data context used for generation, template version info, AI-generated vs. manual sections
- Bottom: "Regenerate with Current Data" button (creates new version), "Delete Draft" button (for drafts only)

**Props:**
```typescript
interface DocumentPreviewEditorProps {
  document: GeneratedDocument;
  onSave: (html: string) => Promise<void>;
  onFinalize: () => Promise<void>;
  onSend: (partyId: string) => Promise<void>;
  onRegenerate: () => Promise<void>;
  onDelete: () => Promise<void>;
  parties: Party[];
}
```

### 6.5 BrandingSettingsSection

**Location:** `frontend/src/pages/Settings.tsx` (add new section to existing Settings page)
**Description:** Section within the Settings page for configuring document branding.

**Layout:**
- Section header: "Document Branding"
- Left column: form fields (display name, brokerage, license number, phone, email, address line 1, address line 2, accent color picker)
- Right column: logo upload area (drag-and-drop zone with preview), live preview of how the letterhead will appear on generated documents
- The live preview updates in real-time as the agent types

**Props:**
```typescript
interface BrandingSettingsSectionProps {
  branding: AgentBranding | null;
  onSave: (branding: AgentBrandingUpdate) => Promise<void>;
  onLogoUpload: (file: File) => Promise<void>;
  onLogoRemove: () => Promise<void>;
}
```

### 6.6 TypeScript Types

```typescript
// frontend/src/types/document.ts

interface DocumentTemplate {
  id: string;
  display_name: string;
  document_type: 'repair_request' | 'amendment' | 'status_update' | 'closing_checklist' | 'post_closing_summary';
  description: string;
  requires_ai: boolean;
  version: number;
}

interface GeneratedDocument {
  id: string;
  transaction_id: string;
  template_id: string;
  template_version: number;
  document_type: string;
  title: string;
  status: 'draft' | 'finalized' | 'sent';
  rendered_html: string;
  pdf_url: string | null;
  generation_options: Record<string, unknown>;
  version: number;
  notes: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

interface GenerationOptions {
  selected_item_ids?: string[];
  recipient_party_id?: string;
  tone?: 'firm' | 'collaborative' | 'urgent';
  response_deadline?: string;
  include_costs?: boolean;
  include_financials?: boolean;
  effective_date?: string;
}

interface AgentBranding {
  id: string;
  display_name: string | null;
  brokerage_name: string | null;
  license_number: string | null;
  phone: string | null;
  email: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  logo_url: string | null;
  accent_color: string;
}
```

---

## 7. Definition of Success

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Repair request letter generates with correct inspection findings, severities, and cost estimates pulled directly from `inspection_items` | Generate from a transaction with an inspection analysis containing 8 items. Select 5 of the 8. Verify the letter contains exactly those 5 items with matching descriptions, locations, severities, and cost ranges. |
| 2 | Repair request letter AI narrative is professional, references the property address and inspection date, and does not fabricate any data | Read the AI-generated opening and closing paragraphs. Confirm every name, date, and dollar amount matches the source data. Confirm tone is professional and uses "request" language. |
| 3 | Amendment form generates with correct old and new values for each changed field | Create a price amendment ($350k to $325k) and a closing date extension (March 15 to April 1). Generate amendment form. Verify both changes appear with correct old and new values. |
| 4 | Status update letter adjusts tone based on recipient role | Generate a status update for a buyer (warm tone) and for a lender (professional/data-focused tone). Compare the AI-generated content and verify tone differences. |
| 5 | Closing checklist includes financing-specific items for a conventional loan and excludes them for a cash transaction | Generate a checklist for a conventional-financed transaction and a cash transaction. Verify the conventional checklist includes appraisal, loan approval, and closing disclosure items. Verify the cash checklist includes proof of funds but not appraisal or loan items. |
| 6 | Closing checklist marks completed milestones as checked | Complete 3 of 8 milestones on a transaction. Generate the checklist. Verify those 3 items show as "Complete" and the remaining 5 show as "Pending" or "Not Started." |
| 7 | Post-closing summary includes complete transaction data: dates, amounts, all parties, all milestones, amendments, inspection summary, and commission breakdown | Close a transaction that has full data (parties, milestones, amendments, inspection, commission). Generate the summary. Verify every section is populated with accurate data. |
| 8 | Agent can preview, edit text, and finalize a document. Edits persist in the exported PDF | Generate a repair letter. In preview, change the opening paragraph text. Finalize. Download the PDF. Open the PDF and verify the edited text appears (not the original AI text). |
| 9 | PDF export produces a correctly formatted, multi-page document with proper page breaks, fonts, and layout | Generate a post-closing summary for a complex transaction (expected 5+ pages). Download the PDF. Verify: pages break at logical points (not mid-sentence or mid-table), fonts are consistent, margins are correct, tables do not overflow. |
| 10 | Agent branding (name, brokerage, logo, accent color) appears on all generated documents | Configure branding with all fields including a logo. Generate each of the 5 document types. Verify every document's header includes the agent name, brokerage, license number, phone, email, and the logo image. Verify accent color appears on horizontal rules and section headers. |
| 11 | Documents without branding configured fall back to minimal header | Remove all branding. Generate a document. Verify the header shows the agent's name and email from the `users` table, with no missing-image or broken-layout issues. |
| 12 | Generated PDFs are stored in MinIO at the correct path and are downloadable via the API | Finalize a document. Check MinIO for an object at `generated/{agent_id}/{transaction_id}/{doc_id}.pdf`. Call the download API endpoint. Verify the response is a valid PDF with correct content. |
| 13 | Document history shows all generated documents per transaction, including multiple versions | Generate a repair letter (v1), finalize it, then regenerate (v2). Verify both versions appear in the document list with correct version numbers, dates, and statuses. |
| 14 | Sending a document via email creates a Communication record and delivers the PDF as an attachment | Finalize a repair letter. Send it to the seller's agent. Verify: a `Communication` record is created with the correct `recipient_party_id`, the email is dispatched via Resend, and the PDF is attached (not just linked). |
| 15 | Generation fails gracefully when prerequisites are not met | Attempt to generate a repair letter on a transaction with no inspection analysis. Verify the API returns a 400 error with a clear message. Verify no document record is created. Verify the frontend shows the error to the agent. |

---

## 8. Regression Test Plan

### 8.1 Phase 6 New Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P6-T01 | Generate repair request letter from inspection analysis with all items selected | Document created with status "draft". Rendered HTML contains all inspection items with correct descriptions, severities, locations, and cost estimates. AI-generated introduction and closing paragraphs present. |
| P6-T02 | Generate repair request letter with subset of inspection items | Only selected items appear in the rendered HTML. Unselected items are absent. Total cost range reflects only selected items. |
| P6-T03 | Generate repair request letter with different tones (firm, collaborative, urgent) | AI-generated narrative adjusts tone appropriately. "Firm" uses stronger language, "collaborative" uses partnership language, "urgent" emphasizes time sensitivity. |
| P6-T04 | Generate amendment form from price change amendment | Rendered HTML shows "Purchase Price" with old value and new value. Reason field populated. Effective date shown. Signature lines present. |
| P6-T05 | Generate amendment form from multiple amendments (price + closing date) | Both amendments appear in the changes table. Each shows field name, old value, and new value correctly. |
| P6-T06 | Generate status update letter for buyer client | AI content uses warm, reassuring tone. Milestones grouped by status (completed, upcoming, overdue). Upcoming milestones include due dates and responsible parties. |
| P6-T07 | Generate status update letter for lender | AI content uses professional, data-focused tone. Financing milestones prominently displayed. Industry terminology present. |
| P6-T08 | Generate closing checklist for conventional financed transaction | Checklist includes all financing items (loan application, appraisal, loan approval, closing disclosure). Completed milestones marked as "Complete." |
| P6-T09 | Generate closing checklist for cash transaction | Checklist includes "Proof of funds verified" but does NOT include appraisal, loan approval, or closing disclosure items. |
| P6-T10 | Generate post-closing summary for a fully completed transaction | All sections populated: property details, key dates, financial summary (with commission from Phase 5), all parties, full milestone timeline, amendments, inspection summary. |
| P6-T11 | Agent edits a generated document and saves | PATCH endpoint updates `rendered_html`. Subsequent GET returns the edited HTML, not the original. `original_html` remains unchanged for audit. |
| P6-T12 | Finalize a document (convert to PDF) | `status` changes to "finalized". `pdf_storage_key` and `pdf_url` are populated. MinIO contains the PDF object. Downloading the PDF returns a valid, non-empty PDF file. |
| P6-T13 | Attempt to finalize an already-finalized document | API returns 409 Conflict. Document status unchanged. No duplicate PDF created. |
| P6-T14 | Delete a draft document | Document record removed from database. If a MinIO object existed (it should not for drafts), it is cleaned up. Subsequent GET returns 404. |
| P6-T15 | Attempt to delete a finalized document | API returns 409 Conflict. Document remains in database. PDF remains in MinIO. |
| P6-T16 | Regenerate a finalized document | New `GeneratedDocument` record created with `version = original.version + 1`. Original document untouched. New document has status "draft" with fresh rendered HTML using current template and current transaction data. |
| P6-T17 | Send finalized document via email to a party | `Communication` record created with correct `transaction_id`, `recipient_party_id`, `recipient_email`, subject, and `attachments` JSON containing the PDF URL. Email dispatched via Resend. `GeneratedDocument.status` updated to "sent", `sent_at` populated. |
| P6-T18 | Generate document when AI content generation fails (Claude API timeout) | Document still generates with placeholder text in AI sections. Agent sees the placeholder and can manually write the content. No error prevents document creation. |
| P6-T19 | Generate document with full branding configured (including logo) | Rendered HTML contains the agent's display name, brokerage, license number, phone, email, and an `<img>` tag for the logo. Accent color applied to CSS variables. |
| P6-T20 | Generate document with no branding configured | Rendered HTML falls back to agent's `name` and `email` from the `users` table. No broken image tags. No missing-data errors. Clean minimal header. |
| P6-T21 | Upload agent logo (valid PNG under 2 MB) | Logo stored in MinIO at `branding/{agent_id}/logo.png`. `agent_branding.logo_url` populated with presigned URL. |
| P6-T22 | Upload agent logo (invalid: 5 MB file) | API returns 400 with message "Logo must be under 2 MB." No file stored in MinIO. |
| P6-T23 | Template versioning: generate doc, update template, generate again | First document records `template_version = 1`. After template update, second document records `template_version = 2`. Both documents render correctly with their respective template versions. |
| P6-T24 | Attempt repair letter generation on transaction without inspection analysis | API returns 400 with message "This transaction has no inspection analysis. Upload and analyze an inspection report first." No document record created. |
| P6-T25 | PDF rendering of a large document (10+ pages) | WeasyPrint completes within 60-second timeout. PDF has correct page breaks. No truncated content. File size is reasonable (under 5 MB for a 15-page document). |

### 8.2 Phase 1--5 Regression Tests

| Test ID | Phase | Description | Expected Result |
|---------|-------|-------------|-----------------|
| REG-01 | 1 | Transaction detail page loads with new Generated Documents section in Documents tab | Page loads without errors. Documents tab renders both uploaded files and generated documents sections. No console errors. |
| REG-02 | 1 | File upload to MinIO still works (shared storage) | Upload a contract PDF. Verify it stores in MinIO and is retrievable via presigned URL. Document generation's use of MinIO does not interfere. |
| REG-03 | 1 | Contract parsing via Claude API still works | Upload a contract PDF and trigger parsing. Verify all fields extracted correctly. The addition of AI document generation prompts does not affect the parsing agent. |
| REG-04 | 1 | Dashboard (Today View) loads correctly with no regressions | Dashboard loads. Transaction health scores display. No errors from new document-related relationships on the Transaction model. |
| REG-05 | 2 | Email sending (Resend integration) still works for non-document emails | Send a milestone reminder email. Verify delivery. The addition of document-attachment email sending does not break existing email flow. |
| REG-06 | 2 | Communication log records all email types correctly | Send a regular nudge email and a document-attachment email. Verify both appear in the communication log with correct types and metadata. |
| REG-07 | 3 | Party portal links still function | Access a party portal via token link. Verify transaction data visible. Generated documents are NOT visible in the party portal (agent-only feature). |
| REG-08 | 3 | Milestone CRUD operations unaffected | Create, update, complete, and waive milestones. Verify all operations succeed. Closing checklist generation reads from milestones but does not modify them. |
| REG-09 | 4 | Inspection report upload and AI analysis still works | Upload an inspection report. Verify Claude analyzes it and produces findings with severities and cost estimates. Repair letter generation reads from these findings but does not modify them. |
| REG-10 | 4 | Inspection items are not modified by repair letter generation | Generate a repair letter that includes 5 of 8 items. Verify all 8 items still exist in `inspection_items` with original data unchanged. The repair letter reads but never writes to inspection data. |
| REG-11 | 5 | Commission data appears correctly in post-closing summary | Close a transaction with full commission data (gross, broker split, team split, net). Generate post-closing summary. Verify the financial section shows all commission fields accurately. |
| REG-12 | 5 | Pipeline dashboard totals unaffected by document generation | Generate several documents for active transactions. Verify pipeline dashboard totals (active, at-risk, closed, lost) remain unchanged. Document generation has no side effects on commission calculations. |
| REG-13 | 5 | Amendment creation still triggers commission recalculation | Create a price amendment. Verify commission recalculation prompt appears. Also verify the amendment is available for amendment form generation. Both systems consume amendment data independently. |

---

## 9. Implementation Order

### Week 15: Foundation -- Data Model, Template Engine, APIs

| Day | Tasks | Files |
|-----|-------|-------|
| Monday | Create SQLAlchemy models for `DocumentTemplate`, `GeneratedDocument`, `AgentBranding`. Add relationships to `Transaction` and `User` models. Create Alembic migration. | `backend/app/models/document_template.py`, `backend/app/models/generated_document.py`, `backend/app/models/agent_branding.py`, `backend/app/models/__init__.py`, `backend/alembic/versions/xxx_phase6_document_generation.py` |
| Tuesday | Build the template engine service: Jinja2 rendering pipeline, WeasyPrint PDF conversion, MinIO storage for generated PDFs. Add `weasyprint` and `Jinja2` to `requirements.txt`. Update Dockerfile with WeasyPrint system dependencies (`libcairo2`, `libpango-1.0-0`, `libgdk-pixbuf2.0-0`, `libffi-dev`). | `backend/app/services/document_generator.py`, `backend/requirements.txt`, `backend/Dockerfile` |
| Wednesday | Create Pydantic schemas for all document-related request/response models. Build the data assembly functions for each document type (methods that query the database and structure data for template context). | `backend/app/schemas/document.py`, `backend/app/services/document_data_assembler.py` |
| Thursday | Build document generation API endpoints: generate, list, get, update, finalize, download PDF, delete. Wire up the full pipeline from API to template engine to MinIO. | `backend/app/api/documents.py`, `backend/app/api/__init__.py` (register router) |
| Friday | Build agent branding API endpoints: GET/PUT branding, POST/DELETE logo. Build branding injection into template context. Seed initial document templates (HTML + CSS for all 5 types) as a migration or seed script. | `backend/app/api/branding.py`, `backend/app/services/branding_service.py`, `backend/seed_templates.py` or migration |

### Week 16: Document Types and Frontend

| Day | Tasks | Files |
|-----|-------|-------|
| Monday | Repair request letter: complete end-to-end flow. Build the AI prompt for repair narratives. Build the finding-selection logic. Test with real inspection data. Ensure cost aggregation is correct for selected items only. | `backend/app/services/repair_letter_service.py`, `backend/templates/repair_request.html`, `backend/templates/repair_request.css` |
| Tuesday | Amendment form and status update letter. Amendment form is purely data-driven (no AI). Status update letter uses AI with tone adjustment by recipient role. Build both AI prompts and data assembly. | `backend/app/services/amendment_form_service.py`, `backend/app/services/status_update_service.py`, `backend/templates/amendment.html`, `backend/templates/status_update.html` |
| Wednesday | Closing prep checklist and post-closing summary. Checklist uses conditional logic based on financing type and representation side. Post-closing summary gathers comprehensive data and uses AI for the executive narrative. | `backend/app/services/closing_checklist_service.py`, `backend/app/services/post_closing_service.py`, `backend/templates/closing_checklist.html`, `backend/templates/post_closing_summary.html` |
| Thursday | Frontend: TypeScript types for documents. API client functions. Generated Documents section in DocumentsTab. TemplateSelectionModal with prerequisite checking. GenerationOptionsPanel with document-type-specific forms. | `frontend/src/types/document.ts`, `frontend/src/lib/api.ts` (add document endpoints), `frontend/src/pages/TransactionDetail/DocumentsTab.tsx`, `frontend/src/components/TemplateSelectionModal.tsx`, `frontend/src/components/GenerationOptionsPanel.tsx` |
| Friday | Frontend: DocumentPreviewEditor with inline editing, rich-text toolbar, finalize/download flow. Wire up the full generate-preview-edit-finalize pipeline in the UI. | `frontend/src/components/DocumentPreviewEditor.tsx`, `frontend/src/pages/TransactionDetail/DocumentsTab.tsx` (integrate editor) |

### Week 17: Polish, Integration, Testing

| Day | Tasks | Files |
|-----|-------|-------|
| Monday | Frontend: branding settings section on the Settings page. Logo upload with drag-and-drop and preview. Accent color picker. Live letterhead preview that updates as the agent types. | `frontend/src/pages/Settings.tsx` (add branding section), `frontend/src/components/BrandingSettingsSection.tsx` |
| Tuesday | Frontend: "Send via Email" integration -- recipient selection modal, subject/message fields, reuses Phase 2 email components. Regeneration flow in the preview editor. Document send endpoint integration. | `frontend/src/components/DocumentSendModal.tsx`, `backend/app/api/documents.py` (send and regenerate endpoints finalized) |
| Wednesday | Integration testing: generate all 5 document types end-to-end with realistic data. Verify PDF output quality. Test edge cases: missing data, AI failures, large documents, special characters in data. | `backend/tests/test_document_generation.py`, `backend/tests/test_repair_letter.py`, `backend/tests/test_amendment_form.py` |
| Thursday | PDF quality assurance: review page breaks on all document types, verify branding renders on every page (not just first), test print-friendly CSS, verify fonts embed correctly, test with and without logo, test accent color variations. | Template CSS refinements across all `backend/templates/*.html` and `backend/templates/*.css` files |
| Friday | Regression testing against Phases 1-5. Performance testing: measure generation time for each document type (target: under 5 seconds without AI, under 15 seconds with AI). Bug fixes. Final review and merge prep. | `backend/tests/test_regression_phase6.py` |

---

## 10. Dependencies

### What Must Be Complete from Phases 1--5

| Phase | Required Capability | Used By |
|-------|-------------------|---------|
| Phase 1 | Transaction model with all property fields, party relationships, file upload via MinIO, Claude API integration | All document types use transaction data. PDF storage uses MinIO. AI content uses Claude. |
| Phase 2 | Email sending via Resend, Communication model and logging | Send document via email to a party. Communication log records the send event. |
| Phase 3 | Milestone model with status tracking, due dates, completion dates | Status update letter, closing prep checklist, and post-closing summary all depend on milestone data. |
| Phase 4 | InspectionAnalysis and InspectionItem models with findings, severities, cost estimates | Repair request letter is built entirely from inspection analysis data. Post-closing summary includes inspection results. |
| Phase 5 | TransactionCommission, CommissionSplit models, pipeline data | Post-closing summary includes commission breakdown. |

### External Libraries and Services

| Dependency | Version | Purpose | Installation Notes |
|------------|---------|---------|-------------------|
| WeasyPrint | >= 61.0 | Converts rendered HTML to PDF. Produces high-quality, print-ready PDFs with CSS support including page breaks, headers/footers, and embedded fonts. | `pip install weasyprint`. Requires system packages in Docker: `apt-get install -y libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev libgdk-pixbuf-2.0-dev`. Must be added to `backend/Dockerfile` before the `pip install` step. |
| Jinja2 | >= 3.1 | Template rendering engine. Renders HTML from template strings with variable substitution, conditionals, loops, and filters. | Already available as a transitive dependency of FastAPI/Starlette. Explicitly add `Jinja2>=3.1` to `requirements.txt` to pin the version. |
| MinIO (existing) | -- | Object storage for generated PDFs and agent logos. | Already configured. Generated PDFs stored at key `generated/{agent_id}/{transaction_id}/{doc_id}.pdf`. Logos stored at `branding/{agent_id}/logo.{ext}`. |
| Claude API (existing) | -- | Generates narrative content for repair letters, status updates, and post-closing summaries. | Already integrated via `anthropic` SDK. Document generation prompts use the same API key and client. |
| Resend (existing) | -- | Sends generated documents as email attachments to parties. | Already integrated in Phase 2. The send endpoint attaches the PDF binary to the Resend API call. |

### Docker Configuration Changes

The `backend/Dockerfile` must be updated to install WeasyPrint's system dependencies:

```dockerfile
# Add before pip install step:
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libgdk-pixbuf-2.0-dev \
    && rm -rf /var/lib/apt/lists/*
```

The `backend/requirements.txt` must add:

```
weasyprint>=61.0
Jinja2>=3.1
```

No changes to `docker-compose.yml` are required. No new containers are added.

---

*Phase 6 Complete -> Proceed to Phase 7: Brokerage Platform*
