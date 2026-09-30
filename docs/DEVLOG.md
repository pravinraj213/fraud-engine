# Development log

What was built, in what order, and why. Newest entries at the bottom of each section.

## 2026-09-30: Environment and AWS SES

- **First prototype** (since replaced): FastAPI + SQLite engine with three rules and a small React console.
- **SES in `ap-south-1`**, sandbox mode (200 emails/day, verified recipients only).
  - IAM policy `FraudEngineSESSend` + user `fraud-engine-ses`: can only send, and only from
    `alerts@pravinraj.me`. The app uses the `fraud-engine` AWS profile; keys live in `~/.aws`, never in the repo.
  - Verified recipients: pravinraj.p.2024.csbs@rajalakshmi.edu.in, pravinraj.2370@gmail.com.
- **Why the sender is `alerts@pravinraj.me`:** mail sent from the college address was silently
  dropped. rajalakshmi.edu.in publishes DMARC `p=reject` with strict alignment, and SES can't sign
  for that domain. We verified our own domain `pravinraj.me` with Easy DKIM (3 CNAMEs) and a custom
  MAIL FROM `bounce.pravinraj.me` (MX + SPF), added through the Cloudflare API. Alerts now pass DMARC.

## 2026-09-30: Implementation Plan 2, Phases 0–9

Built from `docs/IMPLEMENTATION_PLAN.md` (exported from the plan .docx). The earlier prototype was replaced.

| Phase | What | Result |
|---|---|---|
| 0 Scaffold | Package tree, `Settings`, `database.py`, lifespan, CORS, `/api/health`, `rules.yaml`, `pytest.ini` | done |
| 1 Data model | `enums.py`; five tables (`transactions`, `risk_assessments`, `rule_hits`, `review_actions`, `notifications`) with UUID keys, `Numeric(12,2)` money, composite `(account_id, occurred_at)` index; repositories; `SqlHistoryProvider` | repository tests pass |
| 2 Engine core | `base.py`, `registry.py` (`@register_rule`, auto-discovery), `config.py` (YAML), `engine.py` (`EngineResult`, `describe()`), `tests/fakes.py` | aggregation, boundary, broken-rule and extensibility tests pass |
| 3 Rules | `velocity`, `unusual_amount`, `impossible_travel`, `geo_utils` | every worked example is a test; `engine.py` untouched |
| 4 API | Schemas, services (transaction, review with transition table, query/stats), 7 routes | integration tests pass |
| 5 Notifications | `Notifier` interface, `LogNotifier`, `SESNotifier` (sesv2, text + HTML), factory, templates, claim-first idempotent `notify_high_risk` in a background task | Stubber, idempotency and failure tests pass; **real SES alerts delivered** |
| 6 Simulator | `simulator/generate_transactions.py`: baseline, velocity, amount, travel, combo | 15/15 checks pass on a fresh DB (seeds 1, 2, 3, 7, 42) |
| 7–8 Console | React Router; header stats + reviewer name; queue with URL filters, pagination, polling, error/retry; detail page with rule cards, review panel from `allowed_actions`, history | `vite build` passes |
| 9 Docs | README (overview, file guide), this log, `ADDING_A_RULE.md`, `start.sh` | done |

**Tests:** 85 passed; coverage of `app/engine` + `app/services` is 99% (target 85%).

### Decisions and deviations from the plan

- **Several alert recipients.** The plan names one `ALERT_RECIPIENT_EMAIL`. It accepts a
  comma-separated list, because alerts go to both of your addresses.
- **Env var names** follow the plan (`SES_SENDER_EMAIL`, `ALERT_RECIPIENT_EMAIL`, `CONSOLE_BASE_URL`,
  `RULES_CONFIG_PATH`, `CORS_ORIGINS`). The old `SES_SENDER` / `SES_RECIPIENTS` names are gone.
- **`app/timeutils.py`** (not in the plan's tree): `as_utc()` re-attaches UTC to datetimes read
  back from SQLite, which drops tzinfo. Every value read from the DB passes through it.
- **`app/services/errors.py`** (not in the tree): `NotFoundError` / `ConflictError`, mapped to 404 / 409
  in `main.py`, so services never import FastAPI.
- **`create_app(settings, notifier)`** factory in `main.py`, so tests inject a temporary database and
  a `FakeNotifier` without touching the real `.env`.
- **Worked example "6× median, z = 4"** is tested as 6× median giving 50 (MEDIUM). The z-score there is
  about 1.8, because an exact z of 4 would need a contrived history. The row's outcome is the same.
- **Simulator baseline amounts** are ±40% around a per-account base (INR 400–2,000) instead of a flat
  INR 200–5,000. The first five purchases cover the account's whole range. With random amounts,
  a short, uniform early history made ordinary purchases look like z-score outliers (the rule was
  right, the demo data was unlucky), and "baseline → all CLEAN" failed for 2 of 10 accounts.
- **Queue page size** is 25 (API default 50, max 200).
- **Not verified in a browser.** The console builds and its API calls work through the Vite proxy,
  but the Phase 7–8 click-through checklist still needs a manual run (the Chrome extension wasn't connected).

### Housekeeping

- Removed the plan `.docx` (its content is in `docs/IMPLEMENTATION_PLAN.md`), the one-off
  Cloudflare DNS script (records are live), build output and caches.
- Added `start.sh` to run backend + console with one command. If ports 8000/5173 are already in use,
  it stops the listening processes (SIGTERM, then SIGKILL after 5 s) and starts fresh, so re-running it
  replaces a previous run.
- First real run via `start.sh --reset --simulate`: simulator 15/15, and all 4 HIGH alerts sent through SES.

## Next

Hardening Phases 10–14 (Postgres + Alembic, outbox worker, auth, smarter rules, load test) are not
started. Each is a separate step, per the plan.

## 2026-09-30: Email safety, simulator UI, console redesign

Prompted by feedback: runs were sending real email without asking, there was no simulator UI, and
alert links pointed to localhost.

- **Email is opt-in.** `backend/.env` now has `NOTIFIER=log`. `start.sh` forces log mode unless run with
  `--email`, and asks before `--simulate` when email is on.
- **Daily alert cap** `ALERT_DAILY_LIMIT` (default 20 per rolling 24 h, well under the SES sandbox's
  200). Alerts beyond it are recorded as FAILED ("Daily alert limit reached") and not sent. Tested.
- **`GET /api/system`** (new, beyond the plan's 7 endpoints) exposes the alert mode and usage, so the console can
  show an "Email alerts on/off" pill and require confirmation before a simulator run that would email.
- **Alert links.** `start.sh` sets `CONSOLE_BASE_URL` to the machine's LAN address (e.g.
  `http://172.16.101.172:5173`), which opens from a phone on the same Wi-Fi. If the URL is still
  localhost, the email shows the address as text with an explanation instead of a dead button.
  The console is not on the public internet, so the link cannot work from outside the network.
- **Simulator page** `/simulator`: scenario cards, progress bar, pass/fail table with links, and a form
  to send one custom transaction. Run IDs are appended to account IDs so re-runs don't change results.
- **Console redesign:** navigation bar, stats strip, segmented status tabs, Rules page, favicon. Alerts are
  labelled "emailed" or "logged" by channel, so log-mode alerts no longer claim they were emailed.
- **Bug fixed:** the review panel was keyed by status, so it remounted after "Mark reviewed" and hid the
  success message. It is now keyed by transaction.
- **Verified in a real browser** (headless Chromium via Playwright): the simulator runs 15/15 from the UI,
  a manual transaction works, filters survive reload, the back link keeps filters, review buttons are
  disabled until a name is set, FLAGGED → REVIEWED → CLEARED leaves 2 history entries and no buttons,
  there's no horizontal overflow at 390 px, dark mode works, and there are no console errors.
- Tests: 87 passed.

## 2026-09-30: Responsive console, professional alerts, and workflow guide

- Refined the console hierarchy, spacing, summary cards, filters, and review panels. The queue
  becomes labeled transaction cards on phones. Added explicit transaction buttons, keyboard focus,
  a skip link, refresh/reset controls, and the workflow guide in navigation.
- Rebuilt HTML alerts with a centered table layout, inline styles, mobile media queries, an inbox
  preview, risk summary, transaction facts, readable rule evidence, and a review action. Retained
  escaped dynamic content, plain-text delivery, and localhost link guidance.
- Added `frontend/public/how-it-works.html`, a standalone page explaining the implemented workflow,
  default rule thresholds, a scoring example, alerts, review transitions, and current limitations.
- Added a header notification menu and `PUT /api/system/notifications`. The switch affects new
  transactions in the current backend process and resets on restart. It uses server-configured
  recipients only; the endpoint rejects recipient overrides. Initialization failures preserve the
  previous mode. No delivery is triggered by switching modes.
- Restricted the local `.env` recipient list to the single Gmail address requested by the user.
  Email remains off at startup unless enabled through startup configuration or `--email`.
- Disabled simulator submissions until alert settings are loaded.
- Verification: `npm run build` passed; **93 backend tests passed** (one existing Starlette/httpx
  deprecation warning). Chromium checks passed at 1440, 768, 390, and 320 px for the queue,
  simulator, rules, transaction detail, workflow guide, and rendered email, with no page overflow.
  Checked notification on/off controls, recipient display, transaction navigation, and dark mode.
  Browser APIs were mocked; no live email was sent. Gmail/Outlook delivery rendering was not tested.
