# Transaction-to-Close: Project Memory

**Last Updated:** 2026-02-12  
**Current Phase:** Pre-Development (Documentation Complete)

---

## Project Status

| Item | Status |
|------|--------|
| PRD | ✅ Complete (v2.0) |
| Phase 1 Spec | ✅ Complete |
| Phase 2 Spec | ✅ Complete |
| Phase 3 Spec | ✅ Complete |
| Phase 4 Spec | ✅ Complete |
| Phase 5 Spec | ✅ Complete |
| Chain-of-Verification (all phases) | ✅ Complete |
| Test Plans (all phases) | ✅ Complete |
| Changelog | ✅ Complete |
| Development | ⬜ Not Started |

---

## Key Decisions Made

1. **Tech Stack:** React + TypeScript + Tailwind (frontend), Python + FastAPI (backend), PostgreSQL + Redis + S3 (data), Claude API (AI), SendGrid (email)
2. **Representation Sides:** buyer, seller, dual (added dual after CoV #00)
3. **Email Strategy:** SendGrid primary with agent's email as Reply-To; Gmail/Outlook direct send is future enhancement
4. **Agent Approval Required:** No fully autonomous emails in V1. Agent always previews and approves.
5. **Cash Transactions:** Conditional workflows — no lender emails, no appraisal/financing milestones
6. **Inspection Costs:** Framed as "estimated ranges" with disclaimers, not professional quotes
7. **Launch State:** Alabama first, then expand to GA, FL, MS, LA, TX
8. **Timeline:** 20 weeks across 5 phases
9. **Inspection Safety:** Mandatory safety category review even when no issues found

---

## Chain-of-Verification Summary

| CoV | Phase | Key Findings | Resolution |
|-----|-------|-------------|------------|
| #00 | Scope | Dual agency missing; cash transactions not handled; multi-party naming; non-standard contracts; mid-transaction changes | Added dual representation; conditional workflows; multi-party support; contract type detection; amendment tracking |
| #01 | Phase 1 | Scanned PDFs; partial execution; API failures; rate limits; multi-file contracts | Vision fallback; execution detection; retry logic; 429 handling; single-file for V1 |
| #02 | Phase 2 | Missing emails; double-send; SendGrid down; legal compliance; reply handling | Email validation; idempotency keys; queued retry; mandatory preview; Reply-To config |
| #03 | Phase 3 | Celery reliability; timezones; out-of-order milestones; reminder fatigue; duplicate completion | Redis AOF; UTC storage; state-based logic; configurable reminders; idempotent completion |
| #04 | Phase 4 | Cost accuracy; unusual formats; missed safety items; liability; poor OCR | Disclaimer framing; format detection; safety checklist; agent-in-loop; vision fallback |
| #05 | Phase 5 | Generic emails; rollback plan; feature requests; unknown formats; scale | Tone preferences; blue-green deploy; feedback triage; log + iterate; pagination |

---

## Open Questions (For Development Start)

1. **Hosting provider decision** — AWS vs. GCP vs. DigitalOcean? (Recommendation: AWS for S3 + RDS + ECS ecosystem)
2. **Clerk vs. Auth0** — Final auth provider selection
3. **Domain name** — What domain for the platform and email sending?
4. **SendGrid plan** — Free tier (100/day) sufficient for beta, need paid ($20+/mo) for launch
5. **Beta agent recruitment** — Who are the 3-5 agents for beta testing?
6. **Alabama contract samples** — Need 5+ real (redacted) contracts for parser testing
7. **Inspection report samples** — Need 3+ real inspection reports for analyzer testing

---

## Document Inventory

```
ttc-docs/
├── PRD.md                                    — Product Requirements Document (v2.0)
├── CHANGELOG.md                              — Version history
├── phases/
│   ├── PHASE_1_Foundation_Contract_Parsing.md — Weeks 1-4
│   ├── PHASE_2_Communications_Engine.md       — Weeks 5-8
│   ├── PHASE_3_Milestone_Tracking.md          — Weeks 9-12
│   ├── PHASE_4_Inspection_Analysis.md         — Weeks 13-16
│   └── PHASE_5_Polish_Launch.md               — Weeks 17-20
├── testing/
│   └── MASTER_TEST_PLAN.md                    — Comprehensive testing strategy
├── memory/
│   ├── COV_00_project_scope.md                — Scope verification
│   └── PROJECT_STATUS.md                      — This file
└── changelogs/
    └── (per-phase changelogs created during development)
```

---

## Metrics Targets (Consolidated)

| Metric | Target |
|--------|--------|
| Contract parse time | < 30 seconds |
| Email generation time | < 15 seconds |
| Inspection analysis time | < 60 seconds |
| AI extraction accuracy | ≥ 90% |
| Safety item detection | ≥ 95% |
| Email delivery rate | ≥ 98% |
| Email open rate | > 80% |
| Page load times | < 2 seconds |
| System uptime | ≥ 99.5% |
| Agent time saved per transaction | 6+ hours |
| Agent satisfaction | ≥ 4.5 / 5.0 |
