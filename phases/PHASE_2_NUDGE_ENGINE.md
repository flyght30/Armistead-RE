# Phase 2: Nudge Engine — Automated Reminders, Escalation & Email Delivery

## 1. Phase Overview

**Goal:** Wire up real email delivery via Resend and build an automated reminder system with escalation chains that keeps deals on track without the agent remembering anything. Phase 1 gave agents a Today View, milestone templates, action items, and a health score. Phase 2 makes those milestones actionable by automatically nudging parties when deadlines approach, escalating when milestones go overdue, generating AI-drafted emails with agent preview/approval, and giving agents full control over notification frequency and tone.

**Timeline:** Weeks 4-6

**Key Deliverables:**
- **Email Delivery via Resend** — Replace the stubbed `email_sender.py` with real email delivery using the Resend REST API. Track delivery lifecycle (sent, delivered, opened, clicked, bounced, complained) via Resend webhooks. All outbound emails use an authenticated sending domain with SPF/DKIM. Reply-To is set to the agent's personal email so replies land in their inbox.
- **Celery Beat Reminder Jobs** — Hourly scheduled task (`check_milestone_reminders`) that scans all active transactions for upcoming and overdue milestones and creates notification drafts or auto-sends reminders based on agent preferences. A separate `send_queued_emails` task runs every 5 minutes to process the send queue with rate limiting. A `generate_daily_digest` task runs once per day per timezone to consolidate notifications for parties who prefer digests.
- **Escalation Chains** — A four-level escalation system (L0-L3) that progressively increases urgency when milestones remain overdue. L0 is a friendly due-day notice to the responsible party. L1 adds the agent as CC after 1 day. L2 sends a direct urgent email to the agent after 3 days. L3 notifies all parties on the transaction and flags the deal as critical after 7 days. Escalation timing is configurable per agent.
- **Email Composer AI** — Claude-powered contextual email generation that considers milestone type, recipient role, transaction context, prior communication history, and agent tone preferences. Uses Haiku for standard reminders and Sonnet for escalations and custom emails. Learns from agent edits over time.
- **Notification Preferences** — Per-agent approval modes (Preview All, Auto-send Reminders, Full Auto) with a mandatory first-of-type approval mechanism. Per-party email frequency controls (every milestone, daily digest, weekly summary, none). Per-transaction overrides for pausing or adjusting reminder behavior. Vacation mode with backup contact delegation.

---

## 2. Chain of Verification (CoV)

Critical questions that could cause this phase to fail, with risk assessment and resolution strategies.

| # | Question | Risk | Resolution |
|---|----------|------|------------|
| 1 | What if the email provider (Resend) goes down or is unreachable during a critical reminder window? | High — emails fail silently; the agent thinks reminders went out but they did not. Deals slip without anyone noticing. | Queue all emails in Redis via Celery with persistent delivery. Retry with exponential backoff: 30s, 2m, 8m, 30m, 2h. After 5 consecutive failures for a single email, mark the notification_log entry as `failed` and create an action item for the agent in the Today View: "Email to [party name] failed to send — please follow up manually." Log all failures to `notification_log` with `error_message` and `retry_count`. Add a Resend health check to the `/api/health` endpoint. If Resend is down for 30+ minutes, show a banner in the UI: "Email delivery is temporarily delayed. We will retry automatically." |
| 2 | What if an agent has not reviewed their draft queue and pending emails pile up over a weekend? | High — agent returns Monday to find 30+ draft emails. Overwhelmed, they ignore all of them, defeating the purpose of the system. | Cap pending drafts per transaction at 5. When a new reminder would create a 6th draft for the same transaction, update the most recent pending draft for that milestone with refreshed content and bump its `scheduled_for` timestamp instead of creating another entry. Show a consolidated "X pending communications" badge in the NotificationBellBadge, not individual toasts per draft. Add a "Review All" batch approval queue that presents drafts one at a time with Approve/Edit/Reject/Skip and an "Approve All Remaining" shortcut. Drafts auto-expire after 48 hours if not acted on — the next `check_milestone_reminders` run will create fresh drafts with updated context if the milestone is still relevant. |
| 3 | What about Resend API rate limits — what if an agent has 30 transactions all needing reminders on the same day? | High — Resend starter plans allow 10 emails/second. Sending 30+ emails in a burst causes 429 errors. Emails are rejected or delayed unpredictably. | Implement a token bucket rate limiter in the `send_queued_emails` Celery task. Default: 2 emails/second with burst capacity of 10. Spread reminders across the hourly window rather than batching at the top of the hour. Use Celery's `rate_limit` parameter on the individual send subtask. If Resend returns 429, use exponential backoff and re-queue. Prioritize sends by urgency: escalation L2+ first, then overdue, then due-today, then upcoming reminders. This ensures the most critical emails go out first even under rate pressure. |
| 4 | How do we prevent notification fatigue for parties who receive reminders across multiple transactions with the same agent? | High — a lender working on 5 deals with the same agent gets 5 separate reminder emails on the same day. They start ignoring all emails from the system, including critical ones. | Per-party `notification_preference` column: `every_milestone`, `daily_digest`, `weekly_summary`, or `none`. Default for professional parties (lenders, attorneys, title companies) is `daily_digest`. Default for clients (buyers, sellers) is `every_milestone`. Daily digest consolidates all pending items across all transactions into a single email, grouped by transaction with a summary table. Add a `notification_cooldown_hours` field per party (default: 24h) to prevent re-sending to the same email address within the cooldown window even for `every_milestone` parties. The cooldown is per-party, not per-milestone, so a party with 3 milestones due today gets at most one email (or one digest). |
| 5 | What if a party's email address hard-bounces — do we keep trying to send? | High — repeated sends to hard-bounced addresses waste send quota, damage the sending domain's reputation score, and can trigger Resend account suspension. Soft bounces may resolve on their own. | On hard bounce (Resend webhook `email.bounced` with `bounce_type: hard`): immediately mark `parties.email_bounced = true` and `parties.bounced_at = NOW()`. Stop all future automated sends to that address. Create an action item for the agent: "Email for [party name] ([email]) bounced. Please verify their email address and update it." On soft bounce: retry up to 3 times over 24 hours with increasing delays. If all soft bounce retries fail, treat as a hard bounce. Track overall bounce rate per agent; if it exceeds 5% across all sends in a 30-day window, show a settings warning: "Your email bounce rate is high. Please review party email addresses." |
| 6 | What timezone should reminders use — the agent's or the party's? And what happens when the hourly check fires at 3 AM? | Medium — a reminder scheduled for "2 days before due date" fires at midnight UTC, which is 7 PM the previous day in Eastern Time. The party gets a confusing early reminder. Emails arriving at 3 AM look automated and unprofessional. | All milestone `due_date` values are dates (date-level precision). The reminder scheduler resolves "2 days before" relative to the agent's configured timezone. Reminders are only sent during business hours in the agent's timezone (default: 9:00 AM to 6:00 PM). If the `check_milestone_reminders` task identifies a reminder that needs to go out but the current time is outside business hours, it creates the `notification_log` entry with `scheduled_for` set to the next business hour opening (e.g., 9:00 AM the next business day). Store `timezone` on the `users` table (default: `America/New_York`). Business hours are configurable per agent in `notification_preferences`. Weekend sends are suppressed by default unless the agent enables "Send on weekends" in preferences. |
| 7 | How do we handle the "first send" approval requirement — the agent must preview before the system auto-sends any new email type? | High — if the system auto-sends an AI-generated email type the agent has never reviewed, the content could be embarrassing, incorrect, or misrepresent the agent's tone. One bad email destroys trust in the system. | Track `approved_email_types[]` in `users.notification_preferences` JSONB. Email types are: `reminder`, `due_today`, `overdue_l0`, `overdue_l1`, `overdue_l2`, `overdue_l3`, `daily_digest`, `status_update`, `congratulations`. When the system generates an email of a type NOT in the agent's `approved_email_types`, it MUST create an `email_draft` regardless of the agent's `approval_mode` setting. Even an agent in `full_auto` mode must approve the first instance of each type. After the agent approves and sends the first instance, that type is added to `approved_email_types`. Subsequent emails of that type follow the agent's configured `approval_mode`. This means a new agent will need to approve ~9 drafts total before the system is fully autonomous. The UI explains this: "You need to approve the first email of each type so we learn your preferences." |
| 8 | What if the Celery worker crashes mid-batch — are emails double-sent? | High — worker processes 15 of 30 queued emails, crashes, restarts, and re-processes the first 15. Parties receive duplicate reminders. This erodes trust and looks unprofessional. | Three-layer protection: (1) Idempotency keys. Before creating any notification_log entry, compute a deterministic key: `{milestone_id}:{recipient_email}:{type}:{date}`. The `idempotency_key` column has a UNIQUE constraint, so duplicate inserts are rejected at the database level. (2) Atomic status transitions. The `send_queued_emails` task updates status to `sending` BEFORE calling the Resend API, and to `sent` AFTER. If the worker dies between `sending` and `sent`, the entry stays as `sending`. On restart, a recovery sweep finds entries stuck in `sending` for 5+ minutes and checks Resend's API to see if the email was actually delivered. If yes, update to `sent`. If not, reset to `queued` for retry. (3) Resend idempotency key parameter. Pass the `notification_log.id` as Resend's idempotency key so even if we call their API twice with the same key, only one email is sent. |
| 9 | What about CAN-SPAM and GDPR compliance for automated emails? | High — automated emails without unsubscribe links violate CAN-SPAM Act. Potential legal liability and Resend account suspension. | Every automated email includes in the footer: (1) the agent's full name and license number, (2) the brokerage's physical mailing address, (3) the brokerage name, (4) a one-click unsubscribe link: `https://app.armistead.re/unsubscribe/{token}` where the token is a per-party UUID stored in `parties.unsubscribe_token`. The unsubscribe page (public, no auth required) lets the party choose: reduce frequency (daily digest, weekly summary) or fully opt out. Unsubscribed parties are NEVER emailed again by the automated system unless the agent manually overrides in the UI (with a confirmation warning: "This party has opted out of automated emails. Send manually?"). The `unsubscribe_token` is generated at party creation and never expires. Store `unsubscribed_at` on the party record. The system also respects Resend's `List-Unsubscribe` header for one-click unsubscribe in Gmail/Apple Mail. |
| 10 | What if the agent is on vacation — who handles escalating milestones? | Medium — escalation emails CC the agent, but the agent is not checking email. Milestones continue to slide with no one intervening. | Add `vacation_mode` boolean and `vacation_end_date` to `users.notification_preferences`. When enabled: (a) all automated sends are paused and converted to drafts (they accumulate but are not sent), (b) escalation Level 2+ emails CC a designated `backup_email` address (stored in preferences), (c) the Today View shows a prominent yellow banner: "Vacation mode is ON — automated sends are paused until [date]", (d) the daily digest (if applicable) is sent to the backup contact instead. If no backup contact is configured, the system warns the agent before they can enable vacation mode: "You should designate a backup contact before enabling vacation mode." Vacation mode auto-disables at midnight on `vacation_end_date`. If no end date is set, it auto-disables after 14 days with a warning email to the agent. |
| 11 | What about reply-to handling — where do replies to automated emails go? Will parties be confused by the sender address? | Medium — party replies to a reminder and the reply goes to `noreply@armistead.re`. The agent never sees it. The party thinks they responded and the agent thinks there has been no communication. | All automated emails use `From: "[Agent Name] via Armistead RE" <noreply@armistead.re>` (authenticated domain for deliverability) with `Reply-To: [agent's personal email]`. This means all replies land directly in the agent's personal inbox. The system does not intercept, process, or store replies. The email footer states: "Reply directly to this email to reach [Agent Name]." This is transparent — the agent manages reply conversations in their own email client. Future enhancement (not Phase 2): Resend inbound email routing could capture replies and log them as communications in the transaction timeline. |
| 12 | How do we handle the case where a milestone is completed between when a reminder is generated and when it is actually sent? | Medium — an email goes out saying "your inspection is due in 2 days" but the inspection was already completed an hour ago. The party is confused and the agent looks disorganized. | The `send_queued_emails` task performs a pre-send validation check immediately before calling the Resend API for each email. It re-queries the milestone status. If the milestone is now `completed`, `waived`, or `cancelled`, the queued notification is set to status `cancelled` with reason "Milestone completed before send" and the email is NOT sent. This adds ~1 database query per email but prevents stale reminders. The same check verifies that the recipient party has not been removed from the transaction and that their email has not bounced since the notification was queued. |

---

## 3. Detailed Requirements

### 3.1 Email Delivery Service (Resend Integration)

**Primary Provider: Resend**

Resend is selected for its modern REST API, built-in delivery tracking via webhooks, excellent developer documentation, React Email template support, and competitive pricing. The implementation uses a provider abstraction layer (`EmailDeliveryService`) so switching to SendGrid, Postmark, or another provider requires changing only the delivery adapter — all business logic remains unchanged.

**Sending Identity Configuration:**

```
From:       "[Agent Name] via Armistead RE" <noreply@armistead.re>
Reply-To:   [agent's personal email address from users.email]
```

The `From` address uses the application's verified domain for SPF/DKIM authentication. The `Reply-To` ensures all replies go to the agent's personal inbox. The agent's name appears in the `From` display name so the party sees a familiar name.

**Delivery Pipeline (6 stages):**

1. **Content Generation** — Email content is generated by the EmailComposerAgent (AI) or rendered from an HTML template (for digests). The output is stored in the `email_drafts` table with status `draft`.
2. **Agent Approval** — The agent reviews the draft in the EmailPreviewModal. They can edit the subject and body, then approve or reject. If the agent's `approval_mode` is `auto_send_reminders` or `full_auto` AND the email type has been previously approved, this step is skipped — the draft is auto-approved and the system proceeds directly to step 3.
3. **Queue** — The approved email is recorded in `notification_log` with status `queued` and a `scheduled_for` timestamp that respects the agent's business hours and timezone. If the current time is within business hours, `scheduled_for` is set to NOW(). If outside business hours, it is set to the next business hour opening.
4. **Send** — The `send_queued_emails` Celery task picks up entries where `status = 'queued'` AND `scheduled_for <= NOW()`. It performs pre-send validation, then calls the Resend API. On success, status updates to `sent` and the `resend_message_id` is stored.
5. **Track** — Resend fires webhook events (`email.delivered`, `email.opened`, `email.clicked`, `email.bounced`, `email.complained`). The `POST /api/webhooks/email` endpoint receives these events and dispatches to the `process_email_webhook` Celery task, which updates `notification_log` and `communications` status.
6. **Archive** — Sent emails are also recorded in the `communications` table for the transaction communication log. This ensures all emails (manual and automated) appear in a single timeline on the transaction detail page.

**Retry & Fallback Matrix:**

| Scenario | Behavior | Max Retries | Backoff |
|----------|----------|-------------|---------|
| Resend API timeout (>10s) | Retry immediately once, then re-queue with backoff | 5 | 30s, 2m, 8m, 30m, 2h |
| Resend 429 (rate limit) | Exponential backoff, re-queue | 5 | 30s, 2m, 8m, 30m, 2h |
| Resend 5xx (server error) | Retry with exponential backoff | 5 | 30s, 2m, 8m, 30m, 2h |
| Resend hard bounce webhook | Stop all future sends to that address, mark party as bounced, create agent action item | 0 | N/A |
| Resend soft bounce webhook | Retry send over 24 hours | 3 | 1h, 6h, 24h |
| All retries exhausted | Status `failed`, create agent action item: "Email to [name] failed after 5 attempts" | 0 | N/A |

**Delivery Status Tracking via Webhooks:**

| Resend Event | System Action |
|-------------|---------------|
| `email.sent` | Update `notification_log.status` = `sent`, record `sent_at` |
| `email.delivered` | Update status = `delivered`, record `delivered_at` |
| `email.opened` | Update status = `opened` (only if current status is `delivered` or `sent` — do not downgrade from `clicked`), record `opened_at` |
| `email.clicked` | Record `clicked_at` timestamp on `notification_log`. Do not change status. |
| `email.bounced` | Update status = `bounced`, record `bounced_at` and `bounce_reason`. Handle per hard/soft bounce logic described above. |
| `email.complained` | Update status = `complained`. Auto-unsubscribe the party: set `parties.unsubscribed_at = NOW()`. Create agent action item: "[party name] marked your email as spam. They have been automatically unsubscribed." |

**HTML Email Template Requirements:**

All outbound emails are rendered through a single base HTML template with content slots. The template must:

- Be responsive (renders correctly in Gmail, Outlook 2016+, Apple Mail, Yahoo Mail, and iOS Mail)
- Use inline CSS (Outlook does not support `<style>` blocks reliably)
- Include a clean header area with optional brokerage logo (configurable per agent in settings, default: Armistead RE logo)
- Include a body content section populated by AI-generated or template-generated content
- Include an agent signature block: agent name, title, brokerage name, license number, phone number, email address
- Include a footer with: brokerage physical mailing address, "Sent via Armistead RE" text, CAN-SPAM unsubscribe link
- The unsubscribe link uses a unique per-party token: `https://app.armistead.re/unsubscribe/{unsubscribe_token}`
- Include `List-Unsubscribe` and `List-Unsubscribe-Post` headers for one-click unsubscribe support in Gmail and Apple Mail

### 3.2 Automated Reminder System (Celery Beat)

**Celery Beat Schedule:**

```python
CELERY_BEAT_SCHEDULE = {
    'check-milestone-reminders': {
        'task': 'app.tasks.check_milestone_reminders',
        'schedule': crontab(minute=0),              # Every hour, on the hour
    },
    'send-queued-emails': {
        'task': 'app.tasks.send_queued_emails',
        'schedule': crontab(minute='*/5'),           # Every 5 minutes
    },
    'generate-daily-digests': {
        'task': 'app.tasks.generate_daily_digest',
        'schedule': crontab(hour='8,9,10,11,12,13', minute=0),
                                                     # Hourly 8AM-1PM UTC to catch
                                                     # all US timezones at ~9AM local
    },
    'expire-stale-drafts': {
        'task': 'app.tasks.expire_stale_drafts',
        'schedule': crontab(hour=0, minute=30),      # Daily at 12:30 AM UTC
    },
}
```

**Reminder Check Logic (pseudocode for `check_milestone_reminders`):**

```
FOR each agent with at least one active transaction:
    IF agent.vacation_mode == true:
        SKIP all transactions for this agent
        CONTINUE

    FOR each active transaction (status IN ['active', 'confirmed']):
        ACQUIRE Redis distributed lock: "reminder_lock:{transaction_id}" (TTL=5min)
        IF lock not acquired:
            SKIP (another worker is handling this transaction)
            CONTINUE

        LOAD agent's notification_preferences and notification_rules
        RESOLVE agent's local date/time from their timezone setting

        FOR each milestone WHERE status NOT IN ('completed', 'waived', 'cancelled'):
            days_until_due = milestone.due_date - agent_local_today
            rule = FIND matching notification_rule (specific milestone.type first, then '*')
            threshold = rule.days_before OR agent.default_reminder_days

            IF days_until_due > 0 AND days_until_due <= threshold:
                -- UPCOMING REMINDER
                idempotency_key = "{milestone_id}:{party_email}:reminder:{today_date}"
                IF notification_log entry exists with this key: SKIP
                IF party.email_bounced OR party.unsubscribed_at IS NOT NULL: SKIP
                IF party.notification_preference == 'daily_digest': ADD to digest queue, SKIP
                IF party.notification_preference == 'none': SKIP

                IF agent.approval_mode == 'preview_all'
                   OR 'reminder' NOT IN agent.approved_email_types:
                    CREATE email_draft (AI-generated, status='draft')
                ELSE:
                    CREATE notification_log (status='queued',
                        scheduled_for=next_business_hour(agent.timezone))

            ELSE IF days_until_due == 0:
                -- DUE TODAY NOTICE
                (same logic as above but with type='due_today' and more urgent tone)

            ELSE IF days_until_due < 0:
                -- OVERDUE: delegate to EscalationService
                days_overdue = abs(days_until_due)
                IF milestone.reminders_paused_until > NOW(): SKIP
                CALL escalation_service.evaluate(milestone, days_overdue, agent, rule)

        RELEASE distributed lock
```

**Agent Approval Modes:**

| Mode | Behavior | Recommended For |
|------|----------|-----------------|
| `preview_all` | Every email is created as a draft in `email_drafts`. The agent must review, optionally edit, and explicitly approve before the system sends anything. | New agents (first 30 days), agents who want maximum control |
| `auto_send_reminders` | Standard upcoming reminders and due-today notices auto-send (if the type has been previously approved). Overdue L2+, custom emails, and first-of-type emails still require approval. | Agents who have approved at least 10 emails and are comfortable with the system's output |
| `full_auto` | All emails auto-send after first-of-type approval. The agent receives a daily summary of what was sent. | Experienced agents who fully trust the system (opt-in only, requires explicit confirmation) |

**First-of-Type Approval Mechanism:**

Regardless of approval mode, the FIRST email of each type that the system generates for a specific agent MUST be created as a draft for manual review and approval. The email types tracked are:

- `reminder` — standard upcoming milestone reminder
- `due_today` — milestone due today notice
- `overdue_l0` — Level 0 overdue notice (due day)
- `overdue_l1` — Level 1 escalation (1 day overdue)
- `overdue_l2` — Level 2 escalation (3 days overdue)
- `overdue_l3` — Level 3 critical escalation (7 days overdue)
- `daily_digest` — daily summary email for digest-preference parties
- `status_update` — milestone completion notification
- `congratulations` — closing day email

After the agent approves and the email sends successfully, the type is appended to `notification_preferences.approved_email_types[]`. All future emails of that type follow the agent's configured `approval_mode`. This ensures agents always see and validate the AI's output for each category before trusting it to auto-send.

### 3.3 Escalation Chains

Escalation is triggered when a milestone has a `due_date` in the past and its status is not `completed`, `waived`, or `cancelled`. The escalation level is determined by how many days the milestone has been overdue and is tracked on `milestones.escalation_level`.

**Escalation Levels:**

| Level | Trigger (Default Days Overdue) | Recipients | Email Tone | Additional System Actions |
|-------|-------------------------------|------------|------------|--------------------------|
| **L0** | Due date arrives (0 days overdue) | Responsible party only | Friendly reminder. "Just a reminder that [milestone] is due today for [property address]." | None — standard due-today notice |
| **L1** | 1 day overdue | Responsible party + CC agent | Firmer follow-up. "This was due yesterday. Please provide an update at your earliest convenience." | Agent receives an action item in Today View |
| **L2** | 3 days overdue | Responsible party + agent receives a direct separate email | Urgent. "This is now 3 days overdue and may impact the closing timeline. Please prioritize." | Transaction health score receives extra penalty. Action item priority upgraded to HIGH. Notification bell badge turns red. Email always requires agent approval regardless of mode. |
| **L3** | 7 days overdue | All parties on the transaction + agent receives critical alert | Critical. "[Milestone] for [property address] is significantly overdue. All parties are being notified to ensure this is resolved immediately." | Transaction health score drops to critical zone. Today View shows a prominent red banner for this transaction. If `backup_email` is configured, backup contact is CC'd. |

**Configurable Escalation Timing:**

Each agent can customize the escalation trigger days via `notification_rules.escalation_days[]` (default: `[1, 3, 7]`). Examples:

- Fast-moving deals: `[1, 2, 4]` — escalate more aggressively
- Patient agents: `[2, 5, 10]` — more time before each level
- No escalation: set `escalation_enabled = false` on the notification rule

**Escalation Pause & Reset:**

- Agent marks milestone as `in_progress` — resets `escalation_level` to 0 and sets `reminders_paused_until` to 48 hours from now
- Agent marks milestone as `waived` — stops all escalation permanently for that milestone
- Agent manually sends a communication about the milestone — resets the escalation timer by setting `reminders_paused_until` to `NOW() + 48 hours`
- Agent enables vacation mode — pauses all automated sends (but escalation level tracking continues so the system picks up at the right level when vacation mode ends)

### 3.4 Email Composer AI (Claude Integration)

The email composer uses Claude to generate contextual, role-appropriate email drafts. Model selection is based on email complexity:

| Email Type | Model | Reasoning |
|-----------|-------|-----------|
| Standard upcoming reminder | Claude Haiku | High volume, formulaic content, cost-sensitive |
| Due today notice | Claude Haiku | Similar to reminder but with urgency adjustment |
| Overdue L0, L1 | Claude Haiku | Still relatively standard content |
| Overdue L2, L3 | Claude Sonnet | Higher stakes, needs nuanced tone escalation |
| Custom email (agent-initiated) | Claude Sonnet | Freeform content needs higher quality |
| Congratulations / closing day | Claude Sonnet | Personal milestone, should feel genuine |
| Daily digest | Template-based (no AI) | Structured data table, no need for AI |

**System Prompt for Email Generation:**

```
You are a professional real estate email composer for Armistead RE.
You write clear, warm, and action-oriented emails for real estate
transaction coordination.

CONTEXT PROVIDED:
- Milestone type, title, due date, and status
- Recipient's name, role, company, and relationship to the transaction
- Transaction details: property address, key dates, purchase price, financing type
- Agent's name, brokerage, license number, and contact information
- Agent's tone preference: professional | friendly | casual
- Escalation level (0-3) indicating urgency
- Previous communications sent for this milestone (to avoid repetition)
- Agent's style_notes (learned preferences from prior edits)

RULES:
1. Match the agent's tone preference exactly.
2. Be specific: always include the milestone name, due date, and property address.
3. Include a clear call-to-action: what does the recipient need to DO?
4. For overdue emails, increase urgency with each escalation level but never
   be rude, threatening, or passive-aggressive.
5. For reminders to clients (buyers/sellers): warm, reassuring, supportive.
6. For reminders to professionals (lenders, attorneys, title companies): direct,
   factual, respectful of their expertise.
7. Never include financial details (purchase price, earnest money) in emails
   to parties who should not have that information.
8. Never reveal information about other parties' private communications.
9. Keep emails concise: 2-4 paragraphs maximum for reminders, 3-5 for escalations.
10. Subject line must include the property address and be under 80 characters.
11. End with the agent's name (signature block is appended separately).

OUTPUT FORMAT (JSON):
{
  "subject": "string",
  "body_html": "string (semantic HTML, no inline styles — template handles styling)",
  "body_text": "string (plain text fallback)",
  "tone_used": "professional | friendly | casual",
  "urgency_level": "low | medium | high | critical"
}
```

**Learning from Agent Edits:**

When an agent edits an AI-generated draft before approving:

1. Store the original AI draft in `email_drafts.original_ai_content` alongside the agent's edited version.
2. After the agent has edited 5+ emails of the same type, analyze the edit patterns: tone adjustments, preferred phrases, removed sections, added sign-off styles.
3. Update `notification_preferences.style_notes` with a natural-language summary of the agent's preferences (e.g., "Agent prefers to use first names. Agent always includes a phone number invitation. Agent removes urgency language from L1 escalations.").
4. Include `style_notes` in future AI prompts for that agent, resulting in progressively better drafts that require fewer edits.
5. If an agent saves an edited email as a reusable template (via a "Save as Template" button in the EmailPreviewModal), the system prioritizes that template over AI generation for future emails of that type and milestone category.

### 3.5 Notification Preferences

**Per-Agent Settings (stored in `users.notification_preferences` JSONB):**

```json
{
  "approval_mode": "preview_all",
  "default_reminder_days": 2,
  "escalation_enabled": true,
  "escalation_days": [1, 3, 7],
  "tone_preference": "professional",
  "timezone": "America/New_York",
  "business_hours_start": "09:00",
  "business_hours_end": "18:00",
  "send_on_weekends": false,
  "vacation_mode": false,
  "vacation_end_date": null,
  "backup_email": null,
  "approved_email_types": [],
  "style_notes": "",
  "daily_summary_enabled": true,
  "send_copy_to_self": false
}
```

**Per-Party Settings (stored on `parties` table):**

| Setting | Column | Options | Default |
|---------|--------|---------|---------|
| Notification frequency | `notification_preference` | `every_milestone`, `daily_digest`, `weekly_summary`, `none` | `every_milestone` for clients; `daily_digest` for professionals |
| Cooldown period | `notification_cooldown_hours` | Integer (1-168) | 24 |
| Bounce status | `email_bounced` | Boolean | false |
| Unsubscribe status | `unsubscribed_at` | Timestamp or null | null |

**Per-Transaction Overrides:**

Agents can customize notification behavior at the transaction level via a JSONB column `transactions.notification_overrides`:

```json
{
  "reminders_enabled": true,
  "reminder_days_override": null,
  "party_overrides": {
    "<party_id>": {
      "notification_preference": "none"
    }
  }
}
```

- `reminders_enabled: false` — disables all automated reminders for this transaction (useful for deals on hold)
- `reminder_days_override` — overrides the agent's default and the rule's `days_before` for this specific transaction
- `party_overrides` — per-party preference overrides scoped to this transaction only

---

## 4. Data Model

### New Tables

```sql
-- Notification rules: define when/how reminders fire for milestone types
notification_rules:
  id UUID PK DEFAULT gen_random_uuid()
  agent_id UUID NOT NULL FK -> users(id) ON DELETE CASCADE
  milestone_type VARCHAR(50) NOT NULL       -- specific type ('inspection', 'closing') or '*' for all
  days_before INTEGER NOT NULL DEFAULT 2    -- days before due_date to send first reminder
  auto_send BOOLEAN NOT NULL DEFAULT false  -- bypass draft queue (subject to approval_mode + first-of-type)
  recipient_roles TEXT[] NOT NULL DEFAULT '{}'
      -- array of party roles to notify; empty = responsible_party_role only
  escalation_enabled BOOLEAN NOT NULL DEFAULT true
  escalation_days INTEGER[] NOT NULL DEFAULT '{1, 3, 7}'
      -- days overdue at which each escalation level triggers [L1, L2, L3]
  template_id UUID FK -> email_templates(id) ON DELETE SET NULL
      -- optional: use specific template instead of AI generation
  is_active BOOLEAN NOT NULL DEFAULT true
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

  INDEXES:
    idx_notification_rules_agent ON (agent_id)
    idx_notification_rules_type ON (milestone_type)
    UNIQUE idx_notification_rules_agent_type ON (agent_id, milestone_type) WHERE is_active = true

-- Notification log: audit trail for every notification attempt and lifecycle
notification_log:
  id UUID PK DEFAULT gen_random_uuid()
  transaction_id UUID NOT NULL FK -> transactions(id) ON DELETE CASCADE
  milestone_id UUID FK -> milestones(id) ON DELETE SET NULL
  communication_id UUID FK -> communications(id) ON DELETE SET NULL
  rule_id UUID FK -> notification_rules(id) ON DELETE SET NULL
  draft_id UUID FK -> email_drafts(id) ON DELETE SET NULL
  type VARCHAR(50) NOT NULL
      -- reminder, due_today, overdue, escalation, status_update,
      -- daily_digest, congratulations, custom
  escalation_level INTEGER NOT NULL DEFAULT 0
      -- 0=standard, 1=follow-up, 2=urgent, 3=critical
  recipient_email VARCHAR(200) NOT NULL
  recipient_name VARCHAR(200)
  recipient_role VARCHAR(30)
  subject VARCHAR(500)
  status VARCHAR(30) NOT NULL DEFAULT 'pending'
      -- pending, draft, queued, sending, sent, delivered,
      -- opened, clicked, bounced, failed, cancelled, complained
  resend_message_id VARCHAR(200)
      -- Resend's message ID for webhook event correlation
  scheduled_for TIMESTAMPTZ
      -- when the email should actually be sent (respects business hours)
  sent_at TIMESTAMPTZ
  delivered_at TIMESTAMPTZ
  opened_at TIMESTAMPTZ
  clicked_at TIMESTAMPTZ
  bounced_at TIMESTAMPTZ
  bounce_reason TEXT
  error_message TEXT
  retry_count INTEGER NOT NULL DEFAULT 0
  idempotency_key VARCHAR(200) UNIQUE
      -- "{milestone_id}:{recipient_email}:{type}:{date}" prevents duplicates
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

  INDEXES:
    idx_notification_log_transaction ON (transaction_id)
    idx_notification_log_milestone ON (milestone_id)
    idx_notification_log_status ON (status)
    idx_notification_log_scheduled ON (scheduled_for) WHERE status IN ('queued', 'pending')
    idx_notification_log_resend ON (resend_message_id) WHERE resend_message_id IS NOT NULL

-- Email drafts: AI-generated or manually composed emails awaiting agent approval
email_drafts:
  id UUID PK DEFAULT gen_random_uuid()
  transaction_id UUID NOT NULL FK -> transactions(id) ON DELETE CASCADE
  milestone_id UUID FK -> milestones(id) ON DELETE SET NULL
  party_id UUID FK -> parties(id) ON DELETE SET NULL
  notification_rule_id UUID FK -> notification_rules(id) ON DELETE SET NULL
  recipient_email VARCHAR(200) NOT NULL
  recipient_name VARCHAR(200)
  recipient_role VARCHAR(30)
  subject VARCHAR(500) NOT NULL
  body_html TEXT NOT NULL
  body_text TEXT
      -- plain text fallback for email clients that do not render HTML
  email_type VARCHAR(50) NOT NULL
      -- reminder, due_today, overdue, escalation, status_update, custom, congratulations
  escalation_level INTEGER NOT NULL DEFAULT 0
  ai_generated BOOLEAN NOT NULL DEFAULT false
  ai_model_used VARCHAR(50)
      -- 'haiku' or 'sonnet' for cost tracking and quality analysis
  original_ai_content TEXT
      -- stores original AI output when agent edits before approving, for learning
  status VARCHAR(30) NOT NULL DEFAULT 'draft'
      -- draft, approved, sent, rejected, expired, cancelled
  approved_at TIMESTAMPTZ
  approved_by UUID FK -> users(id)
  rejected_at TIMESTAMPTZ
  rejected_reason TEXT
  sent_at TIMESTAMPTZ
  expires_at TIMESTAMPTZ
      -- drafts auto-expire after 48 hours if not acted on
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

  INDEXES:
    idx_email_drafts_transaction ON (transaction_id)
    idx_email_drafts_status ON (status) WHERE status = 'draft'
    idx_email_drafts_pending ON (transaction_id, status) WHERE status = 'draft'
```

### Modifications to Existing Tables

```sql
-- Add notification preferences to users
ALTER TABLE users ADD COLUMN notification_preferences JSONB NOT NULL DEFAULT '{
    "approval_mode": "preview_all",
    "default_reminder_days": 2,
    "escalation_enabled": true,
    "escalation_days": [1, 3, 7],
    "tone_preference": "professional",
    "timezone": "America/New_York",
    "business_hours_start": "09:00",
    "business_hours_end": "18:00",
    "send_on_weekends": false,
    "vacation_mode": false,
    "vacation_end_date": null,
    "backup_email": null,
    "approved_email_types": [],
    "style_notes": "",
    "daily_summary_enabled": true,
    "send_copy_to_self": false
}'::jsonb;
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'America/New_York';

-- Add delivery tracking to communications
ALTER TABLE communications ADD COLUMN delivery_status VARCHAR(30);
    -- pending, sent, delivered, opened, bounced, failed, complained
ALTER TABLE communications ADD COLUMN bounce_reason TEXT;
ALTER TABLE communications ADD COLUMN notification_log_id UUID REFERENCES notification_log(id);
CREATE INDEX idx_communications_resend ON communications(resend_message_id)
    WHERE resend_message_id IS NOT NULL;

-- Add escalation tracking to milestones
ALTER TABLE milestones ADD COLUMN IF NOT EXISTS reminder_sent_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE milestones ADD COLUMN IF NOT EXISTS escalation_level INTEGER NOT NULL DEFAULT 0;
ALTER TABLE milestones ADD COLUMN IF NOT EXISTS reminders_paused_until TIMESTAMPTZ;

-- Add notification controls to parties
ALTER TABLE parties ADD COLUMN notification_preference VARCHAR(30) DEFAULT 'every_milestone';
    -- every_milestone, daily_digest, weekly_summary, none
ALTER TABLE parties ADD COLUMN notification_cooldown_hours INTEGER DEFAULT 24;
ALTER TABLE parties ADD COLUMN last_notification_sent_at TIMESTAMPTZ;
ALTER TABLE parties ADD COLUMN email_bounced BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE parties ADD COLUMN bounced_at TIMESTAMPTZ;
ALTER TABLE parties ADD COLUMN unsubscribed_at TIMESTAMPTZ;
ALTER TABLE parties ADD COLUMN unsubscribe_token UUID DEFAULT gen_random_uuid();
CREATE UNIQUE INDEX idx_parties_unsubscribe ON parties(unsubscribe_token);

-- Add notification overrides to transactions
ALTER TABLE transactions ADD COLUMN notification_overrides JSONB DEFAULT '{
    "reminders_enabled": true,
    "reminder_days_override": null,
    "party_overrides": {}
}'::jsonb;
```

---

## 5. API Endpoints

### 5.1 Communications — Send & Draft

```
POST /api/transactions/{transaction_id}/communications/send
     Description: Send an email immediately (bypasses draft queue). Agent-initiated.
     Auth: Required (agent must own transaction)
     Request Body: {
       recipient_email: string (required),
       recipient_party_id: UUID (optional — links to party record),
       subject: string (required),
       body_html: string (required),
       body_text: string (optional — auto-generated from HTML if omitted),
       type: "custom" | "status_update" | "congratulations" (required),
       milestone_id: UUID (optional — links communication to milestone),
       attachments: string[] (optional — S3 URLs)
     }
     Response 201: {
       id: UUID,
       status: "queued",
       scheduled_for: string (ISO datetime),
       notification_log_id: UUID
     }

POST /api/transactions/{transaction_id}/communications/draft
     Description: Generate an AI email draft for a specific milestone and recipient.
     Auth: Required
     Request Body: {
       milestone_id: UUID (required),
       party_id: UUID (required),
       email_type: "reminder" | "due_today" | "overdue" | "custom" (required),
       custom_instructions: string (optional — additional context for AI)
     }
     Response 201: {
       id: UUID,
       subject: string,
       body_html: string,
       body_text: string,
       ai_generated: true,
       ai_model_used: "haiku" | "sonnet",
       status: "draft",
       expires_at: string (ISO datetime)
     }

GET  /api/transactions/{transaction_id}/communications
     Description: List all communications for a transaction.
     Auth: Required
     Query Params:
       - status: "sent" | "delivered" | "opened" | "bounced" | "failed" (optional)
       - type: string (optional)
       - page: integer (default: 1)
       - limit: integer (default: 20)
     Response 200: {
       items: [{
         id: UUID,
         type: string,
         recipient_email: string,
         recipient_name: string,
         subject: string,
         status: string,
         delivery_status: string,
         sent_at: string | null,
         delivered_at: string | null,
         opened_at: string | null,
         clicked_at: string | null,
         milestone: { id: UUID, title: string, due_date: string } | null
       }],
       total: integer,
       page: integer,
       limit: integer
     }
```

### 5.2 Email Drafts

```
GET  /api/email-drafts
     Description: List pending email drafts for the current agent across all transactions.
     Auth: Required
     Query Params:
       - status: "draft" | "approved" | "sent" | "rejected" | "expired" (default: "draft")
       - transaction_id: UUID (optional)
       - page: integer (default: 1)
       - limit: integer (default: 20)
     Response 200: {
       items: [{
         id: UUID,
         transaction_id: UUID,
         milestone_id: UUID | null,
         party_id: UUID | null,
         recipient_email: string,
         recipient_name: string,
         recipient_role: string,
         subject: string,
         body_html: string,
         body_text: string | null,
         email_type: string,
         escalation_level: integer,
         ai_generated: boolean,
         ai_model_used: string | null,
         status: string,
         created_at: string,
         expires_at: string | null,
         transaction: { id: UUID, property_address: string, status: string }
       }],
       total: integer,
       page: integer,
       limit: integer
     }

GET  /api/email-drafts/{draft_id}
     Description: Get a single email draft with full content.
     Auth: Required
     Response 200: { ...full draft object as in list response... }

PATCH /api/email-drafts/{draft_id}
     Description: Edit a draft email (subject and/or body). Stores original AI content for learning.
     Auth: Required
     Request Body: {
       subject: string (optional),
       body_html: string (optional),
       body_text: string (optional)
     }
     Response 200: { ...updated draft... }

POST /api/email-drafts/{draft_id}/approve
     Description: Approve a draft and queue it for sending. Adds email type to approved_email_types.
     Auth: Required
     Request Body: (empty)
     Response 200: {
       id: UUID,
       status: "approved",
       approved_at: string,
       queued_notification_id: UUID
     }

POST /api/email-drafts/{draft_id}/reject
     Description: Reject a draft. It will not be sent.
     Auth: Required
     Request Body: {
       reason: string (optional)
     }
     Response 200: {
       id: UUID,
       status: "rejected",
       rejected_at: string
     }

POST /api/email-drafts/approve-batch
     Description: Approve multiple drafts at once and queue them all for sending.
     Auth: Required
     Request Body: {
       draft_ids: UUID[]
     }
     Response 200: {
       approved: integer,
       failed: integer,
       results: [{ draft_id: UUID, status: "approved" | "error", error: string | null }]
     }
```

### 5.3 Notification Rules

```
GET  /api/notification-rules
     Description: List all notification rules for the current agent.
     Auth: Required
     Response 200: {
       items: [{
         id: UUID,
         agent_id: UUID,
         milestone_type: string,
         days_before: integer,
         auto_send: boolean,
         recipient_roles: string[],
         escalation_enabled: boolean,
         escalation_days: integer[],
         template_id: UUID | null,
         is_active: boolean,
         created_at: string,
         updated_at: string
       }]
     }

POST /api/notification-rules
     Description: Create a new notification rule.
     Auth: Required
     Request Body: {
       milestone_type: string (required),
       days_before: integer (optional, default: 2),
       auto_send: boolean (optional, default: false),
       recipient_roles: string[] (optional, default: []),
       escalation_enabled: boolean (optional, default: true),
       escalation_days: integer[] (optional, default: [1, 3, 7]),
       template_id: UUID (optional)
     }
     Response 201: { ...rule object... }

PATCH /api/notification-rules/{rule_id}
     Description: Update a notification rule. All fields optional.
     Auth: Required
     Request Body: {
       days_before?: integer,
       auto_send?: boolean,
       recipient_roles?: string[],
       escalation_enabled?: boolean,
       escalation_days?: integer[],
       template_id?: UUID | null
     }
     Response 200: { ...updated rule... }

DELETE /api/notification-rules/{rule_id}
     Description: Soft-delete a notification rule (sets is_active = false).
     Auth: Required
     Response 204 (no body)
```

### 5.4 Notification Log

```
GET  /api/notifications
     Description: List notification log entries for the current agent.
     Auth: Required
     Query Params:
       - status: string (optional)
       - transaction_id: UUID (optional)
       - type: string (optional)
       - escalation_level: integer (optional — 0, 1, 2, or 3)
       - page: integer (default: 1)
       - limit: integer (default: 20)
     Response 200: {
       items: [{
         id: UUID,
         transaction_id: UUID,
         milestone_id: UUID | null,
         type: string,
         escalation_level: integer,
         recipient_email: string,
         recipient_name: string | null,
         status: string,
         scheduled_for: string | null,
         sent_at: string | null,
         delivered_at: string | null,
         opened_at: string | null,
         transaction: { id: UUID, property_address: string },
         milestone: { id: UUID, title: string, due_date: string } | null
       }],
       total: integer,
       page: integer,
       limit: integer
     }

GET  /api/notifications/pending-count
     Description: Get counts of items requiring agent attention (for bell badge).
     Auth: Required
     Response 200: {
       pending_drafts: integer,
       queued_sends: integer,
       failed_sends: integer,
       total_requiring_attention: integer
     }
```

### 5.5 Webhooks

```
POST /api/webhooks/email
     Description: Receive webhook events from Resend. Secured via webhook signature.
     Auth: Resend webhook signature verification (not user auth)
     Request Body (from Resend): {
       type: "email.sent" | "email.delivered" | "email.opened" |
             "email.clicked" | "email.bounced" | "email.complained",
       data: {
         email_id: string,
         to: string[],
         subject: string,
         created_at: string
       }
     }
     Response 200: { status: "processed" }
     Response 401: { error: "Invalid webhook signature" }
```

### 5.6 Unsubscribe (Public — No Auth)

```
GET  /api/unsubscribe/{token}
     Description: Show current notification preference for a party. Public endpoint.
     Auth: None (token-based access)
     Response 200: {
       party_name: string,
       current_preference: string,
       options: ["every_milestone", "daily_digest", "weekly_summary", "none"],
       agent_name: string,
       agent_brokerage: string
     }
     Response 404: { error: "Invalid unsubscribe token" }

POST /api/unsubscribe/{token}
     Description: Update notification preference or fully unsubscribe.
     Auth: None (token-based access)
     Request Body: {
       preference: "every_milestone" | "daily_digest" | "weekly_summary" | "none"
     }
     Response 200: {
       status: "updated",
       new_preference: string,
       message: string
     }
```

### 5.7 Agent Notification Preferences

```
GET  /api/settings/notifications
     Description: Get the current agent's notification preferences.
     Auth: Required
     Response 200: {
       approval_mode: string,
       default_reminder_days: integer,
       escalation_enabled: boolean,
       escalation_days: integer[],
       tone_preference: string,
       timezone: string,
       business_hours_start: string,
       business_hours_end: string,
       send_on_weekends: boolean,
       vacation_mode: boolean,
       vacation_end_date: string | null,
       backup_email: string | null,
       approved_email_types: string[],
       daily_summary_enabled: boolean,
       send_copy_to_self: boolean
     }

PATCH /api/settings/notifications
     Description: Update notification preferences. All fields optional.
     Auth: Required
     Request Body: {
       approval_mode?: "preview_all" | "auto_send_reminders" | "full_auto",
       default_reminder_days?: integer,
       escalation_enabled?: boolean,
       escalation_days?: integer[],
       tone_preference?: "professional" | "friendly" | "casual",
       timezone?: string,
       business_hours_start?: string,
       business_hours_end?: string,
       send_on_weekends?: boolean,
       vacation_mode?: boolean,
       vacation_end_date?: string | null,
       backup_email?: string | null,
       daily_summary_enabled?: boolean,
       send_copy_to_self?: boolean
     }
     Response 200: { ...updated preferences... }
```

---

## 6. Frontend Components

### New Pages

- **`NotificationCenter.tsx`** (`/notifications`) — Full-page notification management view with three tabs. **Pending Drafts tab**: list of all email drafts with status `draft`, sorted by urgency (escalation level descending, then due date ascending). Each draft card shows: recipient name/role, subject line, 2-line preview snippet, transaction property address, urgency color indicator (green/yellow/orange/red for L0-L3), age ("created 2h ago"). Clicking a card opens the EmailPreviewModal. **Sent tab**: chronological list of all sent notifications with delivery status icons (checkmark for delivered, eye icon for opened, link icon for clicked, X for bounced, warning for failed). Filterable by transaction, date range, and delivery status. **Failed tab**: emails that failed after all retries. Each entry has a "Retry" button and a "Send Manually" option that opens the compose flow.

- **`NotificationPreferencesPage.tsx`** (`/settings/notifications`) — Settings page for configuring all notification behavior. Sections: (1) **Approval Mode** — radio group with three options, each with a description paragraph explaining the behavior. The `full_auto` option shows a confirmation checkbox: "I understand that emails will be sent without my review." (2) **Default Reminder Timing** — number input for days before due date (1-14), with a tooltip explaining this is the default used when no milestone-specific rule exists. (3) **Escalation Settings** — toggle to enable/disable escalation globally, plus three number inputs for the day thresholds of L1, L2, L3 (with validation that L1 < L2 < L3). (4) **Timezone & Business Hours** — timezone dropdown (common US timezones), start/end time pickers for business hours, "Send on weekends" toggle. (5) **Vacation Mode** — toggle with conditional fields: end date picker, backup email input. Warning if no backup email is set. (6) **Tone Preference** — radio group (Professional, Friendly, Casual) with a sample email snippet rendered below each option so the agent can see the difference. (7) **Daily Summary** — toggle on/off. (8) **Send Copy to Self** — toggle.

### New Components

- **`NotificationBellBadge.tsx`** — Bell icon component placed in the sidebar navigation. Props: none (fetches from `GET /api/notifications/pending-count` via React Query with 30-second polling interval). Displays a numeric badge when `total_requiring_attention > 0`. Badge is orange for pending drafts, red if there are failed sends. Click navigates to `/notifications`. Animates (gentle bounce) when count increases.

- **`EmailPreviewModal.tsx`** — Full-screen modal overlay for reviewing and acting on an email draft. Layout: left column shows metadata (From, To, Reply-To, Subject, Email Type, Escalation Level, AI Model Used, Transaction, Milestone), right column shows the rendered HTML email preview in an iframe-like container. Bottom action bar has four buttons: "Approve & Send" (primary, green), "Edit" (secondary), "Reject" (destructive, red with confirmation), "Skip" (gray, closes modal without action). Edit mode replaces the preview with an inline editor: editable subject input and a rich text body editor (using a lightweight editor like TipTap or Lexical). Shows "AI Generated" badge if `ai_generated = true`. Shows escalation level badge with color coding (L0 green, L1 yellow, L2 orange, L3 red).

- **`BatchApprovalQueue.tsx`** — Streamlined view for reviewing multiple drafts in rapid succession. Shows one draft at a time (same layout as EmailPreviewModal but without the modal frame). Navigation: "Previous" / "Next" arrows. Progress indicator: "Reviewing 3 of 7". Action buttons: "Approve", "Edit" (opens inline editor), "Reject", "Next" (skip without action). At the bottom: "Approve All Remaining" button with a count and confirmation dialog: "Approve and send 4 remaining emails?" When all drafts are reviewed, shows a summary: "Approved: 5, Rejected: 1, Skipped: 1."

- **`MilestoneNotificationHistory.tsx`** — Timeline component embedded in the milestone detail view on the transaction detail page. Shows all notifications sent for this specific milestone in reverse chronological order. Each entry shows: notification type icon, recipient name, subject line, delivery status with timestamp, escalation level badge. Clicking an entry expands to show the full email content. If no notifications have been sent, shows: "No communications sent for this milestone."

- **`PartyNotificationSettings.tsx`** — Inline component rendered within the Party detail card on the transaction detail page. Displays a dropdown for notification preference (Every Milestone / Daily Digest / Weekly Summary / None) that saves on change via `PATCH /api/parties/{id}`. Shows bounce status alert if `email_bounced = true` with an "Update Email" button that opens an edit dialog. Shows unsubscribe notice if `unsubscribed_at` is not null: "This party unsubscribed on [date]. Automated emails will not be sent."

- **`TransactionNotificationOverrides.tsx`** — Component on the transaction detail page (in a "Notifications" sub-tab or section). Toggle to enable/disable all automated reminders for this transaction (with warning: "Disabling reminders means no automated emails will be sent for any milestone on this deal"). Override reminder days input (replaces agent default for this transaction). Per-party override table: shows all parties on the transaction with their current notification preference and an override dropdown.

### Modified Components

- **`Layout.tsx`** (modified) — Add `NotificationBellBadge` to the sidebar navigation, positioned below the main nav items and above the settings link. Add `/notifications` route to the navigation menu. Add `/settings/notifications` to the settings submenu.

- **`TodayView.tsx`** (modified from Phase 1) — Add a "Pending Approvals" section at the top of the page, rendered only when there are email drafts with status `draft`. Section shows a count badge ("3 emails awaiting review") and a compact list of draft summaries: recipient, subject preview, transaction address. Each item has a "Review" button that opens EmailPreviewModal. "Review All" button opens BatchApprovalQueue.

- **`TransactionDetail/index.tsx`** (modified) — Add a "Communications" tab to the transaction detail page showing the full communication log for this transaction. Tab content is a chronological list of all sent/scheduled/failed communications with delivery status indicators. Add notification status icons to the Milestones tab: envelope icon (reminder sent), clock icon (reminder scheduled), warning triangle (escalation active), number badge showing current escalation level.

- **`MilestoneCard.tsx`** (modified from Phase 1) — Add small inline icons indicating notification status: gray envelope (no reminders sent yet), blue envelope (reminder sent), orange clock (reminder scheduled for future), red warning triangle (escalation active with level badge). Show escalation level badge (L1 yellow, L2 orange, L3 red) on overdue milestones.

- **`Settings.tsx`** (modified) — Add a "Notifications" card/link that navigates to `/settings/notifications`.

- **`App.tsx`** (modified) — Add routes: `/notifications` -> `NotificationCenter`, `/settings/notifications` -> `NotificationPreferencesPage`. Add `/unsubscribe/:token` as a public route (no auth layout) -> `UnsubscribePage`.

---

## 7. Definition of Success

Phase 2 is COMPLETE when ALL of these criteria are met:

| # | Success Criteria | Measurement |
|---|-----------------|-------------|
| 1 | Emails actually deliver to recipient inboxes via Resend and do not land in spam | Send test emails to Gmail, Outlook, and Yahoo accounts. Verify inbox placement. Confirm SPF/DKIM pass using email headers. Check Resend dashboard for 98%+ delivery rate. |
| 2 | Milestone reminders fire at the correct time relative to due dates and agent timezone | Create a milestone due in 2 days with `reminder_days_before = 2`. Run the hourly check task. Verify a draft or queued notification is created within 1 hour of threshold crossing. Verify `scheduled_for` is within agent's business hours. |
| 3 | Escalation chain progresses through all four levels (L0-L3) with correct recipients at each level | Create a milestone and let it go overdue. Verify: L0 fires on due date (responsible party only), L1 at +1 day (party + CC agent), L2 at +3 days (party + agent direct email, requires approval), L3 at +7 days (all parties + critical alert). Verify correct recipients at each level. |
| 4 | Agent preview/approval flow works end-to-end for all three approval modes | Test with each mode: (a) `preview_all` — verify all emails become drafts, (b) `auto_send_reminders` — verify approved types auto-send and unapproved types become drafts, (c) `full_auto` — verify all approved types auto-send. Verify first-of-type enforcement across all modes. |
| 5 | Hard bounce handling correctly stops all future sends to that address | Send to an intentionally invalid email. Receive bounce webhook. Verify `parties.email_bounced = true`. Trigger another reminder for the same milestone. Verify zero emails queued for that party. Verify an action item is created for the agent. |
| 6 | Open and click tracking update notification_log correctly via webhooks | Send a test email. Simulate open and click webhooks. Verify `notification_log` status updates to `opened` then `clicked` with correct timestamps within 60 seconds of webhook receipt. |
| 7 | First-of-type approval is enforced regardless of approval mode | Set agent to `full_auto`. Trigger a `reminder` type the agent has never approved. Verify a draft is created (NOT auto-sent). Approve it. Verify `reminder` is added to `approved_email_types`. Trigger another `reminder`. Verify it auto-sends without creating a draft. |
| 8 | Daily digest consolidates correctly for multi-transaction parties | Set two parties to `daily_digest` preference across 3 transactions with upcoming milestones. Run the digest task. Verify each party receives exactly one email containing all relevant milestones grouped by transaction. Verify no empty digests are generated. |
| 9 | Rate limiting prevents Resend API overload under high volume | Queue 50 emails simultaneously. Run `send_queued_emails`. Verify emails are sent at a rate of approximately 2/second. Verify zero Resend 429 errors in application logs. Verify all 50 emails are eventually sent within the expected time window. |
| 10 | Idempotency prevents duplicate sends even after worker crash | Queue 20 emails. Kill the Celery worker after 10 are sent. Restart the worker. Verify the remaining 10 are sent without re-sending the first 10. Verify `notification_log` contains exactly 20 entries with unique idempotency keys. |
| 11 | Vacation mode completely pauses all automated communication | Enable vacation mode. Trigger overdue milestones across multiple transactions. Verify zero emails are sent, zero drafts are created. Disable vacation mode. Verify the next hourly check resumes normal operation and picks up the overdue milestones at the correct escalation level. |
| 12 | Unsubscribe flow works without authentication and permanently stops emails | Navigate to `/unsubscribe/{token}` (no login). Verify party name and current preference are displayed. Change preference to `none`. Trigger a reminder for that party. Verify the reminder task skips the unsubscribed party. |
| 13 | AI-generated emails are contextually correct and role-appropriate | Generate 10+ emails across different types and recipient roles. Manually review each for: correct property address, correct milestone dates, appropriate tone for the recipient role, no leaked private information across party boundaries, clear call-to-action. Target: 90%+ are send-ready without agent edits. |
| 14 | Notification bell badge count is accurate and updates in real-time | Create 5 drafts. Verify badge shows 5. Approve 2 drafts. Verify badge updates to 3 within the polling interval (30 seconds). Reject 1, let 1 expire, approve 1. Verify badge shows 0. |
| 15 | All automated emails include CAN-SPAM compliant footer content | Inspect the raw HTML of 5 different email types (reminder, overdue, escalation, digest, congratulations). Verify all contain: agent name, brokerage name, brokerage physical address, license number, and a working unsubscribe link. |

---

## 8. Regression Test Plan

### Phase 2 New Tests

**Backend Unit Tests:**

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P2-U01 | `test_resend_send_email_success` — EmailDeliveryService sends email and returns Resend message ID | Resend API called with correct payload; message_id stored in notification_log |
| P2-U02 | `test_resend_send_email_retry_on_timeout` — Resend client retries on connection timeout | Retries 3 times with exponential backoff; succeeds on third attempt; notification_log updated |
| P2-U03 | `test_resend_send_email_retry_on_429` — Resend client backs off on rate limit | Waits with exponential backoff; re-queues if still rate limited after max retries |
| P2-U04 | `test_resend_send_email_fails_after_5_retries` — All retries exhausted | notification_log status = `failed`; agent action item created with descriptive message |
| P2-U05 | `test_webhook_delivered_updates_status` — Delivery webhook processing | notification_log status changes from `sent` to `delivered`; `delivered_at` timestamp recorded |
| P2-U06 | `test_webhook_opened_updates_status` — Open webhook processing | Status updated to `opened`; `opened_at` recorded; does not downgrade from `clicked` |
| P2-U07 | `test_webhook_hard_bounce_marks_party` — Hard bounce handling | `parties.email_bounced = true`; future sends to that email are blocked; agent action item created |
| P2-U08 | `test_webhook_soft_bounce_retries` — Soft bounce handling | Schedules up to 3 retries over 24 hours; converts to hard bounce after all retries fail |
| P2-U09 | `test_webhook_complaint_auto_unsubscribes` — Spam complaint handling | `parties.unsubscribed_at` set; party excluded from future automated sends |
| P2-U10 | `test_webhook_signature_verification_rejects_invalid` — Webhook security | Invalid Resend signature returns 401; no notification_log updates |
| P2-U11 | `test_reminder_created_for_upcoming_milestone` — Reminder creation | Milestone due in 2 days with `reminder_days_before = 2` triggers reminder notification |
| P2-U12 | `test_no_reminder_for_distant_milestone` — Distant milestone skipped | Milestone due in 10 days with `reminder_days_before = 2` does NOT trigger any notification |
| P2-U13 | `test_no_reminder_for_completed_milestone` — Completed milestone skipped | Milestone with status `completed` does not generate any reminder regardless of due_date |
| P2-U14 | `test_no_duplicate_reminder_same_day` — Idempotency enforcement | Running `check_milestone_reminders` twice on the same day produces only one notification_log entry per milestone+recipient+type combination |
| P2-U15 | `test_escalation_l0_fires_on_due_date` — L0 escalation | Milestone due today triggers L0 notification to responsible party only |
| P2-U16 | `test_escalation_l1_fires_after_1_day` — L1 escalation | 1-day overdue milestone triggers L1 to responsible party + CC agent |
| P2-U17 | `test_escalation_l2_fires_after_3_days` — L2 escalation | 3-day overdue milestone triggers L2; always creates draft (never auto-sends) |
| P2-U18 | `test_escalation_l3_notifies_all_parties` — L3 escalation | 7-day overdue milestone sends to all transaction parties + agent critical alert |
| P2-U19 | `test_escalation_reset_on_in_progress` — Escalation reset | Marking milestone as `in_progress` resets `escalation_level` to 0 and pauses for 48h |
| P2-U20 | `test_first_of_type_creates_draft_in_full_auto` — First-of-type enforcement | Agent in `full_auto` mode triggers an email type NOT in `approved_email_types`; draft created, not auto-sent |
| P2-U21 | `test_approved_type_auto_sends` — Auto-send for approved type | Agent in `auto_send_reminders` with `reminder` in `approved_email_types`; notification queued directly (no draft) |
| P2-U22 | `test_approve_draft_queues_notification` — Draft approval flow | Approving an email_draft creates a `notification_log` entry with status `queued` |
| P2-U23 | `test_batch_approve_processes_all` — Batch approval | Batch approving 5 draft IDs results in 5 `notification_log` entries with status `queued` |
| P2-U24 | `test_email_composer_generates_valid_json` — AI output format | EmailComposerAgent returns valid JSON with subject, body_html, body_text, tone_used, urgency_level |
| P2-U25 | `test_email_composer_includes_property_address` — AI content correctness | Every AI-generated email contains the transaction's property address in both subject and body |
| P2-U26 | `test_email_composer_escalation_tone` — Tone escalation | L2 email uses more urgent language than L0; L3 is more urgent than L2; none are rude |
| P2-U27 | `test_daily_digest_groups_by_transaction` — Digest consolidation | Digest for a party on 3 transactions contains 3 grouped sections with correct milestones |
| P2-U28 | `test_daily_digest_skips_empty` — No empty digests | Party with no pending milestones does NOT receive a digest email |
| P2-U29 | `test_vacation_mode_blocks_sends` — Vacation mode | Agent with `vacation_mode = true` generates zero drafts and zero queued notifications |
| P2-U30 | `test_unsubscribed_party_skipped` — Unsubscribe enforcement | Party with `unsubscribed_at` set is skipped by the reminder check, no notification created |
| P2-U31 | `test_bounced_party_skipped` — Bounce enforcement | Party with `email_bounced = true` is skipped by the send task |
| P2-U32 | `test_rate_limiter_spreads_sends` — Rate limiting | 50 queued emails are sent over 25+ seconds (not in a burst) |
| P2-U33 | `test_stale_draft_expires_after_48h` — Draft expiration | Draft created 49 hours ago is set to `expired` by `expire_stale_drafts` task |
| P2-U34 | `test_milestone_completed_cancels_queued_send` — Pre-send validation | Queued notification for a now-completed milestone is cancelled before Resend API is called |
| P2-U35 | `test_notification_preferences_crud` — Preferences API | Agent can GET and PATCH notification preferences; changes persist across requests |
| P2-U36 | `test_notification_rules_crud` — Rules API | Agent can create, read, update (PATCH), and soft-delete notification rules |
| P2-U37 | `test_party_notification_preference_update` — Party preference | Updating `parties.notification_preference` via API changes the field and affects reminder logic |
| P2-U38 | `test_distributed_lock_prevents_double_processing` — Celery lock | Two concurrent `check_milestone_reminders` calls for the same transaction: only one succeeds; the other skips |

**Backend Integration Tests:**

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P2-I01 | `test_full_flow_preview_all` — End-to-end reminder: milestone due -> hourly check -> draft created -> agent approves -> email queued -> email sent -> delivery webhook -> status delivered | All stages complete; notification_log has full lifecycle; communications table entry created |
| P2-I02 | `test_full_flow_auto_send` — End-to-end for auto_send agent | Hourly check -> notification queued (no draft) -> sent -> delivered |
| P2-I03 | `test_escalation_full_lifecycle` — Complete L0-L3 chain | Milestone goes overdue; simulate day-by-day: L0, L1, L2, L3 fire at correct intervals with correct recipients |
| P2-I04 | `test_bounce_stops_all_future_sends` — Hard bounce integration | Send -> bounce webhook -> party bounced -> next reminder check skips party entirely |
| P2-I05 | `test_draft_edit_preserves_original` — Edit tracking | Create AI draft -> edit body -> verify `original_ai_content` stores original; sent email uses edited content |
| P2-I06 | `test_batch_approval_end_to_end` — Batch flow | 5 drafts -> batch approve -> 5 queued -> 5 sent within rate limit |
| P2-I07 | `test_daily_digest_multi_transaction` — Digest integration | 3 transactions, party on all 3 with `daily_digest` preference -> 1 digest email with 3 sections |
| P2-I08 | `test_vacation_mode_end_to_end` — Vacation integration | Enable vacation -> trigger overdue across multiple transactions -> zero sends/drafts -> disable -> normal resumes |
| P2-I09 | `test_unsubscribe_public_endpoint` — Unsubscribe flow | Access `/unsubscribe/{token}` without auth -> update preference -> verify party record updated |
| P2-I10 | `test_webhook_valid_vs_invalid_signature` — Webhook security integration | Valid signature -> 200 + processing; invalid signature -> 401 + no state changes |
| P2-I11 | `test_idempotency_on_worker_restart` — Crash recovery | Queue 20 emails; stop worker after 10; restart; verify exactly 20 sent total (no duplicates) |
| P2-I12 | `test_pending_count_matches_reality` — Badge accuracy | Create drafts and queued items; verify `GET /api/notifications/pending-count` matches actual database state |

**Frontend E2E Tests:**

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P2-E01 | Draft review and approve flow | Navigate to /notifications -> see pending draft -> open EmailPreviewModal -> verify content rendered -> click Approve -> status changes to "sent" -> draft disappears from list |
| P2-E02 | Draft edit and approve flow | Open draft -> click Edit -> change subject and body -> save edits -> approve -> verify edited content is reflected in communication log |
| P2-E03 | Batch approval flow | /notifications shows 5 drafts -> click "Review All" -> approve 3, reject 1, skip 1 -> verify final counts: approved 3, rejected 1, pending 1 |
| P2-E04 | Notification preferences update and persist | /settings/notifications -> change approval_mode to auto_send -> change timezone -> save -> reload page -> verify settings match what was saved |
| P2-E05 | Escalation badges visible on milestone cards | Open transaction with L2 overdue milestone -> verify orange L2 badge on MilestoneCard -> verify MilestoneNotificationHistory shows sent emails |
| P2-E06 | Notification bell badge updates | Verify badge shows correct count -> approve a draft -> verify badge count decrements |

### Phase 1 Regression Tests

All existing Phase 1 tests must continue to pass after Phase 2 changes. The following areas are at highest risk of regression due to Phase 2 modifications:

| Test ID | Description | Expected Result |
|---------|-------------|-----------------|
| P1-R01 | Today View loads and renders four urgency sections correctly | Overdue, Due Today, Coming Up, This Week sections all render with correct items; new "Pending Approvals" section appears only when drafts exist |
| P1-R02 | Today View action items can be completed, snoozed, and dismissed | Mark Complete, Snooze, and Dismiss buttons all function correctly; state changes persist |
| P1-R03 | Milestone template application creates correct milestones with computed dates | GA Conventional Buyer template produces 18 milestones with correct date offsets |
| P1-R04 | Cash transaction templates skip financing/appraisal milestones | GA Cash Buyer template skips conditional milestones; only 12 milestones created |
| P1-R05 | Health score calculation produces correct values for green/yellow/red scenarios | Healthy transaction >= 85; 2 overdue milestones <= 60; missing lender on financed deal penalized by 15 |
| P1-R06 | Closing date change cascades to milestone dates correctly | Auto-generated milestones with closing_date offset update; manually-edited milestones do not |
| P1-R07 | Transaction CRUD (create, read, update, list, soft-delete) all function | All existing transaction endpoints return correct data with new `notification_overrides` column present |
| P1-R08 | Party CRUD (add, edit, remove, role validation) all function | Party endpoints work correctly with new notification columns; existing parties without notification_preference default to `every_milestone` |
| P1-R09 | Milestone CRUD (create, edit, delete, status change) all function | Manual milestone operations work correctly with new `escalation_level` and `reminder_sent_count` columns present |
| P1-R10 | File upload and download (S3/MinIO) still function | Upload, signed URL generation, and file metadata all work unchanged |
| P1-R11 | Contract parsing via Claude AI still functions | AI contract parser produces parsed fields with confidence scores unchanged by Phase 2 |
| P1-R12 | Pipeline sidebar renders all active transactions with correct health dots | Sidebar shows transactions with accurate health colors; clicking filters Today View correctly |

---

## 9. Implementation Order

### Week 4: Email Infrastructure & Data Model

**Day 1 (Monday):**
- Create SQLAlchemy models in `backend/app/models/`:
  - `notification_rule.py` — NotificationRule model
  - `notification_log.py` — NotificationLog model
  - `email_draft.py` — EmailDraft model
- Update `backend/app/models/__init__.py` to import new models
- Create Alembic migration for the three new tables with all indexes and constraints
- Run migration and verify table creation

**Day 2 (Tuesday):**
- Create Alembic migration for modifications to existing tables:
  - `users`: add `notification_preferences` JSONB, `timezone` VARCHAR
  - `communications`: add `delivery_status`, `bounce_reason`, `notification_log_id` FK
  - `milestones`: add `reminder_sent_count`, `escalation_level`, `reminders_paused_until`
  - `parties`: add `notification_preference`, `notification_cooldown_hours`, `last_notification_sent_at`, `email_bounced`, `bounced_at`, `unsubscribed_at`, `unsubscribe_token`
  - `transactions`: add `notification_overrides` JSONB
- Create Pydantic schemas in `backend/app/schemas/`:
  - `notification_rule.py` — request/response schemas for rules
  - `notification_log.py` — response schema for log entries
  - `email_draft.py` — request/response schemas for drafts
  - `notification_preferences.py` — preferences read/update schemas
- Update existing party and communication schemas to include new fields

**Day 3 (Wednesday):**
- Create `backend/app/services/email_delivery_service.py`:
  - Resend client wrapper with provider abstraction
  - `send_email(to, subject, html, text, reply_to, headers, tags)` method
  - Retry logic with exponential backoff for timeouts, 429s, and 5xx
  - Rate limiter (token bucket, 2/sec, burst 10)
- Add `resend>=2.0.0` to `backend/requirements.txt`
- Write unit tests: `test_resend_send_email_success`, `test_resend_retry_on_timeout`, `test_resend_retry_on_429`, `test_resend_fails_after_5_retries`

**Day 4 (Thursday):**
- Create `backend/app/api/webhooks.py`:
  - `POST /api/webhooks/email` endpoint
  - Resend webhook signature verification
  - Dispatch to `process_email_webhook` Celery task
- Create `backend/app/tasks/webhook_tasks.py`:
  - `process_email_webhook` task implementation
  - Handle all event types: sent, delivered, opened, clicked, bounced, complained
  - Hard bounce: mark party, create action item
  - Soft bounce: schedule retries
  - Complaint: auto-unsubscribe
- Write unit tests: `test_webhook_delivered`, `test_webhook_opened`, `test_webhook_hard_bounce`, `test_webhook_complaint`, `test_webhook_signature_rejects_invalid`

**Day 5 (Friday):**
- Build responsive HTML email template using Jinja2:
  - `backend/app/templates/email_base.html` — base template with header, body slot, signature, footer
  - `backend/app/templates/email_reminder.html` — reminder-specific body
  - `backend/app/templates/email_overdue.html` — overdue-specific body
  - `backend/app/templates/email_digest.html` — daily digest body
- Add `jinja2>=3.1.0` to requirements.txt
- Test email rendering in Gmail, Outlook, Apple Mail using Litmus or manual testing
- Create unsubscribe page template: `backend/app/templates/unsubscribe.html`

### Week 5: Celery Tasks & Escalation Engine

**Day 1 (Monday):**
- Configure Celery in the project:
  - Create `backend/app/celery_app.py` — Celery application factory with Redis broker
  - Create `backend/app/celery_config.py` — Beat schedule configuration
  - Add `celery-worker` and `celery-beat` services to `docker-compose.yml`
  - Verify Celery worker starts and connects to Redis
- Create `backend/app/tasks/__init__.py` — task registration
- Create `backend/app/tasks/reminder_tasks.py`:
  - `check_milestone_reminders` task skeleton with Redis distributed locking
  - Write unit tests for lock acquisition, release, and timeout behavior

**Day 2 (Tuesday):**
- Create `backend/app/services/reminder_service.py`:
  - Full reminder check logic: upcoming detection, due-today detection, overdue detection
  - Idempotency key generation and duplicate checking
  - Party preference checking (daily_digest, none, cooldown)
  - Business hours scheduling logic
  - Draft vs. auto-send decision based on approval_mode and first-of-type
- Complete `check_milestone_reminders` task with ReminderService integration
- Write unit tests: `test_reminder_upcoming`, `test_no_reminder_distant`, `test_no_reminder_completed`, `test_no_duplicate`, `test_digest_party_skipped`

**Day 3 (Wednesday):**
- Create `backend/app/services/escalation_service.py`:
  - Escalation level calculation from `days_overdue` and `escalation_days[]`
  - Recipient determination per level (L0: party only, L1: +CC agent, L2: +agent direct, L3: all parties)
  - Escalation pause checking (`reminders_paused_until`)
  - Escalation reset on milestone status change
  - Integration with ReminderService for notification creation
- Write unit tests: `test_l0_on_due_date`, `test_l1_after_1_day`, `test_l2_after_3_days`, `test_l3_all_parties`, `test_reset_on_in_progress`, `test_custom_escalation_days`

**Day 4 (Thursday):**
- Create `backend/app/tasks/send_tasks.py`:
  - `send_queued_emails` task with rate limiting
  - Pre-send validation: re-check milestone status, party bounce status, unsubscribe status
  - Resend API call with idempotency key
  - Communications table entry creation after successful send
  - Error handling: retry or fail based on retry count
- Create `backend/app/tasks/maintenance_tasks.py`:
  - `expire_stale_drafts` task
- Write integration tests: `test_full_flow_preview_all`, `test_full_flow_auto_send`, `test_cancelled_for_completed_milestone`

**Day 5 (Friday):**
- Create `backend/app/tasks/digest_tasks.py`:
  - `generate_daily_digest` task
  - Agent timezone-aware scheduling (only process agents where local time is ~9 AM)
  - Party grouping across multiple transactions
  - Digest HTML rendering using Jinja2 template
  - Empty digest suppression
- Write tests: `test_digest_groups_by_transaction`, `test_digest_skips_empty`, `test_digest_timezone_aware`
- Run full backend test suite; fix any failures

### Week 6: AI Composer, Frontend & Full Testing

**Day 1 (Monday):**
- Create `backend/app/agents/email_composer.py`:
  - Claude API integration for contextual email generation
  - System prompt construction with full transaction/milestone/party context
  - Haiku vs. Sonnet routing based on email type
  - JSON output parsing and validation
  - Style notes injection from agent preferences
  - Fallback to template-based generation if AI call fails
- Write unit tests with mocked Claude responses: `test_composer_valid_json`, `test_composer_includes_address`, `test_composer_escalation_tone`, `test_composer_haiku_for_reminder`, `test_composer_sonnet_for_l2`

**Day 2 (Tuesday):**
- Create API routes in `backend/app/api/`:
  - `notifications.py` — notification rules CRUD, notification log list, pending-count
  - `email_drafts.py` — drafts list/get/edit/approve/reject/batch-approve
  - `unsubscribe.py` — public unsubscribe GET/POST
  - Update `communications.py` — add send and draft endpoints
  - Update `settings.py` or create `notification_settings.py` — preferences GET/PATCH
- Update `backend/app/api/__init__.py` to register new routers
- Write API integration tests for all new endpoints

**Day 3 (Wednesday):**
- Build frontend components:
  - `frontend/src/pages/NotificationCenter.tsx` — three-tab layout with Pending, Sent, Failed
  - `frontend/src/components/NotificationBellBadge.tsx` — sidebar bell with polling
  - `frontend/src/components/EmailPreviewModal.tsx` — full preview/edit/approve modal
  - Wire up React Query hooks for all notification API endpoints
  - Update `frontend/src/lib/api.ts` with new API client functions

**Day 4 (Thursday):**
- Build remaining frontend components:
  - `frontend/src/components/BatchApprovalQueue.tsx` — sequential review flow
  - `frontend/src/pages/NotificationPreferencesPage.tsx` — full settings page
  - `frontend/src/components/PartyNotificationSettings.tsx` — inline party controls
  - `frontend/src/components/TransactionNotificationOverrides.tsx` — transaction-level overrides
  - `frontend/src/components/MilestoneNotificationHistory.tsx` — milestone communication timeline
- Modify existing components:
  - `Layout.tsx` — add NotificationBellBadge to sidebar
  - `TodayView.tsx` — add Pending Approvals section
  - `TransactionDetail/index.tsx` — add Communications tab and milestone notification icons
  - `App.tsx` — add new routes

**Day 5 (Friday):**
- Full integration testing:
  - Run all Phase 2 unit tests (38+ tests)
  - Run all Phase 2 integration tests (12+ tests)
  - Run all Phase 1 regression tests (12 tests)
  - Run all pre-Phase-1 regression tests
  - Manual E2E testing of all 6 frontend scenarios
  - Performance test: `check_milestone_reminders` with 30+ active transactions completes within 60 seconds
  - Verify Celery worker and beat start correctly in Docker Compose
  - Verify all new environment variables are documented and have sensible defaults for development

---

## 10. Dependencies

### What Must Be Complete from Phase 1

| Phase 1 Deliverable | Why Phase 2 Needs It |
|---------------------|---------------------|
| **Milestone templates and auto-generation** | Milestones must have `due_date`, `responsible_party_role`, and `reminder_days_before` set correctly so the reminder scheduler knows when to fire and who to notify |
| **Action items system** | Phase 2 creates action items for failed sends, bounced emails, and escalation alerts. The action item infrastructure (CRUD, Today View rendering) must work. |
| **Transaction health score** | Escalation Level 2+ imposes additional health score penalties. The health score computation and display must be functional. |
| **Today View as primary dashboard** | Phase 2 adds a "Pending Approvals" section to the Today View. The Today View must be the active `/` route with working section rendering. |
| **Milestone CRUD and status management** | The reminder scheduler checks milestone status (`completed`, `waived`, etc.) and the escalation service updates `escalation_level`. Milestone reads and writes must work. |
| **Party CRUD** | Phase 2 adds columns to the `parties` table and queries party records for notification preferences and bounce status. Party reads and writes must work. |
| **User authentication** | All new API endpoints (except `/unsubscribe/{token}` and `/webhooks/email`) require authenticated user context. Auth middleware must be in place. |

### External Services

| Service | Purpose | Required For | Setup Steps |
|---------|---------|-------------|-------------|
| **Resend** (resend.com) | Email delivery API | All outbound email sending and delivery tracking | 1. Create account at resend.com. 2. Generate API key, add as `RESEND_API_KEY` env var. 3. Verify sending domain (`armistead.re`) by adding DNS records (CNAME for DKIM, TXT for SPF). 4. Configure webhook URL in Resend dashboard: `https://api.armistead.re/api/webhooks/email`. 5. Copy webhook signing secret, add as `RESEND_WEBHOOK_SECRET` env var. |
| **Claude API** (Anthropic) | AI email composition | Email draft generation | Already configured from Phase 1 contract parsing. No additional setup needed. Ensure `ANTHROPIC_API_KEY` is set. Haiku and Sonnet model access required. |

### Infrastructure (Docker Compose Changes)

| Component | Current State | Phase 2 Changes |
|-----------|--------------|-----------------|
| **Redis 7** | Running; used by backend for caching | Additionally used as: Celery message broker, Celery result backend, distributed lock storage, rate limiter state |
| **Celery Worker** | Not configured (celery is in requirements.txt but no service exists) | Add `celery-worker` service to docker-compose.yml: `celery -A app.celery_app worker --loglevel=info --concurrency=4` |
| **Celery Beat** | Not configured | Add `celery-beat` service to docker-compose.yml: `celery -A app.celery_app beat --loglevel=info` |
| **PostgreSQL 16** | Running with existing tables | Add 3 new tables and modify 5 existing tables via 2 Alembic migrations |

**Docker Compose Additions:**

```yaml
  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/armistead
      - REDIS_URL=redis://redis:6379/0
      - RESEND_API_KEY=${RESEND_API_KEY}
      - RESEND_WEBHOOK_SECRET=${RESEND_WEBHOOK_SECRET}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - db
      - redis
    restart: unless-stopped

  celery-beat:
    build: ./backend
    command: celery -A app.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db/armistead
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped
```

### Python Dependencies (additions to `backend/requirements.txt`)

```
resend>=2.0.0          # Resend email delivery SDK
celery[redis]>=5.3.0   # Already listed; ensure redis extra is included
redis>=5.0.0           # Already listed; used for Celery broker + distributed locks
jinja2>=3.1.0          # HTML email template rendering
pytz>=2024.1           # Timezone handling for business hours and scheduling
```

### New Environment Variables

| Variable | Description | Required | Default |
|----------|------------|----------|---------|
| `RESEND_API_KEY` | Resend API key for email delivery | Yes (for real sending; can use test key in development) | None |
| `RESEND_WEBHOOK_SECRET` | Resend webhook signing secret for verifying callbacks | Yes (for webhook processing) | None |
| `RESEND_FROM_DOMAIN` | Verified sending domain | No | `armistead.re` |
| `RESEND_FROM_EMAIL` | Verified sender email | No | `noreply@armistead.re` |
| `CELERY_BROKER_URL` | Redis URL for Celery broker | No | Falls back to `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Redis URL for Celery results | No | Falls back to `REDIS_URL` |

---

*Phase 2 Complete -> Proceed to Phase 3: Party Portal*
