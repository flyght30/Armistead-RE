# Phase 4: Inspection Report Analysis

**Timeline:** Weeks 13-16  
**Status:** Not Started  
**Depends On:** Phase 3 Complete  
**CoV Status:** Verified (see below)

---

## 1. Phase Objective

Build the AI-powered inspection report analyzer that scans home inspection PDFs, extracts all findings, categorizes by severity, estimates repair costs, ranks by risk, and generates an executive summary the agent can use for client communication and repair negotiations.

**Deliverable:** Agent uploads inspection report → AI analyzes within 60 seconds → agent sees ranked findings with cost estimates → can share summary with client → can track repair negotiation status.

---

## 2. Scope

### In Scope
- Inspection report PDF upload and processing
- Inspection Analyzer AI Agent (Claude API)
- Finding extraction with severity classification (critical → cosmetic)
- Estimated repair cost ranges per finding
- Risk-based ranking (most important first)
- Executive summary generation
- Shareable client summary (formatted, non-technical)
- Repair request tracking (identified → requested → countered → agreed → denied → completed)
- Integration with Phase 3 milestones (inspection complete triggers follow-ups)
- Integration with Phase 2 emails (share analysis via email)

### Out of Scope (This Phase)
- Automated repair request document generation
- Contractor matching/referrals
- Photo extraction from inspection reports
- Historical cost data by market/ZIP code

---

## 3. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|-------------------|
| US-4.1 | As an agent, I can upload a home inspection report PDF | PDF accepted, stored in S3, associated with transaction |
| US-4.2 | As an agent, I see AI analysis within 60 seconds | Analysis complete with all findings, severity, costs, and summary |
| US-4.3 | As an agent, findings are ranked from most to least important | Critical/safety items first, cosmetic last |
| US-4.4 | As an agent, each finding shows estimated repair cost range | Low-high range per finding in dollars |
| US-4.5 | As an agent, I see an executive summary | Total cost range, top 5 priorities, overall risk level, recommendation |
| US-4.6 | As an agent, I can share a client-friendly summary via email | Formatted summary email generated and sent through existing email system |
| US-4.7 | As an agent, I can track repair negotiation status per finding | Status: identified, requested, countered, agreed, denied, completed |
| US-4.8 | As an agent, when I update repair statuses, follow-up emails notify parties | Status changes trigger follow-up communications |
| US-4.9 | As an agent, I can filter/sort findings by severity, cost, or status | Filter controls on analysis view |
| US-4.10 | As an agent, I see which items require licensed professional evaluation | Flagged items that need structural engineer, electrician, etc. |

---

## 4. Technical Tasks

### 4.1 Inspection Analyzer AI Agent (Week 13-14)

| Task | Description | Estimate |
|------|-------------|----------|
| T-4.1 | Inspection Analyzer prompt engineering and schema design | 8h |
| T-4.2 | PDF text extraction for inspection reports (PyMuPDF) | 4h |
| T-4.3 | Large report handling (chunking for context window limits) | 4h |
| T-4.4 | Finding extraction and classification pipeline | 6h |
| T-4.5 | Cost estimation logic (severity-based defaults + AI refinement) | 4h |
| T-4.6 | Risk ranking algorithm (severity × cost × safety factor) | 3h |
| T-4.7 | Executive summary generation | 4h |
| T-4.8 | Client-friendly summary generation (non-technical language) | 3h |
| T-4.9 | Professional evaluation flagging (items needing licensed specialist) | 2h |
| T-4.10 | Response validation (Pydantic schema for analysis output) | 3h |

### 4.2 API Development (Week 14-15)

| Task | Description | Estimate |
|------|-------------|----------|
| T-4.11 | POST /api/transactions/:id/inspection — upload report | 3h |
| T-4.12 | POST /api/transactions/:id/inspection/analyze — trigger AI analysis | 4h |
| T-4.13 | GET /api/transactions/:id/inspection/analysis — get results | 2h |
| T-4.14 | PATCH /api/transactions/:id/inspection/items/:id — update item status | 2h |
| T-4.15 | POST /api/transactions/:id/inspection/share — generate shareable summary | 3h |
| T-4.16 | GET /api/transactions/:id/inspection/summary — client-friendly format | 2h |
| T-4.17 | Integration: mark inspection milestone complete when analysis done | 2h |
| T-4.18 | Integration: trigger follow-up emails on repair status changes | 3h |

### 4.3 Frontend Development (Weeks 15-16)

| Task | Description | Estimate |
|------|-------------|----------|
| T-4.19 | Inspection upload component (on transaction detail page) | 3h |
| T-4.20 | Analysis loading state with progress indicator | 2h |
| T-4.21 | Executive summary card (total cost, risk level, top items, recommendation) | 4h |
| T-4.22 | Findings list with severity badges and cost ranges | 6h |
| T-4.23 | Finding detail panel (description, location, assessment, recommendation) | 4h |
| T-4.24 | Filter/sort controls (severity, cost, status, location) | 3h |
| T-4.25 | Repair status dropdown per finding | 3h |
| T-4.26 | "Share with Client" button → email preview → send | 3h |
| T-4.27 | Licensed professional evaluation flags/badges | 2h |
| T-4.28 | Repair negotiation summary view (agreed vs. denied totals) | 3h |

---

## 5. Inspection Analyzer Specification

### 5.1 System Prompt

```
You are a home inspection report analyzer for real estate transactions. 
You parse inspection reports and extract every finding, classify severity, 
estimate repair costs, and assess risk.

INPUT: Full text of a home inspection report for a residential property.

OUTPUT: JSON with the following structure:
{
  "executive_summary": {
    "overall_risk_level": "low|moderate|high|critical",
    "total_estimated_cost_low": number,
    "total_estimated_cost_high": number,
    "top_priorities": [top 5 items with brief descriptions],
    "recommendation": "proceed_as_is|request_repairs|request_credit|
                       further_evaluation|consider_walking_away",
    "recommendation_reasoning": "string"
  },
  "findings": [
    {
      "description": "Clear description of the issue",
      "location": "Where in the property (e.g., 'Master bathroom', 'Roof')",
      "severity": "critical|major|moderate|minor|cosmetic",
      "estimated_cost_low": number,
      "estimated_cost_high": number,
      "risk_assessment": "Why this matters and potential consequences if ignored",
      "recommendation": "What should be done about it",
      "requires_licensed_professional": boolean,
      "professional_type": "structural_engineer|electrician|plumber|
                           roofer|hvac_tech|pest_control|null",
      "negotiation_priority": "high|medium|low"
    }
  ]
}

SEVERITY RULES:
- CRITICAL: Immediate safety hazard OR structural integrity compromised
  (active gas leak, foundation failure, no smoke detectors, knob-and-tube wiring, 
   major water intrusion, mold, structural cracks)
- MAJOR: Significant system at/past end of life OR major repair needed
  (roof replacement, HVAC replacement, main line plumbing, panel upgrade,
   water heater failure)
- MODERATE: Functional issue needing professional repair within 1-2 years
  (aging water heater, minor leaks, improper venting, deck safety issues,
   grading/drainage concerns)
- MINOR: Small repairs, handyman-level work
  (dripping faucets, missing caulk, sticking doors, loose hardware,
   minor grading, gutter cleaning)
- COSMETIC: Appearance only, no functional or safety impact
  (paint, nail pops, minor drywall, trim damage, cosmetic cracks)

COST ESTIMATION RULES:
- Base costs on typical US residential repair costs (2024-2026 pricing)
- Always provide a LOW and HIGH range
- Critical items: factor in urgency premium (10-20%)
- Include labor in all estimates
- If uncertain, widen the range rather than guess wrong
- For items requiring specialist evaluation, note "cost pending evaluation"
  and estimate the evaluation cost itself ($200-$500 typically)

RANKING RULES:
- Sort findings by: critical first, then major, moderate, minor, cosmetic
- Within each severity level, sort by estimated cost (highest first)
- Safety hazards ALWAYS rank above non-safety items regardless of cost
```

### 5.2 Chunking Strategy for Large Reports

Home inspection reports can be 40-80+ pages. Strategy:
1. Extract full text from PDF
2. If text < 150,000 characters (fits in Claude's context): send as single request
3. If text > 150,000 characters: split into logical sections (structure, exterior, interior, systems, etc.), analyze each section, then merge and deduplicate findings
4. Always send the executive summary section (if identifiable) in every chunk for context

### 5.3 Client Summary Format

The client-friendly summary strips technical jargon and focuses on:
- Overall assessment (positive framing: "The home is in [good/fair/needs attention] condition")
- Top items that need attention (plain English descriptions)
- Estimated total repair investment range
- Recommended next steps
- Reassurance that the agent is handling negotiations

---

## 6. Chain-of-Verification: Phase 4

### Step 1: Baseline
Phase 4 adds inspection report upload, AI analysis with severity ranking and cost estimates, client summary sharing, and repair negotiation tracking.

### Step 2: Self-Questioning

**Q1:** How accurate are AI-generated repair cost estimates without knowing the local market?
**Q2:** What if the inspection report format is unusual (narrative vs. checklist, photos-heavy, etc.)?
**Q3:** Could the AI miss critical safety items and rank them too low?
**Q4:** What liability does the agent take on by sharing AI-generated cost estimates with clients?
**Q5:** How do we handle inspection reports with poor OCR quality (scanned, handwritten notes)?

### Step 3: Independent Verification

**A1 — Cost Accuracy:** AI cost estimates are inherently approximate. They should be framed as "typical ranges" not precise quotes. The system should include a disclaimer: "Cost estimates are approximate national averages and may vary by location. Obtain contractor quotes for accurate pricing." The value is in relative ranking (most expensive items first), not absolute accuracy.
**Resolution:** All cost displays include disclaimer. Framed as "estimated range" not quotes. Agent can override any cost estimate.

**A2 — Unusual Formats:** Inspection reports vary widely. Some are checklist-based (InterNACHI format), some are narrative, some are photo-heavy with minimal text. The AI should handle all formats because it's parsing natural language, not a fixed schema. For photo-heavy reports with minimal text, accuracy may be lower — the system should warn the agent if extracted text is unusually short.
**Resolution:** If extracted text < 5,000 characters for a multi-page PDF, warn agent that the report may be image-heavy and analysis may be incomplete. Suggest manual review.

**A3 — Missing Critical Items:** This is the biggest risk. A false negative on a safety issue could have serious consequences. Mitigation: the system should ALWAYS flag common safety categories (electrical, structural, gas, water intrusion, mold) even if the report says they're fine — providing a "no issues found" entry to confirm the AI reviewed that category. This creates a checklist effect.
**Resolution:** Mandatory safety category review. Even if no issues found, the analysis confirms each safety category was evaluated. Add a "safety categories reviewed" section to the output.

**A4 — Liability:** The AI analysis is a TOOL for the agent, not professional advice. Clear disclaimers are essential. The agent is the licensed professional making recommendations to their client. The AI provides data; the agent provides advice. Client-facing summaries must include: "This analysis is generated as a reference tool. Consult with your agent and qualified professionals for specific recommendations."
**Resolution:** Disclaimers on all outputs. Agent reviews before sharing. System never sends analysis directly to client without agent approval.

**A5 — Poor OCR Quality:** Scanned inspection reports may have poor text extraction. Same approach as contract parsing: if text extraction yields minimal results, attempt vision-based analysis (sending pages as images to Claude). Inspection reports are typically longer than contracts, so this may require multiple vision API calls.
**Resolution:** Text extraction first. If insufficient, fall back to vision-based analysis with page-by-page processing. Warn agent about potential reduced accuracy.

### Step 4: Confidence Check
**Confidence: 95%** — The cost accuracy and liability concerns are managed through disclaimers and agent-in-the-loop design. The safety category checklist is a strong safeguard against missed critical items.

### Step 5: Implement
Proceed with Phase 4. Incorporate safety category checklist, disclaimers on all outputs, and image fallback for scanned reports.

---

## 7. Definition of Done (Phase 4)

| Criteria | Verification |
|----------|-------------|
| Inspection report upload works (PDF) | Manual test |
| Analysis completes within 60 seconds | Performance test on 3+ reports |
| All findings extracted with severity classification | Manual comparison against source report |
| Cost estimates provided per finding | Verify ranges are reasonable |
| Findings ranked correctly (critical first, then by cost) | Manual verification |
| Executive summary accurate and useful | Agent review |
| Client summary is non-technical and professional | Manual review |
| Share with client via email works | E2E test |
| Repair status tracking works per finding | CRUD test |
| Repair status changes trigger follow-up emails | Integration test |
| Safety categories always reviewed (even if no issues) | Verify with "clean" inspection report |
| Disclaimers present on all outputs | Manual check |
| Large reports (40+ pages) processed successfully | Test with large report |
| Poor-quality scanned reports handled gracefully | Test with scanned report |
| Filter/sort works on findings list | Manual test |

---

## 8. Test Plan

### 8.1 Unit Tests

| Test Area | Tests |
|-----------|-------|
| Inspection analyzer | Correct severity classification; cost ranges reasonable; ranking order correct |
| PDF extraction | Text extraction from text PDF; image fallback trigger; chunking for large docs |
| Executive summary | Risk level calculation; top priorities selection; recommendation logic |
| Repair status | Status transitions; follow-up trigger on status change |

### 8.2 Integration Tests

| Test | Steps | Expected Result |
|------|-------|----------------|
| Full analysis flow | Upload report → trigger analysis → get results | All findings extracted, ranked, costed |
| Large report | Upload 60-page report → analyze | Completes < 90 seconds, no missing sections |
| Clean report | Upload report with no major issues | Overall risk "low", recommendation "proceed_as_is" |
| Critical findings | Upload report with safety issues | Critical items ranked first, recommendation reflects severity |
| Client summary | Generate → review → send via email | Non-technical, professional, includes disclaimer |
| Repair tracking | Update item status to "agreed" → check follow-ups | Follow-up emails generated for relevant parties |
| Milestone integration | Analysis complete → inspection milestone | Inspection milestone auto-completed |

### 8.3 AI Accuracy Tests

| Test | Criteria | Min Accuracy |
|------|----------|-------------|
| Finding extraction | All items from report captured | 90% (compared to manual review) |
| Severity classification | Correct severity level | 85% agreement with professional opinion |
| Cost estimation | Within 50% of contractor quotes | 70% of items (best effort) |
| Safety item detection | All critical safety items found | 95% (this is the highest bar) |
| Executive summary | Accurate reflection of findings | Qualitative agent review |

### 8.4 E2E Tests

| Test | Flow |
|------|------|
| Happy path | Upload report → Wait for analysis → Review findings → Share with client → Track repairs |
| Repair negotiation | Mark items as "requested" → Update to "agreed" → Verify follow-up emails |
| Full transaction flow | Upload contract → Parse → Emails → Milestones → Upload inspection → Analysis → Repairs → Continue to closing |

---

## 9. Phase 4 Success Criteria

| Metric | Target | How Measured |
|--------|--------|-------------|
| All user stories completed | 10/10 | Story acceptance criteria |
| Analysis time | < 60 seconds for standard reports | Performance tests |
| Finding extraction accuracy | ≥ 90% | Manual comparison on 3+ reports |
| Safety item detection | ≥ 95% | Manual verification |
| Cost estimates within reasonable range | ≥ 70% within 50% of actual | Best-effort comparison |
| Agent finds analysis useful | Qualitative positive feedback | Agent review sessions |
| Client summary professional and clear | Qualitative positive feedback | Agent review |
| No analysis shared without agent approval | 100% | Workflow enforcement |

---

*Phase 4 Complete → Proceed to Phase 5: Polish & Launch*
