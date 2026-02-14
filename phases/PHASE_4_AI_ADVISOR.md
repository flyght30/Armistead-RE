# Phase 4: AI Transaction Advisor

## 1. Phase Overview

### Goal

Evolve the AI from a one-time contract parser into an ongoing transaction advisor that monitors deals daily, generates risk alerts, provides contextual suggestions, assists with document generation, and offers an interactive chat interface -- turning Armistead RE from a passive record-keeper into a proactive deal management co-pilot.

A 20-year broker does not lose deals because of ignorance. They lose deals because something slipped through the cracks during weeks 3-6 of a 45-day closing timeline -- the lender went silent, the title search stalled, the repair request never got filed. Phase 4 is the system that watches every deal the way a veteran broker watches their top-priority transaction: constantly, with pattern recognition earned from experience, catching the subtle signals that something is drifting off course.

### Timeline

Weeks 10-12 (3 weeks, following completion of Phases 1-3)

### Depends On

- **Phase 1** -- Contract parsing, transactions, parties, milestones data model, milestone templates, action items, health score
- **Phase 2** -- Resend email delivery, communication history, notification rules, email drafts, Celery beat scheduler, escalation chains
- **Phase 3** -- Party portal, portal activity tracking, inspection analyses with items, amendment tracking, file uploads

The AI advisor needs milestones, email history, portal activity, inspection data, and amendment records to perform meaningful analysis. Without these upstream data sources populated, the advisor has nothing to reason about. A risk monitor that has no milestones to evaluate or no communication history to analyze provides zero value.

### Key Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | **Transaction Risk Monitor** | Celery beat job that analyzes every active transaction daily, flags overdue milestones, silent parties, approaching deadlines, and generates severity-rated `AIInsight` records |
| 2 | **Contextual Suggestions** | Pre-computed, state-aware suggestions that appear instantly when an agent opens a transaction -- not generic advice, but recommendations rooted in the actual data for that deal |
| 3 | **Closing Readiness Check** | Deterministic database audit across 6 categories (milestones, documents, parties, overdue items, inspections, communications) with an optional AI-generated natural-language summary |
| 4 | **Smart Email Composer** | Claude-powered email generation that uses the full transaction context to draft situationally appropriate emails for repair requests, status updates, follow-ups, and more |
| 5 | **Inspection Negotiation Assistant** | Generate repair request letters from selected inspection findings, complete with cost estimates, severity justification, and professional formatting ready for submission to the seller's agent |
| 6 | **"Ask AI" Chat Interface** | Per-transaction conversational advisor with streaming responses, conversation persistence, and the ability to draft emails or letters directly from the chat |

---

## 2. Chain of Verification (CoV)

Every AI feature carries the risk of eroding trust rather than building it. A single hallucinated dollar amount in a repair request letter, a stale risk alert that the agent already resolved, or a 15-second wait time on the transaction detail page -- any of these can train an agent to ignore the system entirely. The following questions systematically identify and resolve these risks.

| # | Question | Risk Level | Resolution |
|---|----------|------------|------------|
| 1 | **What if the AI generates incorrect risk assessments?** An incorrect risk alert could cause an agent to take unnecessary action, or worse, past false positives could erode trust so the agent ignores a real risk later. | HIGH | Every AI insight is labeled with a confidence indicator and marked as "AI-generated." The UI shows a persistent disclaimer: "AI suggestions are advisory only -- verify before acting." Agents can thumbs-up/thumbs-down insights, feeding a quality loop. Critical-severity insights require a human-authored reason before they can be dismissed, creating an audit trail. The daily scan prompt is constrained to a maximum of 5 insights per transaction to prevent alert flooding. |
| 2 | **What about API cost -- running analysis on 100+ transactions daily?** At approximately 1,500 input tokens per transaction context and 500 output tokens per insight, 100 transactions per day would consume roughly 200K tokens per day. | MEDIUM | Use Claude 3.5 Haiku for the daily risk scan (high volume, structured output, cost-sensitive -- approximately $0.30/day at 100 transactions). Reserve Claude Sonnet 4 for the chat advisor and email composer where output quality directly impacts the agent's reputation. Batch transactions into groups of 5 per API call where possible. Cache transaction context snapshots in Redis with a 1-hour TTL so repeated queries within the same day do not re-serialize the entire transaction graph. Add a per-agent daily token budget (`AI_DAILY_TOKEN_BUDGET`, default 500,000 tokens) with a configurable cap in settings. |
| 3 | **How do we prevent AI hallucination in generated letters and emails?** The AI could fabricate party names, invent dollar amounts, or reference milestones that do not exist. A hallucinated repair request letter sent to the wrong party would be a serious liability. | CRITICAL | All generated content is populated from structured database fields, not from free-form AI memory. The prompt includes only verified data (party names from the `parties` table, costs from `inspection_items`, dates from `milestones`). The UI renders a preview showing which database fields populated which parts of the email. A `source_references` JSON field on each generated document maps every factual claim back to a database record ID. The agent must explicitly review and click "Send" -- there is no auto-send path for AI-generated content. Post-generation validation checks that every dollar amount, date, and name in the output matches a database record. |
| 4 | **What if the AI suggests actions inappropriate for the jurisdiction?** Real estate law varies significantly by state. A suggestion valid in Georgia (e.g., "file the repair request amendment within 10 days of the inspection period") may be procedurally wrong in California where the default inspection contingency period is 17 days. | MEDIUM | Phase 1 already captures `property_state` on every transaction. The advisor prompt includes state-specific context from a `jurisdiction_rules` configuration map (a static JSON file). Initially this ships with Georgia rules only (primary market). A `disclaimer` field on every insight reads: "This suggestion is based on general {state} real estate practices. Consult your broker or attorney for jurisdiction-specific legal advice." The jurisdiction config can be expanded per state without code changes. The AI is explicitly instructed in its system prompt to never give legal advice and to recommend attorney consultation for legal questions. |
| 5 | **What about latency -- AI calls can take 5-30 seconds?** The daily scan runs as a background Celery job, so latency is irrelevant. But the "Ask AI" chat and contextual suggestions are interactive. A 15-second wait on the transaction detail page is unacceptable. | HIGH | Contextual suggestions are pre-computed during the daily scan and cached in `ai_insights` with `trigger = 'daily_scan'`. When the agent opens a transaction, suggestions load instantly from the database -- zero AI latency. The "Ask AI" chat uses streaming responses via Server-Sent Events (SSE) so the agent sees tokens arrive in real time (target: <2 seconds to first token). The closing readiness check runs a deterministic database query first (renders the checklist immediately), then streams an optional AI summary afterward. Email composition shows a loading state ("Drafting your email...") while the AI generates content. |
| 6 | **How do we handle stale insights the agent has already addressed?** If the agent resolved a late inspection 2 hours ago but the daily scan ran at midnight, the alert is stale and annoying. Too many stale alerts train agents to ignore the system. | MEDIUM | Insights have an `auto_resolve_condition` JSONB field (e.g., `{"milestone_id": "abc", "required_status": "completed"}`). A lightweight post-action hook in the milestone and communication services checks whether any open insights match the action just taken and auto-dismisses them. The daily scan also evaluates all existing open insights and closes any whose condition is now met before generating new ones. Agents can manually dismiss with a single click (plus a required reason for critical-severity items). Snoozed insights reactivate after the snooze period. |
| 7 | **What if the AI advisor becomes a professional liability?** If an agent skips their own due diligence because "the AI said it was fine" and the deal falls through, the brokerage could face liability. A broker of record would be alarmed if their agents abdicated judgment to a machine. | HIGH | The system is designed to only flag risks and make suggestions -- it never says "everything is fine" or "you are clear to close." The closing readiness check is a factual checklist (milestone complete: yes/no, document uploaded: yes/no) not a judgment call. All AI outputs include the disclaimer: "This is an AI-generated suggestion and does not constitute legal, financial, or professional real estate advice." The agent's manual review is logged (`reviewed_at`, `reviewed_by`) creating an audit trail that the human made the final decision. Terms of service explicitly state the AI is advisory only. |
| 8 | **How do we handle AI model changes without breaking existing functionality?** If Anthropic deprecates a model version or changes output format, existing prompts may break silently. | LOW | Every AI call logs the model version used (`model_version` field on `ai_insights` and `ai_conversations`). Prompts are versioned in a `PROMPT_REGISTRY` dict keyed by `(task_type, version)`. When upgrading models, deploy new prompt versions alongside old ones and A/B test on a subset of transactions. A `prompt_version` field on each output enables debugging and rollback. Integration tests run against a mock Claude client that validates prompt/response schema contracts. |
| 9 | **What about data privacy -- are we sending PII to the Claude API?** Transaction data includes party names, emails, phone numbers, property addresses, and financial figures. | MEDIUM | Anthropic's API data policy states that API inputs are not used for model training. Document this in the privacy policy. Minimize PII in prompts: use role labels instead of full names where possible (e.g., "Buyer" instead of "John Smith") for the daily scan. For the chat advisor and email composer where names are necessary, include them but strip phone numbers and email addresses from the AI context (these are filled in from the database after generation, not by the AI). Add an `ai_audit_log` that records a hash of what was sent per API call for compliance reviews. |
| 10 | **What if the API rate limit is hit during daily analysis?** Anthropic rate limits vary by tier. A burst of 100+ concurrent requests during the daily scan could trigger 429 errors. | MEDIUM | The daily Celery job processes transactions sequentially with a configurable `AI_SCAN_BATCH_SIZE` (default: 5) and `AI_SCAN_DELAY_SECONDS` (default: 2.0) between batches. The existing `_call_claude_with_retry` function in `contract_parser.py` already implements exponential backoff for rate limits -- extract this into a shared `ai_client.py` utility and reuse across all agents. Add a circuit breaker: if 3 consecutive rate limit errors occur, pause the scan for 60 seconds. Log partial progress so the scan can resume from where it stopped on the next scheduled run. |
| 11 | **How do we measure whether the AI advice is actually useful?** Without metrics, we cannot justify the API cost or improve the system. | MEDIUM | Track: (a) insight dismiss rate -- a high dismiss rate signals low quality, (b) thumbs-up vs thumbs-down ratio per insight type, (c) time-to-action after an insight is generated, (d) closing readiness check usage frequency, (e) chat messages per transaction as a measure of engagement, (f) email composer usage vs template-based emails. Store these in the `ai_insights` table via `feedback_score` and `acted_on_at` fields. Build a `/api/stats/ai` endpoint for the dashboard. Quality target: >70% of non-dismissed insights should have a positive or neutral feedback score within the first 30 days of deployment. |
| 12 | **What about the "Ask AI" feature -- how do we prevent misuse or off-topic questions?** An agent could use the chat for personal questions or other non-real-estate tasks, wasting API tokens. | LOW | The chat system prompt hard-constrains the AI to real estate transaction advisory. Off-topic questions receive a polite redirect: "I can only help with questions related to this transaction." The system prompt includes the full transaction context so the AI naturally stays on topic. A `max_messages_per_transaction_per_day` limit (default: 50) prevents runaway usage. All conversations are logged for audit. The UI only surfaces the chat within the transaction detail view, reinforcing the scoped context. |
| 13 | **What if an agent dismisses a critical insight and something goes wrong later?** The agent might claim they never saw it, or the system might be blamed for not being persistent enough. | MEDIUM | All insight state changes are immutable audit events: created, viewed, dismissed (with reason), auto-resolved. The `ai_insights` table has `dismissed_at`, `dismissed_by`, and `dismiss_reason` fields. Critical-severity insights require a dismiss reason (cannot be blank-dismissed). A weekly digest email can summarize all dismissed critical insights for the managing broker (configurable per brokerage). |
| 14 | **How do we handle concurrent AI requests from multiple agents?** If 10 agents each open a transaction and trigger the "Ask AI" chat simultaneously, we could overwhelm the API. | LOW | Contextual suggestions are pre-computed, so no concurrent API pressure there. The "Ask AI" chat is the only truly on-demand AI call. Use a Redis-based semaphore (`MAX_CONCURRENT_AI_CALLS`, default: 5) to limit concurrent API calls. Requests beyond the limit are queued and processed FIFO. The streaming SSE response means the user sees progress even while waiting. |

---

## 3. Detailed Requirements

### 3.1 Transaction Risk Monitor

**What a 20-year broker would tell you:** "The deals I lost were never the ones with obvious problems. They were the ones where a lender went quiet for 8 days and nobody noticed, or where the title search was 'in progress' for two weeks straight and nobody asked why. I need something that watches for the silence, not just the screaming."

**Trigger:** A Celery beat scheduled task runs daily at 6:00 AM UTC (configurable via `AI_SCAN_CRON` setting). Can also be triggered on-demand per-transaction via the API.

**Process:**
1. Query all transactions with `status IN ('confirmed', 'pending_review', 'active')`.
2. For each transaction, build a context snapshot:
   - All milestones with statuses, due dates, and days since last status change
   - All parties and their roles
   - Latest 10 communications (date, recipient, subject, status)
   - Inspection analyses with unresolved items and total estimated cost ranges
   - Amendment history (last 5 amendments with fields changed)
   - Days until closing date
   - Files uploaded vs expected (based on financing type and representation side)
   - Days since last agent activity on this transaction
3. Check existing open `ai_insights` for this transaction; auto-resolve any whose `auto_resolve_condition` is now met.
4. Send the context snapshot to Claude 3.5 Haiku with a structured prompt requesting risk analysis.
5. Parse the JSON array response and create `AIInsight` records. Invalid items are logged and skipped.

**Insight Types:**

| Type | Description | Broker Insight | Example |
|------|-------------|----------------|---------|
| `risk_alert` | Something could go wrong if no action is taken | The kind of thing that wakes a broker up at 2 AM | "Financing contingency deadline is in 2 days but the lender milestone is still 'pending'. No communication with the lender in 12 days." |
| `suggestion` | Proactive recommendation the agent should consider | The advice a mentor gives after reviewing the file | "The inspection was completed 3 days ago. Consider scheduling a repair negotiation meeting with the seller's agent before the contingency deadline." |
| `prediction` | Pattern-based forecast based on current trajectory | What experience tells you when you have seen this pattern before | "Based on the current pace, the closing date of March 15 may slip. 3 of 8 milestones are still incomplete with 10 days remaining." |
| `celebration` | Something went well -- positive reinforcement | Because deals are stressful and agents need to know what is going right | "All pre-closing milestones are now complete, 4 days ahead of schedule." |

**Severity Levels:**

| Severity | Criteria | UI Treatment |
|----------|----------|--------------|
| `critical` | Deadline within 48 hours AND milestone incomplete AND no recent action | Red banner at top of insights panel, cannot be blank-dismissed, requires reason |
| `warning` | Deadline within 7 days AND potential risk identified | Yellow card, shown prominently below critical items |
| `info` | General suggestion, no time pressure | Blue card, collapsible, shown after warnings |
| `positive` | Good news, celebration, milestone completed ahead of schedule | Green card, shown briefly, auto-dismisses after 7 days |

**Auto-Resolution Rules:**

Each insight can optionally carry an `auto_resolve_condition` JSONB field. The daily scan and post-action hooks evaluate these conditions:

- `{"milestone_id": "uuid", "required_status": "completed"}` -- Resolve when the referenced milestone reaches the required status.
- `{"party_role": "lender", "required_action": "communication_sent"}` -- Resolve when a communication is sent to a party with the specified role after the insight was created.
- `{"date_passed": "2025-03-15"}` -- Resolve when the referenced date has passed (prediction became irrelevant).
- All auto-resolutions are logged with `resolved_reason = 'auto:condition_met'`.

**Agent Controls:**
- Dismiss with reason (required for critical severity, optional for others)
- Thumbs up / thumbs down feedback (single click, toggleable)
- "Remind me later" snooze with preset options: 4 hours, 1 day, 3 days
- Filter insights by type, severity, and status
- View dismissed/resolved insights in a history section
- "Refresh" button to trigger an on-demand scan for the current transaction

### 3.2 Contextual Suggestions

When an agent views a transaction, the system provides relevant advice based on the current deal state. These are pre-computed by the daily scan and cached in `ai_insights` with `trigger = 'daily_scan'`, meaning they load instantly from the database with zero AI latency.

**What a broker expects:** "When I open a deal file, I want to immediately see what needs my attention. Not a generic checklist -- tell me what is specific to THIS deal, right now, today."

**Suggestion Triggers and Examples:**

| Transaction State | Suggestion |
|-------------------|------------|
| Status changed to `confirmed` within last 24 hours | "Consider sending welcome emails to all parties introducing yourself and outlining the timeline." |
| Inspection complete, no repair request filed, contingency deadline within 5 days | "The inspection contingency deadline is in {N} days. Consider whether to request repairs, request a price reduction, or waive the contingency." |
| Financing milestone `pending` + no lender communication in 7+ days | "The lender has not provided an update in {N} days. Consider following up to confirm the loan is on track for closing." |
| All milestones `completed` | "All milestones are complete. This transaction appears ready for closing. Run a Closing Readiness Check to confirm." |
| Appraisal milestone overdue by 3+ days | "The appraisal was due {N} days ago and is still pending. This could delay closing. Contact the appraiser or lender for a status update." |
| Amendment filed within last 48 hours + affected parties not notified | "An amendment to {field} was filed {N} days ago. {count} affected parties have not been notified." |
| Closing date within 7 days + title milestone incomplete | "Closing is in {N} days but the title search is not complete. Title clearance is typically a prerequisite for closing." |
| Earnest money deadline approaching + no deposit confirmation | "The earnest money deposit deadline is in {N} days. Confirm the deposit has been received by the escrow holder." |
| Buyer-side transaction + no home warranty discussion | "Consider discussing home warranty options with the buyer. This is commonly addressed before closing." |
| Seller disclosure not uploaded + more than 5 days since binding agreement | "The seller's disclosure has not been uploaded. In most states, the seller must provide this within a specific timeframe." |

**Rendering:**
- Suggestions appear in a collapsible "AI Advisor" panel on the transaction detail page
- Ordered by severity (critical first, positive last)
- Each card shows: severity-colored icon, title, description, suggested action button (navigates to relevant section), dismiss button
- Clicking "Send Follow-Up Email" opens the Smart Email Composer pre-configured for a lender follow-up

### 3.3 Closing Readiness Check

An on-demand audit that runs a deterministic checklist against the database (no AI call for the checklist itself) with an optional AI-generated summary streamed via SSE.

**What a broker expects:** "Two days before closing, I want a single place that tells me: are we ready? Not 'probably' -- I want a line-item checklist. Is the title clear? Is the loan funded? Is the survey done? Green check or red X, no ambiguity."

**Checklist Categories:**

**1. Milestones Audit**
- Query all milestones for the transaction
- For each milestone: title, status, due_date, completed_at
- PASS: milestone `status = 'completed'`
- WARN: milestone not completed but `due_date > now() + 3 days`
- FAIL: milestone `status != 'completed'` and `due_date < now()` (overdue)
- Result: list of `{milestone_title, status, due_date, pass/warn/fail, reason}`

**2. Documents Audit**
- Define required documents per `financing_type` and `representation_side`:
  - All transactions: purchase contract, inspection report
  - Financed (conventional/FHA/VA): pre-approval letter, loan commitment, appraisal report
  - Cash: proof of funds
  - Buyer-side: buyer agency agreement
  - Seller-side: listing agreement, seller disclosure
- Cross-reference `files` table for uploaded documents matching expected types
- Result: list of `{document_type, uploaded: bool, file_id?, pass/fail}`

**3. Parties Audit**
- Define required roles per `representation_side`:
  - Buyer-side: buyer, buyer_agent, seller_agent, lender (if financed), title_company, closing_attorney
  - Seller-side: seller, seller_agent, buyer_agent, title_company, closing_attorney
- Cross-reference `parties` table
- Result: list of `{role, present: bool, party_name?, pass/fail}`

**4. Overdue Items Audit**
- Query all milestones where `due_date < now()` and `status != 'completed'`
- Result: list of `{item, days_overdue, responsible_party_role}`

**5. Inspection Items Audit**
- Query all `inspection_items` where `repair_status NOT IN ('completed', 'waived', 'not_requested')`
- Flag items with severity `high` or `critical` that remain unresolved
- Result: list of `{description, location, severity, repair_status, estimated_cost_low, estimated_cost_high}`

**6. Communication Coverage Audit**
- Check that all parties have been contacted at least once since the transaction was confirmed
- Check that no key party (buyer, seller, lender) has gone without a communication in 14+ days
- Result: list of `{party_name, party_role, last_contact_date, days_since_contact, pass/warn/fail}`

**Overall Readiness Score:**

```
score = (pass_count / total_check_count) * 100
```

Status mapping:
- `ready`: All checks pass, score = 100
- `ready_with_warnings`: No failures, but some warnings exist (score >= 80)
- `not_ready`: One or more failures (score < 80)
- `critical`: Overdue items exist AND closing is within 7 days

**Optional AI Summary:**
After the checklist renders, the structured results are sent to Claude 3.5 Haiku for a natural-language summary. This summary streams via SSE, arriving after the deterministic checklist is already visible. Example: "This transaction is mostly ready for closing. Two items need attention: the lender has not provided the final loan commitment, and one inspection repair (electrical panel) is still pending seller response. Everything else is on track."

### 3.4 Smart Email Composer

Unlike Phase 2's template-based emails (static templates with variable substitution), the smart email composer generates situationally-aware emails using the full transaction context.

**What a broker expects:** "I write the same 15 email types over and over, but each one is slightly different because every deal has different parties, different issues, different timelines. I need something that understands THIS deal and writes the email I would write if I had 20 minutes to craft it perfectly."

**How It Works:**
1. Agent selects an email intent (e.g., "Repair Request", "Status Update", "Follow Up")
2. System builds a context payload from the database:
   - Transaction details (address, price, dates, status)
   - All parties (names, roles, emails)
   - Relevant milestones and their statuses
   - Inspection items (for repair-related emails)
   - Recent communications to the same recipient (to avoid repeating information)
   - Amendment history (for change-related emails)
3. Claude Sonnet 4 generates the email body with the agent's configured tone and signature
4. Agent reviews in a rich preview with:
   - Highlighted database-sourced fields (party names, dates, amounts) shown in a distinct color
   - Source references for every factual claim (hoverable tooltips showing which record sourced the data)
   - Full edit capability before sending
5. Agent clicks "Send" (or edits and sends)

**Supported Email Intents:**

| Intent | Context Used | Default Recipient | Broker Note |
|--------|-------------|-------------------|-------------|
| `repair_request` | Selected inspection items, estimated costs, property details | Seller's agent | "The repair request is the most important letter in a buyer's agent toolkit. It has to be specific, reasonable, and backed by the inspection report." |
| `status_update` | All milestones, recent completions, upcoming deadlines | All parties or selected | "Every party on a deal wants to know: are we on track? A good status update keeps everyone calm." |
| `lender_followup` | Financing milestone status, days since last contact, contingency deadline | Lender | "Lenders go quiet. It is never a good sign. Following up early and often is how you prevent closing delays." |
| `closing_congratulations` | Final closing details, all party names | All parties | "Closing day is a celebration. The email should feel personal, not templated." |
| `amendment_notification` | Amendment details, old value, new value, reason | Affected parties | "When something changes, every affected party needs to know immediately and clearly." |
| `deadline_reminder` | Upcoming milestone, due date, responsible party | Responsible party | "Direct but not aggressive. Give them the deadline and make it easy to respond." |
| `welcome_introduction` | Agent info, transaction timeline, key milestones | All parties | "The first email sets the tone for the entire transaction. It should inspire confidence." |
| `custom` | Full transaction context + agent's free-text description | Agent-selected | "Sometimes you just need to write something specific. Give me the context and let me steer." |

**Agent Tone Settings:**
- Stored in `user.settings.email_tone` (e.g., "professional", "warm", "concise")
- Agent's `email_signature` is appended automatically (not generated by AI)
- The AI adapts vocabulary and formality based on the tone setting

### 3.5 Inspection Negotiation Assistant (Repair Letter Generator)

**What a broker expects:** "The repair request letter can make or break a deal. Too aggressive and the seller walks. Too soft and your buyer pays for problems the seller should fix. I need a letter that is firm, specific, backed by the inspector's findings, and gives the seller a clear path to respond."

**How It Works:**
1. Agent navigates to the Inspections tab on the transaction detail page
2. Agent selects specific inspection items they want to include in the repair request
3. Agent can add a cover note or special instructions (e.g., "emphasize safety concerns", "request credit in lieu of repairs for items 2 and 4")
4. System assembles a context payload:
   - Selected inspection items with: description, location, severity, estimated cost range, risk assessment, inspector recommendation
   - Property details (address, age if available, purchase price)
   - Buyer and seller party details (names, agent names)
   - Transaction timeline (closing date, inspection contingency deadline)
5. Claude Sonnet 4 generates a formal repair request letter
6. Agent reviews in a formatted preview with:
   - Each inspection item clearly referenced with its database-sourced details
   - Cost estimates presented as ranges (not fabricated point estimates)
   - A professional structure: introduction, itemized findings, requested remediation, timeline for response, closing
7. Agent can edit any part of the letter before sending or downloading as PDF

**Letter Structure:**
```
Date: {generated_date}
To: {seller_agent_name}, {seller_agent_company}
Re: Repair Request -- {property_address}
    Purchase Contract dated {contract_date}
    Buyer: {buyer_name}

Dear {seller_agent_name},

[Introduction: Following the home inspection completed on {inspection_date},
the Buyer requests the following repairs/remediation be completed prior to closing.]

ITEM 1: {description}
Location: {location}
Inspector Finding: {risk_assessment}
Estimated Cost: ${low} - ${high}
Requested Action: {recommendation or agent override}

[... additional items ...]

TOTAL ESTIMATED COST RANGE: ${total_low} - ${total_high}

[Closing: timeline for response, reference to contract contingency,
professional closing]

Respectfully,
{agent_name}
{agent_company}
{agent_license_number}
```

**Important Constraints:**
- Dollar amounts come exclusively from `inspection_items.estimated_cost_low` and `estimated_cost_high` -- the AI never invents numbers
- Severity ratings come from the inspector's assessment, not from the AI's judgment
- The letter clearly attributes findings to the home inspection report, not to the AI
- The agent's license number and brokerage info are appended from the `users` table

### 3.6 "Ask AI" Chat

A per-transaction conversational interface where agents can ask questions, request explanations, and generate document drafts in an interactive dialogue.

**Architecture:**
- Each transaction has its own conversation thread stored in `ai_conversations`
- The system prompt is rebuilt on every request with fresh transaction context
- Conversation history (up to 20 most recent non-archived messages) is included in each request
- Responses stream via SSE for real-time display

**System Prompt Construction:**
```
You are a real estate transaction advisor for Armistead RE. You are helping
{agent_name} manage a {representation_side}-side {financing_type} transaction
for the property at {property_address}, {property_city}, {property_state}
{property_zip}.

Purchase price: {purchase_price}
Closing date: {closing_date} ({days_until_closing} days from now)
Current status: {status}

PARTIES:
{for each party: role, name}

MILESTONES:
{for each milestone: title, status, due_date, completed_at}

RECENT COMMUNICATIONS (last 10):
{for each: date, recipient_role, subject, status}

INSPECTION SUMMARY:
{if exists: overall_risk_level, item count, unresolved count,
 total estimated cost range}

OPEN AI INSIGHTS:
{for each active insight: type, severity, title}

RULES:
- You may ONLY answer questions related to this transaction and general
  real estate practices.
- Do not provide legal advice. Recommend consulting an attorney for legal
  questions.
- Do not fabricate information not present in the transaction data above.
- If asked about data you do not have, say so clearly.
- If asked to draft an email, format it as a complete email with subject line.
- If asked an off-topic question, respond: "I can only help with questions
  related to this transaction. Is there something about this deal I can
  assist with?"
```

**Example Interactions:**

1. "What should I focus on for this deal?" -- AI reviews milestones, identifies the most urgent incomplete items, and prioritizes them based on closing timeline.

2. "Draft a follow-up email to the lender about the appraisal" -- AI pulls the lender's name, the appraisal milestone status, last communication date, and generates a complete email.

3. "What are the risks of extending the closing date?" -- AI considers rate lock expiration, contract contingency deadlines, seller's timeline, and financing status.

4. "Summarize where we are" -- AI provides a status overview with milestone completion percentage, upcoming deadlines, and any active risk alerts.

5. "Help me write a repair request for the HVAC and plumbing issues" -- AI pulls the specific inspection items, generates a repair request, and offers to open it in the Repair Letter Generator for formal formatting.

**Conversation Limits:**
- Maximum 50 messages per transaction per day (configurable via `AI_CHAT_MAX_MESSAGES_PER_DAY`)
- Maximum 20 messages included as history in each API request
- Messages older than 30 days are marked as archived but still viewable in the UI
- Total conversation storage: 500 messages per transaction before oldest are permanently archived

**Message Type Routing:**
- `chat`: Standard conversational response
- `email_draft`: Response is formatted as a complete email (subject + body) that can be sent directly to the email composer
- `readiness_summary`: Response is formatted as a closing readiness narrative

---

## 4. Data Model

### 4.1 `ai_insights` Table

```sql
CREATE TABLE ai_insights (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id          UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    type                    VARCHAR NOT NULL,
        -- 'risk_alert', 'suggestion', 'prediction', 'celebration'
    severity                VARCHAR NOT NULL,
        -- 'critical', 'warning', 'info', 'positive'
    title                   VARCHAR NOT NULL,
    description             TEXT NOT NULL,
    suggested_action        VARCHAR,
        -- optional CTA label, e.g. "Send Follow-Up Email"
    suggested_action_url    VARCHAR,
        -- optional deep link within the app, e.g. "/transactions/{id}/communications"

    -- Resolution tracking
    status                  VARCHAR NOT NULL DEFAULT 'active',
        -- 'active', 'dismissed', 'resolved', 'snoozed'
    auto_resolve_condition  JSONB,
        -- e.g. {"milestone_id": "uuid", "required_status": "completed"}
    dismissed_at            TIMESTAMP WITH TIME ZONE,
    dismissed_by            UUID REFERENCES users(id),
    dismiss_reason          VARCHAR,
    resolved_at             TIMESTAMP WITH TIME ZONE,
    resolved_reason         VARCHAR,
        -- 'auto:condition_met', 'auto:expired', 'manual'
    snoozed_until           TIMESTAMP WITH TIME ZONE,

    -- Feedback and quality tracking
    feedback_score          INTEGER,
        -- -1 (thumbs down), 0 (neutral), 1 (thumbs up)
    acted_on_at             TIMESTAMP WITH TIME ZONE,

    -- AI metadata
    model_version           VARCHAR NOT NULL,
        -- e.g. 'claude-3-5-haiku-20241022'
    prompt_version          VARCHAR NOT NULL,
        -- e.g. 'risk_scan_v1'
    trigger                 VARCHAR NOT NULL DEFAULT 'daily_scan',
        -- 'daily_scan', 'on_demand', 'event_hook'
    source_references       JSONB,
        -- [{"type": "milestone", "id": "uuid"}, {"type": "inspection_item", "id": "uuid"}]
    tokens_used             INTEGER,

    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_insights_transaction_status ON ai_insights(transaction_id, status);
CREATE INDEX idx_ai_insights_type_severity ON ai_insights(type, severity);
CREATE INDEX idx_ai_insights_snoozed ON ai_insights(snoozed_until)
    WHERE status = 'snoozed';
CREATE INDEX idx_ai_insights_active ON ai_insights(transaction_id)
    WHERE status = 'active';
```

**SQLAlchemy Model (`backend/app/models/ai_insight.py`):**

```python
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class AIInsight(BaseModel):
    __tablename__ = "ai_insights"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    suggested_action = Column(String, nullable=True)
    suggested_action_url = Column(String, nullable=True)

    status = Column(String, nullable=False, default="active")
    auto_resolve_condition = Column(JSON, nullable=True)
    dismissed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    dismissed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    dismiss_reason = Column(String, nullable=True)
    resolved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    resolved_reason = Column(String, nullable=True)
    snoozed_until = Column(TIMESTAMP(timezone=True), nullable=True)

    feedback_score = Column(Integer, nullable=True)
    acted_on_at = Column(TIMESTAMP(timezone=True), nullable=True)

    model_version = Column(String, nullable=False)
    prompt_version = Column(String, nullable=False)
    trigger = Column(String, nullable=False, default="daily_scan")
    source_references = Column(JSON, nullable=True)
    tokens_used = Column(Integer, nullable=True)

    transaction = relationship("Transaction", back_populates="ai_insights")
    dismissed_by_user = relationship("User", foreign_keys=[dismissed_by])
```

### 4.2 `ai_conversations` Table

```sql
CREATE TABLE ai_conversations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id      UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    agent_id            UUID NOT NULL REFERENCES users(id),
    role                VARCHAR NOT NULL,
        -- 'user' or 'assistant'
    content             TEXT NOT NULL,
    message_type        VARCHAR NOT NULL DEFAULT 'chat',
        -- 'chat', 'email_draft', 'readiness_summary', 'repair_letter'

    -- AI metadata (only populated for assistant messages)
    model_version       VARCHAR,
    prompt_version      VARCHAR,
    tokens_used         INTEGER,
    source_references   JSONB,

    -- Archival
    is_archived         BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX idx_ai_conversations_transaction ON ai_conversations(transaction_id, created_at DESC);
CREATE INDEX idx_ai_conversations_agent ON ai_conversations(agent_id);
CREATE INDEX idx_ai_conversations_active ON ai_conversations(transaction_id)
    WHERE is_archived = FALSE;
```

**SQLAlchemy Model (`backend/app/models/ai_conversation.py`):**

```python
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from .base_model import BaseModel


class AIConversation(BaseModel):
    __tablename__ = "ai_conversations"

    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False, default="chat")

    model_version = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    source_references = Column(JSON, nullable=True)

    is_archived = Column(Boolean, nullable=False, default=False)

    transaction = relationship("Transaction", back_populates="ai_conversations")
    agent = relationship("User", back_populates="ai_conversations")
```

### 4.3 Relationship Updates

**Transaction model** -- add to `backend/app/models/transaction.py`:
```python
ai_insights = relationship("AIInsight", back_populates="transaction", cascade="all, delete-orphan")
ai_conversations = relationship("AIConversation", back_populates="transaction", cascade="all, delete-orphan")
```

**User model** -- add to `backend/app/models/user.py`:
```python
ai_conversations = relationship("AIConversation", back_populates="agent")
```

**Models `__init__.py`** -- add imports:
```python
from .ai_insight import AIInsight
from .ai_conversation import AIConversation
```

---

## 5. API Endpoints

### 5.1 AI Insights

```
GET    /api/transactions/{id}/insights
       Query params:
           status: 'active' | 'dismissed' | 'resolved' | 'snoozed' (default: 'active')
           type: 'risk_alert' | 'suggestion' | 'prediction' | 'celebration'
           severity: 'critical' | 'warning' | 'info' | 'positive'
           limit: int (default: 50)
           offset: int (default: 0)
       Response 200:
           { items: AIInsightResponse[], pagination: { limit, offset, total } }
```

```
GET    /api/transactions/{id}/insights/{insight_id}
       Response 200: AIInsightResponse
```

```
PATCH  /api/transactions/{id}/insights/{insight_id}/dismiss
       Body: { reason: string }
       Validation: reason is REQUIRED if insight severity == 'critical'
       Response 200: AIInsightResponse (updated with status='dismissed')
```

```
PATCH  /api/transactions/{id}/insights/{insight_id}/snooze
       Body: { until: datetime }
       Response 200: AIInsightResponse (updated with status='snoozed')
```

```
PATCH  /api/transactions/{id}/insights/{insight_id}/feedback
       Body: { score: -1 | 0 | 1 }
       Response 200: AIInsightResponse (updated with feedback_score)
```

```
POST   /api/transactions/{id}/insights/refresh
       Description: Triggers an on-demand insight scan for this single transaction
       Response 200: { items: AIInsightResponse[], tokens_used: int }
```

```
GET    /api/insights/summary
       Description: Aggregated insight counts across all transactions for the
                    authenticated agent
       Response 200: {
           critical: int,
           warning: int,
           info: int,
           positive: int,
           total_active: int
       }
```

### 5.2 Closing Readiness

```
POST   /api/transactions/{id}/closing-readiness
       Description: Run the deterministic closing readiness check
       Response 200: {
           overall_status: 'ready' | 'ready_with_warnings' | 'not_ready' | 'critical',
           score: float,
           categories: [
               {
                   name: string,
                   status: 'pass' | 'warn' | 'fail',
                   items: [
                       { label: string, status: 'pass' | 'warn' | 'fail', detail: string }
                   ]
               }
           ],
           ai_summary: null
       }
```

```
GET    /api/transactions/{id}/closing-readiness/stream
       Description: SSE stream for the AI summary portion of the readiness check.
                    Connect after the POST returns the structured checklist.
       Response: text/event-stream
       Events:
           event: token    data: { content: string }
           event: done     data: { summary: string, tokens_used: int }
           event: error    data: { code: string, message: string }
```

### 5.3 Smart Email Composer

```
POST   /api/transactions/{id}/compose-email
       Body: {
           intent: string,
               -- 'repair_request' | 'status_update' | 'lender_followup' |
               -- 'closing_congratulations' | 'amendment_notification' |
               -- 'deadline_reminder' | 'welcome_introduction' | 'custom'
           recipient_party_ids: UUID[],
           selected_inspection_item_ids: UUID[],
               -- only for 'repair_request' intent
           custom_instructions: string | null,
               -- for 'custom' intent or additional guidance
           tone_override: string | null
               -- overrides agent's default tone for this email
       }
       Response 200: {
           subject: string,
           body: string,
           recipients: [
               { party_id: UUID, name: string, email: string, role: string }
           ],
           source_references: [
               { field: string, source_type: string, source_id: UUID }
           ],
           model_version: string,
           tokens_used: int
       }
```

```
POST   /api/transactions/{id}/compose-email/send
       Description: Send a composed (and potentially edited) email
       Body: {
           subject: string,
           body: string,
           recipient_party_ids: UUID[],
           original_draft_references: JSON
               -- for audit trail, links to source records
       }
       Response 201: { communication_ids: UUID[] }
```

### 5.4 Repair Letter Generator

```
POST   /api/transactions/{id}/generate-letter
       Body: {
           type: 'repair_request',
               -- extensible for future letter types
           inspection_item_ids: UUID[],
               -- which inspection items to include
           cover_note: string | null,
               -- agent's additional instructions
           format: 'html' | 'pdf'
               -- output format (PDF uses the HTML + wkhtmltopdf or similar)
       }
       Response 200: {
           letter_html: string,
           letter_text: string,
           total_estimated_cost_low: float,
           total_estimated_cost_high: float,
           item_count: int,
           source_references: [
               { item_id: UUID, description: string, cost_low: float, cost_high: float }
           ],
           model_version: string,
           tokens_used: int
       }
```

```
POST   /api/transactions/{id}/generate-letter/send
       Description: Send the generated letter as an email to the seller's agent
       Body: {
           letter_html: string,
               -- agent may have edited
           recipient_party_id: UUID,
           subject: string
       }
       Response 201: { communication_id: UUID }
```

### 5.5 Ask AI Chat

```
GET    /api/transactions/{id}/chat
       Query params:
           limit: int (default: 50)
           before: datetime (cursor-based pagination, returns messages before this timestamp)
       Response 200: {
           messages: AIConversationResponse[],
           has_more: bool
       }
```

```
POST   /api/transactions/{id}/chat
       Body: {
           message: string,
           message_type: 'chat' | 'email_draft' | 'repair_letter'
       }
       Response: text/event-stream (SSE)
       Events:
           event: token    data: { content: string }
           event: done     data: {
               message_id: UUID,
               tokens_used: int,
               source_references: JSON
           }
           event: error    data: { code: string, message: string }
```

```
DELETE /api/transactions/{id}/chat
       Description: Archive all messages for this transaction (soft delete,
                    sets is_archived = true)
       Response 200: { archived_count: int }
```

### 5.6 AI Stats

```
GET    /api/stats/ai
       Description: AI usage and quality metrics for the authenticated agent
       Response 200: {
           total_insights_generated: int,
           insights_by_type: {
               risk_alert: int,
               suggestion: int,
               prediction: int,
               celebration: int
           },
           feedback_summary: {
               positive: int,
               negative: int,
               neutral: int,
               no_feedback: int
           },
           dismiss_rate: float,
           avg_tokens_per_day: int,
           total_chat_messages: int,
           total_emails_composed: int,
           total_letters_generated: int,
           top_insight_types: [{ type: string, count: int }]
       }
```

### 5.7 Pydantic Schemas

**`backend/app/schemas/ai_insight.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime


class AIInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    type: str
    severity: str
    title: str
    description: str
    suggested_action: Optional[str] = None
    suggested_action_url: Optional[str] = None
    status: str
    auto_resolve_condition: Optional[Dict[str, Any]] = None
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[UUID] = None
    dismiss_reason: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_reason: Optional[str] = None
    snoozed_until: Optional[datetime] = None
    feedback_score: Optional[int] = None
    acted_on_at: Optional[datetime] = None
    model_version: str
    prompt_version: str
    trigger: str
    source_references: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class AIInsightDismiss(BaseModel):
    reason: Optional[str] = None


class AIInsightSnooze(BaseModel):
    until: datetime


class AIInsightFeedback(BaseModel):
    score: int  # -1, 0, or 1


class AIInsightList(BaseModel):
    items: List[AIInsightResponse]
    pagination: Dict[str, Any]


class AIInsightSummary(BaseModel):
    critical: int
    warning: int
    info: int
    positive: int
    total_active: int
```

**`backend/app/schemas/ai_conversation.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime


class AIConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transaction_id: UUID
    agent_id: UUID
    role: str
    content: str
    message_type: str
    model_version: Optional[str] = None
    prompt_version: Optional[str] = None
    tokens_used: Optional[int] = None
    source_references: Optional[Dict[str, Any]] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ChatMessageCreate(BaseModel):
    message: str
    message_type: str = "chat"


class ChatHistory(BaseModel):
    messages: List[AIConversationResponse]
    has_more: bool
```

**`backend/app/schemas/closing_readiness.py`**

```python
from pydantic import BaseModel
from typing import List, Optional


class ReadinessItem(BaseModel):
    label: str
    status: str  # 'pass', 'warn', 'fail'
    detail: str


class ReadinessCategory(BaseModel):
    name: str
    status: str  # 'pass', 'warn', 'fail'
    items: List[ReadinessItem]


class ClosingReadinessResponse(BaseModel):
    overall_status: str
    score: float
    categories: List[ReadinessCategory]
    ai_summary: Optional[str] = None
```

**`backend/app/schemas/email_compose.py`**

```python
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from uuid import UUID


class ComposeEmailRequest(BaseModel):
    intent: str
    recipient_party_ids: List[UUID]
    selected_inspection_item_ids: List[UUID] = []
    custom_instructions: Optional[str] = None
    tone_override: Optional[str] = None


class SourceReference(BaseModel):
    field: str
    source_type: str
    source_id: UUID


class RecipientInfo(BaseModel):
    party_id: UUID
    name: str
    email: str
    role: str


class ComposeEmailResponse(BaseModel):
    subject: str
    body: str
    recipients: List[RecipientInfo]
    source_references: List[SourceReference]
    model_version: str
    tokens_used: int


class SendComposedEmailRequest(BaseModel):
    subject: str
    body: str
    recipient_party_ids: List[UUID]
    original_draft_references: Optional[Dict[str, Any]] = None


class SendComposedEmailResponse(BaseModel):
    communication_ids: List[UUID]
```

**`backend/app/schemas/repair_letter.py`**

```python
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class GenerateLetterRequest(BaseModel):
    type: str = "repair_request"
    inspection_item_ids: List[UUID]
    cover_note: Optional[str] = None
    format: str = "html"


class LetterSourceReference(BaseModel):
    item_id: UUID
    description: str
    cost_low: float
    cost_high: float


class GenerateLetterResponse(BaseModel):
    letter_html: str
    letter_text: str
    total_estimated_cost_low: float
    total_estimated_cost_high: float
    item_count: int
    source_references: List[LetterSourceReference]
    model_version: str
    tokens_used: int


class SendLetterRequest(BaseModel):
    letter_html: str
    recipient_party_id: UUID
    subject: str


class SendLetterResponse(BaseModel):
    communication_id: UUID
```

---

## 6. Frontend Components

### 6.1 AIInsightsPanel

**Location:** `frontend/src/components/AIInsightsPanel.tsx`
**Description:** Collapsible panel rendered on the transaction detail page showing active AI insights sorted by severity.

**Sub-components:**

| Component | Description | Key Props |
|-----------|-------------|-----------|
| `InsightCard` | Individual insight with severity-colored left border, type icon, title, description, and action buttons | `insight: AIInsight`, `onDismiss`, `onSnooze`, `onFeedback` |
| `InsightActions` | Button group: Dismiss (with modal for critical), Snooze dropdown (4h / 1d / 3d), Thumbs up/down | `insightId: string`, `severity: string` |
| `InsightHistory` | Collapsible accordion showing resolved and dismissed insights with timestamps and reasons | `transactionId: string` |
| `InsightBadge` | Small count badge (critical count in red, warning count in yellow) for use on transaction cards in the dashboard | `criticalCount: number`, `warningCount: number` |

**Layout:**
- Panel sits at the top of the transaction detail Overview tab
- Critical insights: red left border, red background tint, cannot be collapsed
- Warning insights: yellow left border
- Info insights: blue left border, collapsible
- Positive insights: green left border, auto-fade after 7 days
- Each card has a suggested action button that navigates to the relevant section (e.g., "Send Follow-Up" goes to the communications tab with the email composer pre-configured)
- Polls `GET /api/transactions/{id}/insights?status=active` every 60 seconds
- Dismiss for critical severity opens a confirmation modal with a required text input for reason

### 6.2 ClosingReadinessDialog

**Location:** `frontend/src/components/ClosingReadinessDialog.tsx`
**Description:** Modal dialog triggered by a "Run Closing Readiness Check" button on the transaction detail page.

**Sub-components:**

| Component | Description | Key Props |
|-----------|-------------|-----------|
| `ReadinessScoreCircle` | Circular progress indicator (0-100) with color coding: green (90-100), yellow (70-89), red (<70) | `score: number`, `status: string` |
| `ReadinessCategoryCard` | Expandable card per category (Milestones, Documents, Parties, Overdue, Inspections, Communications) | `category: ReadinessCategory` |
| `ReadinessItem` | Individual pass/warn/fail line item with status icon and detail text | `item: ReadinessItem` |
| `ReadinessAISummary` | Streaming text area that renders the AI summary tokens as they arrive via SSE | `transactionId: string` |

**Layout:**
- Modal opens with a loading spinner while POST request runs
- Checklist renders immediately from the structured JSON response
- AI summary section at the bottom shows "Generating summary..." with a typing indicator, then streams in text via SSE
- Each category card is expandable/collapsible, with the category-level status icon (green check, yellow warning, red X)
- Print-friendly CSS for agents who want a physical checklist
- "Run Again" button to re-execute the check

### 6.3 SmartEmailComposerDialog

**Location:** `frontend/src/components/SmartEmailComposerDialog.tsx`
**Description:** Multi-step modal dialog for generating and sending AI-composed emails.

**Steps:**

1. **Intent Selection** -- Grid of clickable intent cards, each with an icon and short description. Cards: Repair Request, Status Update, Lender Follow-Up, Closing Congratulations, Amendment Notice, Deadline Reminder, Welcome Introduction, Custom.

2. **Configuration** -- Select recipients from a checkbox list of transaction parties. For `repair_request` intent, shows an additional section: checkbox list of inspection items with severity badges and cost ranges. Optional custom instructions text area.

3. **Preview** -- Full email preview with:
   - Subject line (editable inline)
   - Body content (editable with rich text toolbar)
   - Database-sourced fields highlighted in blue with hover tooltips showing the source record
   - Recipient list with email addresses
   - "Regenerate" button to request a new draft

4. **Send** -- Confirmation step with final recipient list, subject, and a "Send" button.

**Sub-components:**

| Component | Description |
|-----------|-------------|
| `IntentSelector` | Grid of intent option cards with icons |
| `RecipientSelector` | Checkbox list of transaction parties with roles |
| `InspectionItemSelector` | Checkbox list of inspection items with severity and cost (shown for repair_request intent only) |
| `EmailPreview` | Rich text preview with source-reference highlighting |
| `EmailEditor` | Editable version of the preview for modifications |
| `SourceReferenceTooltip` | Hover tooltip showing which database record sourced a highlighted field |

### 6.4 RepairLetterDialog

**Location:** `frontend/src/components/RepairLetterDialog.tsx`
**Description:** Dedicated dialog for generating formal repair request letters from inspection findings.

**Layout:**
- Left panel: Inspection items list with checkboxes, severity badges, cost ranges, and location tags
- Right panel: Live preview of the generated letter
- Bottom bar: Cover note text area, "Generate Letter" button, "Download PDF" button, "Send to Seller's Agent" button
- After generation, the letter preview shows each inspection item in a formatted block with costs pulled directly from the database
- Agent can click into any section of the letter to edit text inline

### 6.5 AIChatPanel

**Location:** `frontend/src/components/AIChatPanel.tsx`
**Description:** Collapsible sidebar panel (or bottom drawer on smaller screens) for per-transaction AI conversation.

**Sub-components:**

| Component | Description |
|-----------|-------------|
| `ChatMessageList` | Scrollable container with user messages right-aligned and assistant messages left-aligned |
| `ChatMessage` | Individual message bubble with role icon (user avatar or AI icon), content, timestamp |
| `ChatInput` | Text input with send button, message type toggle (Chat / Draft Email / Draft Letter) |
| `ChatStreamingIndicator` | Animated typing dots while AI response streams |
| `ChatSourceReferences` | Collapsible section on assistant messages showing referenced database records |

**Behavior:**
- Opens as a slide-in panel from the right side of the transaction detail page
- Loads history via `GET /api/transactions/{id}/chat`
- Sends messages via `POST /api/transactions/{id}/chat` and connects to the SSE response
- Tokens are appended to the current assistant message bubble as they arrive
- When the AI generates an email draft (message_type = 'email_draft'), a "Send this email" button appears that opens the SmartEmailComposerDialog pre-populated with the draft
- "Clear conversation" button archives all messages (with confirmation dialog)
- Message counter shows remaining messages for the day (e.g., "47/50 messages remaining")

### 6.6 AIAdvisorDashboardWidget

**Location:** `frontend/src/components/AIAdvisorDashboardWidget.tsx`
**Description:** Summary card on the main dashboard showing aggregate AI insight counts across all of the agent's transactions.

**Content:**
- Critical alerts count (red badge, large number)
- Warning count (yellow badge)
- Total active suggestions count
- "View All" link that filters the transaction list to those with active insights
- Preview list of the top 3 critical or warning insights with transaction name, insight title, and "View" link

### 6.7 AIStatsPanel

**Location:** `frontend/src/components/AIStatsPanel.tsx`
**Description:** Panel on the Settings page displaying AI usage and quality metrics.

**Content:**
- Total insights generated (all time, number)
- Insights by type (pie chart or bar chart: risk_alert, suggestion, prediction, celebration)
- Feedback distribution (stacked bar: positive, negative, neutral, no feedback)
- Dismiss rate (percentage with trend arrow)
- Daily token usage (line chart, last 30 days)
- Total chat messages and emails composed (numbers)
- Total repair letters generated (number)

### 6.8 TypeScript Types

**Location:** `frontend/src/types/ai.ts`

```typescript
export interface AIInsight {
  id: string;
  transaction_id: string;
  type: 'risk_alert' | 'suggestion' | 'prediction' | 'celebration';
  severity: 'critical' | 'warning' | 'info' | 'positive';
  title: string;
  description: string;
  suggested_action: string | null;
  suggested_action_url: string | null;
  status: 'active' | 'dismissed' | 'resolved' | 'snoozed';
  auto_resolve_condition: Record<string, any> | null;
  dismissed_at: string | null;
  dismissed_by: string | null;
  dismiss_reason: string | null;
  resolved_at: string | null;
  resolved_reason: string | null;
  snoozed_until: string | null;
  feedback_score: number | null;
  acted_on_at: string | null;
  model_version: string;
  prompt_version: string;
  trigger: string;
  source_references: Record<string, any> | null;
  tokens_used: number | null;
  created_at: string;
  updated_at: string;
}

export interface AIConversationMessage {
  id: string;
  transaction_id: string;
  agent_id: string;
  role: 'user' | 'assistant';
  content: string;
  message_type: 'chat' | 'email_draft' | 'readiness_summary' | 'repair_letter';
  model_version: string | null;
  prompt_version: string | null;
  tokens_used: number | null;
  source_references: Record<string, any> | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClosingReadinessItem {
  label: string;
  status: 'pass' | 'warn' | 'fail';
  detail: string;
}

export interface ClosingReadinessCategory {
  name: string;
  status: 'pass' | 'warn' | 'fail';
  items: ClosingReadinessItem[];
}

export interface ClosingReadinessResult {
  overall_status: 'ready' | 'ready_with_warnings' | 'not_ready' | 'critical';
  score: number;
  categories: ClosingReadinessCategory[];
  ai_summary: string | null;
}

export interface ComposeEmailRequest {
  intent: string;
  recipient_party_ids: string[];
  selected_inspection_item_ids: string[];
  custom_instructions: string | null;
  tone_override: string | null;
}

export interface ComposeEmailResponse {
  subject: string;
  body: string;
  recipients: { party_id: string; name: string; email: string; role: string }[];
  source_references: { field: string; source_type: string; source_id: string }[];
  model_version: string;
  tokens_used: number;
}

export interface GenerateLetterRequest {
  type: string;
  inspection_item_ids: string[];
  cover_note: string | null;
  format: 'html' | 'pdf';
}

export interface GenerateLetterResponse {
  letter_html: string;
  letter_text: string;
  total_estimated_cost_low: number;
  total_estimated_cost_high: number;
  item_count: number;
  source_references: { item_id: string; description: string; cost_low: number; cost_high: number }[];
  model_version: string;
  tokens_used: number;
}

export interface AIInsightSummary {
  critical: number;
  warning: number;
  info: number;
  positive: number;
  total_active: number;
}

export interface AIStats {
  total_insights_generated: number;
  insights_by_type: Record<string, number>;
  feedback_summary: {
    positive: number;
    negative: number;
    neutral: number;
    no_feedback: number;
  };
  dismiss_rate: number;
  avg_tokens_per_day: number;
  total_chat_messages: number;
  total_emails_composed: number;
  total_letters_generated: number;
  top_insight_types: { type: string; count: number }[];
}
```

### 6.9 Transaction Detail Page Modifications

The existing `TransactionDetail/index.tsx` currently has 7 tabs: Overview, Timeline, Parties, Documents, Inspections, History, Communications. Phase 4 adds:

- **AI Insights Panel** on the Overview tab (above existing content)
- **"Ask AI" button** in the page header actions area, opening the AIChatPanel sidebar
- **"Closing Readiness" button** in the page header actions area, opening the ClosingReadinessDialog
- **"Generate Repair Letter" button** on the Inspections tab, opening the RepairLetterDialog
- **"Compose Email" button** enhanced on the Communications tab to offer both template-based (Phase 2) and AI-composed (Phase 4) options

---

## 7. Definition of Success

| # | Criterion | Measurement | Target |
|---|-----------|-------------|--------|
| 1 | Daily risk scan completes for all active transactions | Celery job logs completion time and transaction count | 100% of active transactions scanned within 30 minutes of scheduled time |
| 2 | Insights are generated with appropriate severity levels | Manual review of 50 generated insights across 10 test transactions with known states | >90% of insights have the correct severity classification |
| 3 | Auto-resolution works correctly and promptly | Create an insight with a milestone condition, complete the milestone, verify insight resolves | 100% of auto-resolvable insights resolved within 5 minutes of condition being met |
| 4 | Closing readiness check returns accurate results | Run check on 5 transactions with known states, verify every line item against database | 100% accuracy on pass/warn/fail classification for all 6 categories |
| 5 | Smart email composer generates factually correct emails | Generate 10 emails across different intents, verify all data points against the database | Zero hallucinated data points (names, dates, amounts) in generated emails |
| 6 | Chat advisor responds within acceptable latency | Measure time-to-first-token for 20 chat messages across different transaction sizes | <2 seconds time-to-first-token (p95) |
| 7 | Chat advisor stays on topic when tested with off-topic prompts | Send 10 off-topic messages ("What is the weather?", "Write me a poem", etc.) | 100% of off-topic messages receive a polite redirect, no off-topic content generated |
| 8 | AI API cost stays within budget for a typical brokerage | Monitor daily token usage across all agents for one week with 50-100 active transactions | <$5/day total API cost |
| 9 | Agent feedback loop is functional end-to-end | Verify thumbs up, thumbs down, dismiss with reason, snooze, and unsnooze all work | All feedback actions persist correctly and appear accurately in AI stats |
| 10 | SSE streaming works across browsers | Test chat and readiness summary streaming in Chrome, Firefox, and Safari | Streaming renders correctly with no dropped tokens, connection timeouts, or rendering issues |
| 11 | Conversation history is preserved and paginated correctly | Create 60 messages in a transaction chat, verify pagination via before cursor, verify archive | History loads correctly with cursor-based pagination; archived messages excluded from default query |
| 12 | Dashboard widget shows accurate counts | Create critical and warning insights across 3 transactions, verify dashboard widget | Widget shows correct counts and top insights within 5 seconds of page load |
| 13 | Repair letter references are accurate | Generate a repair request letter for 3 inspection items, verify every cost and description matches the database | 100% of source references point to valid, correct `inspection_items` records |
| 14 | Rate limiting and circuit breaker function correctly | Simulate API rate limits during a daily scan (mock 429 responses) | Scan pauses, retries with exponential backoff, and resumes without data loss or duplicate insights |
| 15 | Model version is tracked on all AI outputs | Query `ai_insights` and `ai_conversations` tables after generating content | 100% of records have non-null `model_version` and `prompt_version` |
| 16 | Repair letter PDF generation produces a valid, professional document | Generate 3 repair letters and verify PDF output renders correctly with proper formatting | PDF includes all selected inspection items, correct cost ranges, agent info, and clean formatting |

---

## 8. Regression Test Plan

### Phase 4 New Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P4-01 | `test_daily_scan_generates_insights` -- Run the daily scan on a transaction with an overdue milestone. | A `risk_alert` insight with severity `critical` is created with a valid `source_references` pointing to the overdue milestone. |
| P4-02 | `test_daily_scan_auto_resolves_stale_insights` -- Create an insight with `auto_resolve_condition = {milestone_id: X, required_status: completed}`. Complete milestone X. Run the scan. | Insight status changes to `resolved` with `resolved_reason = 'auto:condition_met'`. |
| P4-03 | `test_daily_scan_skips_draft_transactions` -- Create a transaction with `status = 'draft'` and an overdue milestone. Run the daily scan. | No insights generated for the draft transaction. |
| P4-04 | `test_daily_scan_max_five_insights_per_transaction` -- Create a transaction with 8 overdue milestones and 3 silent parties. Run the scan. | Maximum 5 insights generated for this transaction, prioritized by severity. |
| P4-05 | `test_insight_dismiss_requires_reason_for_critical` -- PATCH dismiss a critical insight with no reason. | 422 Unprocessable Entity. PATCH with a reason returns 200 and insight status = 'dismissed'. |
| P4-06 | `test_insight_snooze_and_reactivation` -- Snooze an insight until a time 1 second in the past. Run the snooze-check logic. | Insight status changes from 'snoozed' back to 'active'. |
| P4-07 | `test_insight_feedback_persists` -- POST feedback (score=1) on an insight. GET the insight. | `feedback_score = 1` persisted and returned. |
| P4-08 | `test_closing_readiness_all_pass` -- Create a transaction with all milestones completed, all required documents uploaded, all required parties present. Run the check. | `overall_status = 'ready'`, `score = 100`, all categories have `status = 'pass'`. |
| P4-09 | `test_closing_readiness_missing_milestone` -- Create a transaction with one overdue milestone. | `overall_status = 'not_ready'`, milestones category `status = 'fail'`, overdue milestone listed in items. |
| P4-10 | `test_closing_readiness_missing_party` -- Create a buyer-side financed transaction without a lender party. | Parties category `status = 'fail'`, "Lender" listed as missing. |
| P4-11 | `test_closing_readiness_unresolved_inspection_items` -- Create inspection items with `repair_status = 'pending'` and severity `high`. | Inspection category `status = 'fail'`, items listed with cost ranges. |
| P4-12 | `test_email_composer_repair_request` -- Compose a repair request email referencing 2 inspection items. | Response includes both items' descriptions and costs. `source_references` map to the correct `inspection_items` IDs. |
| P4-13 | `test_email_composer_no_hallucination` -- Compose an email (with mocked Claude returning a controlled response). Parse every data point. | Every name, date, and amount in the response body exists in the database for this transaction. |
| P4-14 | `test_repair_letter_generation` -- Generate a repair letter for 3 inspection items. | Letter HTML contains all 3 items with correct descriptions, locations, and cost ranges from the database. `total_estimated_cost_low` equals the sum of the 3 items' `estimated_cost_low`. |
| P4-15 | `test_repair_letter_no_invented_costs` -- Generate a repair letter (mocked Claude). Verify no dollar amounts appear that do not match `inspection_items` records. | All dollar amounts in the letter trace to database records. |
| P4-16 | `test_chat_saves_user_message` -- POST a chat message. GET chat history. | User message appears with `role = 'user'`, correct `content`, correct `message_type`. |
| P4-17 | `test_chat_saves_assistant_message` -- POST a chat message (mocked Claude). | Assistant message saved with `role = 'assistant'`, non-null `model_version`, non-null `tokens_used`. |
| P4-18 | `test_chat_message_limit_per_day` -- Send 51 messages in one day (limit=50). | First 50 succeed. 51st returns 429 Too Many Requests with error message about daily limit. |
| P4-19 | `test_chat_archive_soft_deletes` -- Create 5 messages. DELETE chat. GET chat. | All 5 messages have `is_archived = True`. GET returns empty list (default excludes archived). |
| P4-20 | `test_chat_off_topic_redirect` -- Send "What is the weather today?" (mocked Claude configured to redirect). | Response contains the redirect phrase: "I can only help with questions related to this transaction." |
| P4-21 | `test_ai_stats_endpoint` -- Create insights with various types and feedback scores. GET `/api/stats/ai`. | All aggregation fields (total, by_type, feedback_summary, dismiss_rate) match expected values. |
| P4-22 | `test_insight_summary_endpoint` -- Create 3 critical, 2 warning, 1 info insight across multiple transactions. GET `/api/insights/summary`. | Returns `{critical: 3, warning: 2, info: 1, positive: 0, total_active: 6}`. |
| P4-23 | `test_rate_limit_retry` -- Mock Claude client to raise `RateLimitError` twice then succeed. | `call_claude` retries with exponential backoff and returns the successful response. |
| P4-24 | `test_circuit_breaker_pauses_scan` -- Mock Claude client to raise `RateLimitError` 3 consecutive times. | Scan pauses for the configured duration (60s), logs the circuit breaker activation. |
| P4-25 | `test_shared_ai_client_returns_token_count` -- Call `call_claude` with a simple prompt. | Returns a tuple of `(response_text, tokens_used)` where `tokens_used > 0`. |
| P4-26 | `test_compose_email_send_creates_communication` -- Compose an email, then POST to the send endpoint. | A `Communication` record is created in the database with correct subject, body, recipient, and transaction_id. |

### Phase 1-3 Regression Tests

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| R-01 | `test_create_transaction` -- POST `/api/transactions` with valid payload. | Transaction created with correct fields, 201 status. |
| R-02 | `test_update_transaction` -- PATCH `/api/transactions/{id}` with partial fields. | Only specified fields updated, amendment record created. |
| R-03 | `test_list_transactions_pagination` -- GET `/api/transactions` with page/limit params. | Correct subset returned with pagination metadata. |
| R-04 | `test_create_party` -- POST `/api/transactions/{id}/parties` with valid party. | Party created and associated with transaction. |
| R-05 | `test_contract_parsing` -- Upload a test PDF and trigger contract parsing (mocked Claude). | Transaction fields populated from parsed data, `ai_extraction_confidence` set. |
| R-06 | `test_file_upload_to_minio` -- Upload a file via the files endpoint. | File stored in MinIO, `File` record created with correct URL and content_type. |
| R-07 | `test_create_milestone` -- POST a milestone to a transaction. | Milestone created with correct `due_date`, `status`, and `responsible_party_role`. |
| R-08 | `test_milestone_status_update` -- PATCH milestone status from 'pending' to 'completed'. | Status updated, `completed_at` timestamp set. |
| R-09 | `test_send_email_communication` -- Trigger email send via communication endpoint. | Communication record created with `status = 'sent'`. |
| R-10 | `test_inspection_analysis_creation` -- POST inspection analysis with 3 items. | `InspectionAnalysis` record created with 3 `InspectionItem` children. |
| R-11 | `test_inspection_item_repair_status_update` -- Update an inspection item's `repair_status`. | Status changes correctly, `updated_at` timestamp refreshed. |
| R-12 | `test_dashboard_stats` -- GET `/api/stats` after creating test transactions. | Stats endpoint returns correct counts for transactions, milestones, parties. |
| R-13 | `test_transaction_detail_includes_all_relations` -- GET `/api/transactions/{id}` for a fully-populated transaction. | Response includes parties, milestones, files, inspections, communications, amendments, AND now `ai_insights`. |
| R-14 | `test_cascade_delete_transaction` -- Soft-delete a transaction that has parties, milestones, files, insights, and conversations. | All child records cascade correctly. `ai_insights` and `ai_conversations` records are also deleted. |
| R-15 | `test_amendment_creation` -- Update a transaction field. | Amendment record created with old_value, new_value, changed_by_id, and correct field_changed. |

---

## 9. Implementation Order

### Week 10: Foundation and Risk Monitor

**Step 4.1: Data Model and Shared AI Client (Days 1-2)**

Files to create or modify:
- `backend/alembic/versions/xxxx_add_ai_insights_and_conversations.py` -- New migration
- `backend/app/models/ai_insight.py` -- New model
- `backend/app/models/ai_conversation.py` -- New model
- `backend/app/models/__init__.py` -- Add new model imports
- `backend/app/models/transaction.py` -- Add `ai_insights` and `ai_conversations` relationships
- `backend/app/models/user.py` -- Add `ai_conversations` relationship
- `backend/app/agents/ai_client.py` -- New shared AI client (extract from `contract_parser.py`)
- `backend/app/agents/contract_parser.py` -- Refactor to use shared client
- `backend/app/schemas/ai_insight.py` -- New schemas
- `backend/app/schemas/ai_conversation.py` -- New schemas
- `backend/app/schemas/closing_readiness.py` -- New schemas
- `backend/app/schemas/email_compose.py` -- New schemas
- `backend/app/schemas/repair_letter.py` -- New schemas

Tasks:
1. Create Alembic migration for `ai_insights` and `ai_conversations` tables with all indexes
2. Create SQLAlchemy models: `AIInsight`, `AIConversation`
3. Update `Transaction` and `User` models with new relationships
4. Update `models/__init__.py` and `schemas/__init__.py` exports
5. Extract `_call_claude_with_retry` from `contract_parser.py` into `ai_client.py` with `call_claude()` (non-streaming) and `stream_claude()` (streaming) functions
6. Add model constants: `MODEL_HAIKU = "claude-3-5-haiku-20241022"`, `MODEL_SONNET = "claude-sonnet-4-20250514"`
7. Refactor `contract_parser.py` to import from `ai_client.py`
8. Create all Pydantic schemas for Phase 4 endpoints
9. Write unit tests for models, schemas, and the shared AI client

**Step 4.2: Transaction Risk Monitor (Days 3-5)**

Files to create or modify:
- `backend/app/agents/transaction_advisor.py` -- New agent
- `backend/app/services/insight_service.py` -- New service
- `backend/app/api/insights.py` -- New API router
- `backend/app/api/__init__.py` -- Register insights router
- `backend/app/tasks/ai_scan.py` -- New Celery task (or add to existing tasks module)
- `backend/app/config.py` -- Add AI configuration settings

Tasks:
1. Add AI configuration to `Settings`: `ai_scan_cron`, `ai_scan_batch_size`, `ai_scan_delay_seconds`, `ai_daily_token_budget`, `ai_max_concurrent_calls`
2. Implement `TransactionAdvisor` agent:
   - `build_context_snapshot(transaction)` -- Serializes transaction data for the prompt
   - `analyze_transaction(snapshot, existing_insights)` -- Calls Claude Haiku, returns parsed insights
   - `auto_resolve_insights(transaction_id)` -- Evaluates open insights' auto_resolve_conditions
3. Implement `insight_service.py`: CRUD operations, dismiss, snooze, feedback, list with filters
4. Create Celery beat task `daily_risk_scan` that queries active transactions, processes in batches, calls TransactionAdvisor
5. Create API endpoints: GET insights (list + detail), PATCH dismiss/snooze/feedback, POST refresh, GET summary
6. Register the insights router in `api/__init__.py`
7. Write integration tests for the daily scan (mocked Claude)
8. Write API tests for all insight endpoints

### Week 11: Closing Readiness, Email Composer, and Repair Letters

**Step 4.3: Closing Readiness Check (Days 1-2)**

Files to create or modify:
- `backend/app/agents/closing_readiness.py` -- New agent
- `backend/app/services/readiness_service.py` -- New service
- `backend/app/api/readiness.py` -- New API router
- `backend/app/api/__init__.py` -- Register readiness router

Tasks:
1. Implement `ClosingReadinessChecker` with all 6 audit categories as pure database queries
2. Implement the document requirements matrix (required docs per financing_type + representation_side)
3. Implement the party requirements matrix (required roles per representation_side)
4. Implement score calculation logic
5. Implement SSE endpoint for the AI summary stream (using `stream_claude` from `ai_client.py`)
6. Create API endpoints: POST readiness check, GET readiness stream
7. Write unit tests for each audit category with known data states
8. Write integration test for the full readiness check

**Step 4.4: Smart Email Composer and Repair Letter Generator (Days 3-5)**

Files to create or modify:
- `backend/app/agents/smart_email_composer.py` -- New agent
- `backend/app/agents/repair_letter_generator.py` -- New agent
- `backend/app/services/email_compose_service.py` -- New service
- `backend/app/services/letter_service.py` -- New service
- `backend/app/api/compose.py` -- New API router (or extend existing)
- `backend/app/api/__init__.py` -- Register new routers

Tasks:
1. Implement `SmartEmailComposer` agent with intent-specific prompt templates
2. Implement context assembly per intent (repair_request, status_update, lender_followup, etc.)
3. Implement source reference tracking (map AI output fields to database record IDs)
4. Implement `RepairLetterGenerator` agent with the formal letter prompt template
5. Implement post-generation validation: verify all dollar amounts and names in output match database
6. Create compose and send API endpoints
7. Create generate-letter and send-letter API endpoints
8. Integration with existing `Communication` model for sent emails
9. Write integration tests for each email intent (mocked Claude)
10. Write the hallucination detection test

### Week 12: Chat Advisor and Frontend

**Step 4.5: Ask AI Chat (Days 1-2)**

Files to create or modify:
- `backend/app/agents/chat_advisor.py` -- New agent
- `backend/app/services/chat_service.py` -- New service
- `backend/app/api/chat.py` -- New API router
- `backend/app/api/__init__.py` -- Register chat router

Tasks:
1. Implement `ChatAdvisor` agent with system prompt builder (refreshed per request)
2. Implement SSE streaming endpoint using `stream_claude`
3. Implement conversation history management (fetch last 20 non-archived messages)
4. Create chat history endpoint with cursor-based pagination
5. Create chat archive (soft delete) endpoint
6. Implement daily message limit check (Redis counter with TTL)
7. Implement message type routing (chat, email_draft, repair_letter)
8. Write API tests for chat endpoints
9. Write integration tests for streaming and conversation persistence

**Step 4.6: Frontend Components (Days 3-5)**

Files to create or modify:
- `frontend/src/types/ai.ts` -- New TypeScript types
- `frontend/src/components/AIInsightsPanel.tsx` -- New component
- `frontend/src/components/InsightCard.tsx` -- New component
- `frontend/src/components/ClosingReadinessDialog.tsx` -- New component
- `frontend/src/components/SmartEmailComposerDialog.tsx` -- New component
- `frontend/src/components/RepairLetterDialog.tsx` -- New component
- `frontend/src/components/AIChatPanel.tsx` -- New component
- `frontend/src/components/AIAdvisorDashboardWidget.tsx` -- New component
- `frontend/src/components/AIStatsPanel.tsx` -- New component
- `frontend/src/pages/TransactionDetail/index.tsx` -- Add AI buttons and insights panel
- `frontend/src/pages/TransactionDetail/OverviewTab.tsx` -- Embed AIInsightsPanel
- `frontend/src/pages/TransactionDetail/InspectionsTab.tsx` -- Add repair letter button
- `frontend/src/pages/Dashboard.tsx` -- Add AIAdvisorDashboardWidget
- `frontend/src/pages/Settings.tsx` -- Add AIStatsPanel
- `frontend/src/lib/api.ts` -- Add AI endpoint functions and SSE helpers

Tasks:
1. Create TypeScript types for all AI-related data structures
2. Build `AIInsightsPanel` with `InsightCard` sub-components (dismiss, snooze, feedback)
3. Build `ClosingReadinessDialog` with streaming AI summary via EventSource
4. Build `SmartEmailComposerDialog` with 4-step flow (intent, config, preview, send)
5. Build `RepairLetterDialog` with item selection and live preview
6. Build `AIChatPanel` with SSE streaming message display
7. Build `AIAdvisorDashboardWidget` for the main dashboard
8. Build `AIStatsPanel` for the Settings page
9. Add SSE helper utilities to `api.ts` for EventSource connection management
10. Integrate all components into existing pages (transaction detail, dashboard, settings)
11. Run full regression test suite across Phases 1-4

---

## 10. Dependencies

### What Must Be Complete from Phases 1-3

| Phase | Requirement | Why Phase 4 Needs It |
|-------|------------|---------------------|
| Phase 1 | Transaction CRUD with all fields | The advisor analyzes transaction data -- without transactions, there is nothing to advise on |
| Phase 1 | Milestones with `due_date`, `status`, `completed_at` | The risk monitor's primary signal is milestone status relative to deadlines |
| Phase 1 | Parties with `role`, `name`, `email` | The email composer and repair letter generator address specific parties by role |
| Phase 1 | Contract parser operational | Phase 4 refactors the shared AI client out of the existing parser |
| Phase 1 | File upload to MinIO | The closing readiness check audits uploaded documents against required documents |
| Phase 2 | Communication model with `sent_at`, `status` | The advisor checks communication recency per party to detect "silent" parties |
| Phase 2 | Celery beat scheduler running | The daily risk scan runs as a Celery beat task |
| Phase 2 | Email sending capability (Resend or stub) | The email composer's "send" action creates Communication records and delivers emails |
| Phase 3 | Inspection analyses with items | The repair letter generator and closing readiness check depend on inspection data |
| Phase 3 | Inspection items with `repair_status`, `severity`, `estimated_cost_low/high` | The repair letter pulls specific findings, costs, and severities from these records |

### Infrastructure Dependencies

| Dependency | Purpose | Current Status |
|-----------|---------|----------------|
| Anthropic Claude API | AI model calls (Haiku for scans, Sonnet for chat/compose) | Already configured in `app/config.py` via `claude_api_key` |
| Celery + Redis | Daily scan background job, snooze reactivation, message rate limiting | Celery in `requirements.txt`; need beat scheduler configuration and worker/beat services in docker-compose |
| Redis | Celery broker, transaction context caching (1h TTL), concurrent AI call semaphore, daily message counter | Already running in `docker-compose.yml` |
| PostgreSQL | `ai_insights` and `ai_conversations` tables | Already running, needs Alembic migration |

### New Python Dependencies

| Package | Purpose | Status |
|---------|---------|--------|
| `sse-starlette` | Server-Sent Events support for FastAPI streaming endpoints | **NEW** -- add to `requirements.txt` |

All other dependencies (`anthropic`, `celery`, `redis`, `fastapi`, `sqlalchemy`) are already present in `requirements.txt`.

### Docker Compose Additions

If not already added by Phase 2, add Celery worker and beat services:

```yaml
  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/ttc
      - REDIS_URL=redis://redis
      - CLAUDE_API_KEY=your_claude_api_key
    depends_on:
      - db
      - redis

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis
    depends_on:
      - redis
```

### Configuration Additions to `backend/app/config.py`

```python
# AI Advisor settings
ai_scan_cron: str = "0 6 * * *"                # Daily at 6:00 AM UTC
ai_scan_batch_size: int = 5                     # Transactions per API call batch
ai_scan_delay_seconds: float = 2.0              # Delay between batches (rate limit safety)
ai_daily_token_budget: int = 500000             # Max tokens per agent per day
ai_max_concurrent_calls: int = 5                # Redis semaphore limit for concurrent API calls
ai_chat_max_messages_per_day: int = 50          # Per transaction per day
ai_chat_max_history: int = 20                   # Messages included in chat context window
ai_chat_archive_after_days: int = 30            # Auto-archive messages older than this
ai_circuit_breaker_threshold: int = 3           # Consecutive rate limit errors before pause
ai_circuit_breaker_pause_seconds: int = 60      # Pause duration after circuit breaker triggers
```

### External Service Requirements

- **Anthropic API Tier**: Tier 2+ recommended for production. Tier 2 provides 4,000 requests/minute for Haiku and 1,000 requests/minute for Sonnet, which is sufficient for a brokerage with up to 500 active transactions.
- **Redis Memory**: Allocate at least 256MB for transaction context caching. Each cached snapshot is approximately 2-5KB; 1,000 cached transactions would use approximately 5MB plus Redis overhead.
- **No additional external services**: Phase 4 does not introduce any new external providers beyond the Anthropic API that is already configured. Email delivery uses the existing Resend integration from Phase 2.

### Cost Projection

| Agent | Model | Est. Cost per Unit | Daily Volume (100 txn) | Daily Cost |
|-------|-------|--------------------|------------------------|------------|
| TransactionAdvisor (daily scan) | Claude 3.5 Haiku | ~$0.003/transaction | 100 | ~$0.30 |
| ClosingReadinessChecker (AI summary) | Claude 3.5 Haiku | ~$0.02/check | ~10 checks | ~$0.20 |
| SmartEmailComposer | Claude Sonnet 4 | ~$0.08/email | ~20 emails | ~$1.60 |
| RepairLetterGenerator | Claude Sonnet 4 | ~$0.10/letter | ~5 letters | ~$0.50 |
| ChatAdvisor | Claude Sonnet 4 | ~$0.10/message | ~50 messages | ~$5.00 |
| **Total** | | | | **~$7.60/day** |

At scale (500 active transactions), the daily scan cost increases to approximately $1.50/day. Chat and compose costs scale with agent usage, not transaction count. The per-agent daily token budget serves as a hard cost ceiling.
