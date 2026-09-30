# fraud-rule-engine

A fraud rule engine for card transactions. Every transaction posted to the API is scored by a set of
pluggable rules (velocity, unusual amount, impossible travel). The transaction, its risk assessment
and the rule hits behind it are stored in SQLite. Reviewers work the queue of flagged transactions in a
React console and mark each one **reviewed** (really suspicious) or **cleared** (false positive).
Any transaction scoring at or above the high-risk threshold sends one email alert through Amazon SES.

## Architecture

```text
 Simulator / client ──POST /api/transactions──▶ FastAPI (api/ → services/ → repositories/) ──▶ SQLite
                                                      │           ▲
                                        evaluate()    ▼           │ history (read-only)
                                                 RuleEngine ──────┘
                                                      │ HIGH
                                                      ▼
                                   background task: notification_service ──▶ Notifier (SES / log)

 Reviewer console (React, :5173) ──/api (Vite proxy)──▶ FastAPI (:8000)
```

The engine never writes to the database. It reads history through `SqlHistoryProvider`, and the service
layer stores the transaction and its verdict together in one commit.

## Quick start

```bash
./start.sh --reset --simulate
```

This creates `backend/.venv` and installs packages on first run. It stops anything already on
ports 8000/5173, starts the API and the console, and fills the database with demo traffic. Then open
http://localhost:5173 (API docs: http://localhost:8000/docs). Ctrl+C stops everything.

| Command | What it does |
|---|---|
| `./start.sh` | Start API + console, keeping existing data |
| `./start.sh --reset` | Delete `backend/fraud.db` first |
| `./start.sh --simulate` | Run the command-line simulator once the API is up |
| `./start.sh --email` | Send HIGH alerts as real email through SES (off by default; asks before simulating) |

The easiest way to generate traffic is the **Simulator** page in the console (http://localhost:5173/simulator).
It runs the same scenarios as the CLI, shows pass/fail per check, and lets you send single hand-made transactions.

For a visual explanation of ingestion, rules, scoring, alerts, and reviewer decisions, open
**How it works** in the navigation ([standalone HTML](frontend/public/how-it-works.html), served at `/how-it-works.html`).

To enable email from the UI, open **Email alerts off** in the header, check the recipient, then select
**Turn on email alerts**. The switch uses the server's configured SES sender and recipients; recipients
cannot be changed through this control. It applies to new transactions in the current server process;
restarting restores the startup setting (`./start.sh --email` starts with email enabled). Already queued
alerts may still be delivered after switching off. The current console has no authentication, so this
control, like review actions, is intended for a trusted local deployment. Multiple backend workers do
not share the runtime switch. Successful initialization does not verify SES delivery permissions.

Manual start, if you prefer:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

```bash
python simulator/generate_transactions.py --scenario all
```

## Environment variables (`backend/.env`)

Copy `backend/.env.example` to `backend/.env`. `start.sh` does this for you if the file is missing.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./fraud.db` | SQLAlchemy URL |
| `RULES_CONFIG_PATH` | `rules.yaml` | Rule enable/weight/params file |
| `HIGH_RISK_THRESHOLD` | `70` | Score at which a transaction is HIGH and an alert is sent |
| `NOTIFIER` | `log` | `log` (server log) or `ses` (email) |
| `AWS_REGION` / `AWS_PROFILE` | `ap-south-1` / none | Where and as whom SES is called |
| `SES_SENDER_EMAIL` | none | Verified sender, e.g. `alerts@pravinraj.me` |
| `ALERT_RECIPIENT_EMAIL` | none | One address, or several separated by commas |
| `ALERT_DAILY_LIMIT` | `20` | Safety cap: at most this many alerts per rolling 24 h; extra ones are recorded as FAILED, not sent |
| `CONSOLE_BASE_URL` | `http://localhost:5173` | Link in alert emails. `start.sh` sets it to this machine's network address so the link opens on other devices on the same network; a localhost link is shown as plain text instead of a button |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed browser origins |

## How scoring works

1. Each enabled rule returns a score from 0 to 100 when it triggers, and nothing otherwise.
2. `total = min(100, round(Σ score × weight))` over the rules that triggered.
3. Level and status:

| Condition | Risk level | Status |
|---|---|---|
| No rule triggered | NONE | CLEAN (never in the queue) |
| Total below 40 (`medium_threshold` in `rules.yaml`) | LOW | FLAGGED |
| 40 up to 69 | MEDIUM | FLAGGED |
| 70 and above (`HIGH_RISK_THRESHOLD`) | HIGH | FLAGGED + one email alert |

| Rule | Triggers when | Score |
|---|---|---|
| `velocity` | More than 5 transactions on the account in 10 minutes | 40, +15 per extra transaction (6 → 40, 8 → 70, max 100) |
| `unusual_amount` | z-score ≥ 3 or ≥ 5× the account's median; for accounts with fewer than 5 transactions, INR 100,000 or more | 50, or 80 when z ≥ 6 or ≥ 10× median |
| `impossible_travel` | Reaching this location from the previous one would need more than 900 km/h (distances under 100 km are ignored) | 70, or 90 above 1,800 km/h or at the same moment |

Review lifecycle: FLAGGED → REVIEWED or CLEARED, and REVIEWED → CLEARED. CLEARED is final; any
other move returns 409. To add a rule, see [docs/ADDING_A_RULE.md](docs/ADDING_A_RULE.md): one new
file, no engine changes.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness check |
| POST | `/api/transactions` | Ingest, evaluate, store, maybe alert (201) |
| GET | `/api/flags` | Review queue: `status` (FLAGGED, REVIEWED, CLEARED, ALL), `risk_level`, `account_id`, `sort` (score, newest), `limit`, `offset` |
| GET | `/api/transactions/{id}` | Full detail: transaction, assessment, rule hits, reviews, notification, allowed actions |
| POST | `/api/transactions/{id}/review` | `{"action": "REVIEWED" \| "CLEARED", "reviewer": "...", "note": "..."}` |
| GET | `/api/stats` | Counts by status, open flags by level, alerts sent/failed |
| GET | `/api/rules` | Registered rules with their weight and params |
| GET | `/api/system` | Alert mode (`ses` or `log`), daily limit and usage, and thresholds (the console uses it to warn before email goes out) |
| PUT | `/api/system/notifications` | `{"enabled": true \| false}` toggles email for the current server process; uses only configured recipients |

Money is sent and returned as a string (`"4999.00"`); times are ISO 8601 UTC (`...Z`).

## Running tests

```bash
cd backend && .venv/bin/pytest -q
```

93 tests cover the rules (every worked example in the plan), engine, repositories, API, reviews,
notifications (idempotency, failures, SES via botocore Stubber) and email templates. Tests never call
real AWS or touch `fraud.db`. Add `--cov=app/engine --cov=app/services` for coverage (99%).

## AWS SES

Set up per the project setup guide: SES in `ap-south-1` (sandbox), sender domain `pravinraj.me`
verified with DKIM, and a send-only IAM user `fraud-engine-ses` stored as the `fraud-engine` AWS
profile. Set `NOTIFIER=ses` in `backend/.env`. In sandbox mode every recipient must be verified.
The domain uses DKIM because a college or Gmail sender fails DMARC when sent through SES; see
[docs/DEVLOG.md](docs/DEVLOG.md).

## Design decisions and trade-offs

- **Rules are plugins.** `@register_rule` plus package auto-discovery plus `rules.yaml`. The engine only
  knows the `Rule` interface, and a test proves a new rule runs without editing `engine.py`.
- **Evaluate before insert**, so a rule's history never contains the transaction being scored.
- **Claim-first alerts.** The alert task inserts a `notifications` row (unique per assessment)
  before sending, so it can never send twice. A failed send is recorded as FAILED and never raised into the request.
- **Layering.** Routers only parse input and return output. Services hold logic, repositories hold queries.
  The review transitions live in one dictionary.
- **Decimal money, UTC everywhere, UUID keys**, and string enums shared by models and schemas.

## Known limitations

No reviewer authentication (the reviewer name is typed in). SQLite with offset pagination. An alert is lost
if the server stops mid-send (background task, no outbox). Single currency (INR). Rules run inside the
ingest request. Hardening Phases 10–14 of the plan address these.

## File guide

### Root

| File | What it is |
|---|---|
| `start.sh` | One-command launcher. Installs dependencies on first run, stops anything on ports 8000/5173, then starts the API and console. Email is off unless `--email`; `--reset` wipes the database; `--simulate` loads demo traffic. |
| `docker-compose.yml` | Runs the backend and console in containers. It mounts `~/.aws` read-only so SES can use your profile. Not yet updated for the Phase 10 Postgres setup. |
| `CLAUDE.md` | Working rules for Claude Code in this repo: phase-by-phase, tests must pass, never edit `engine.py` to add a rule. Read automatically at session start. |
| `README.md` | This file. |

### `docs/`

| File | What it is |
|---|---|
| `IMPLEMENTATION_PLAN.md` | The full spec (Implementation Plan 2) as Markdown: data model, rule formulas, API, console, tests and phases 0–14. |
| `DEVLOG.md` | What was built and when, test results, and every decision or deviation from the plan. Update it after each phase. |
| `ADDING_A_RULE.md` | Step-by-step guide to adding a fourth rule (worked example: `blocked_merchant`) without touching the engine. |

### `backend/`

| File | What it is |
|---|---|
| `requirements.txt` | Python dependencies: FastAPI, SQLAlchemy, pydantic-settings, boto3, PyYAML, pytest and pytest-cov. |
| `rules.yaml` | Per-rule `enabled`, `weight` and `params`, plus the MEDIUM threshold. Edit it to tune rules without code changes. |
| `.env.example` | Template for `backend/.env` listing every setting. The real `.env` holds your SES addresses and is git-ignored. |
| `pytest.ini` | Makes `app` importable from tests and points pytest at `tests/`. |
| `Dockerfile` | Backend container image: installs requirements, copies `app/` and `rules.yaml`, and runs uvicorn on port 8000. |

### `backend/app/`

| File | What it is |
|---|---|
| `main.py` | `create_app()` builds the FastAPI app. The lifespan creates tables, loads the engine and notifier, then CORS, the 404/409 error mapping and all `/api` routers are added. |
| `config.py` | `Settings` (pydantic-settings) reads every environment variable and `backend/.env`. `get_settings()` caches it. |
| `database.py` | SQLAlchemy engine, `SessionLocal`, `Base` and the `get_db` dependency. `configure_database()` lets tests point at a temporary file. |
| `enums.py` | String enums shared by models and schemas: `RiskLevel`, `ReviewStatus`, `ReviewAction`, `NotificationStatus`. |
| `models.py` | The five tables: `transactions`, `risk_assessments`, `rule_hits`, `review_actions`, `notifications`. UUID keys, `Numeric(12,2)` money, and unique constraints that enforce one assessment and one alert per transaction. |
| `schemas.py` | Pydantic request/response models (`TransactionIn`, `TransactionDetailOut`, `FlagListOut`, `ReviewIn`, `StatsOut`…) with the plan's validation rules. |
| `timeutils.py` | `utcnow()` and `as_utc()`. SQLite drops timezone info, so every datetime read back is re-marked as UTC here. |

### `backend/app/api/` (routers: parse input, call a service, return output)

| File | What it is |
|---|---|
| `deps.py` | FastAPI dependencies that hand routers the engine, notifier and settings stored on `app.state`. |
| `health.py` | `GET /api/health` liveness check. |
| `transactions.py` | `POST /api/transactions` (ingest, and schedule the alert when HIGH), `GET /api/transactions/{id}`, and `POST /api/transactions/{id}/review`. |
| `flags.py` | `GET /api/flags`: the review queue with status, risk level, account, sort, limit and offset filters. |
| `stats.py` | `GET /api/stats`: header counts by status, open flags by level, and alerts sent or failed. |
| `rules.py` | `GET /api/rules`: every registered rule with its description, enabled flag, weight and params. |
| `system.py` | Alert mode, configured recipients, usage, and thresholds; `PUT /api/system/notifications` switches delivery for the current server process. |

### `backend/app/services/` (business logic)

| File | What it is |
|---|---|
| `transaction_service.py` | Turns the request into `TransactionData`, evaluates it against stored history, then inserts the transaction, assessment and rule hits in one commit. |
| `review_service.py` | The `TRANSITIONS` table (the only definition of the review lifecycle), `allowed_actions()`, and applying a review with its audit row. |
| `query_service.py` | Builds the detail, queue-item and stats responses from database rows. |
| `notification_service.py` | `notify_high_risk()`: runs as a background task with its own session. It claims the alert row, enforces the daily alert limit, sends, and records SENT or FAILED, and never raises. |
| `errors.py` | `NotFoundError` and `ConflictError`, mapped to HTTP 404 and 409 in `main.py`, so services never import FastAPI. |

### `backend/app/repositories/` (database queries)

| File | What it is |
|---|---|
| `history.py` | `SqlHistoryProvider`: the rules' read-only view of an account's stored transactions (`count_in_window`, `recent_amounts`, `previous_transaction`). |
| `transactions.py` | Insert and fetch transaction rows. |
| `assessments.py` | Insert an assessment with its rule hits, filtered and sorted queue queries with totals, and status/level counts. |
| `reviews.py` | Append a `review_actions` audit row. |
| `notifications.py` | `claim()` inserts the PENDING alert row (the unique constraint blocks duplicates), `finish()` records the outcome, plus counts by status. |

### `backend/app/engine/` (the rule engine)

| File | What it is |
|---|---|
| `base.py` | Core types: `TransactionData`, `RuleResult`, the `HistoryProvider` protocol and the abstract `Rule` class every rule extends. |
| `registry.py` | `RULE_REGISTRY`, the `@register_rule` decorator (rejects duplicate names) and `discover_rules()`, which imports every module in `rules/`. |
| `config.py` | Loads `rules.yaml` into `EngineConfig`. A rule missing from the file runs enabled with its defaults. |
| `engine.py` | `RuleEngine`: builds rules from config, runs them (skipping any that crash), combines weighted scores into a level and status, and `describe()`s them. Never edited to add a rule. |
| `geo_utils.py` | Haversine distance in km, plus a label-or-coordinates helper for readable locations. |
| `rules/velocity.py` | Flags too many transactions on one account in a short window. |
| `rules/unusual_amount.py` | Flags amounts far above the account's usual spend (z-score and ratio to median), with a fixed limit for new accounts. |
| `rules/impossible_travel.py` | Flags two transactions too far apart to travel between in the time available (faster than 900 km/h). |

### `backend/app/notifications/` (alert delivery)

| File | What it is |
|---|---|
| `base.py` | `AlertPayload`, `SendResult` and the abstract `Notifier` interface every channel implements. |
| `templates.py` | Pure functions that render the alert subject, plain-text body and HTML body. Values are escaped; a localhost console link becomes plain text with a note instead of a button that fails on other devices. |
| `ses.py` | `SESNotifier`: sends the alert through the SES v2 `send_email` API with text and HTML bodies. AWS errors become a failed `SendResult`. |
| `log.py` | `LogNotifier`: writes the alert to the server log instead of emailing. Default for local work. |
| `factory.py` | `get_notifier()` picks the notifier from `NOTIFIER`, and fails at startup if SES is chosen without sender or recipient addresses. |

### `backend/tests/`

| File | What it is |
|---|---|
| `conftest.py` | Fixtures: an API client on a temporary SQLite file with a recording notifier, the real engine, and registry cleanup. |
| `fakes.py` | `make_txn()` factory, `InMemoryHistoryProvider` (same semantics as the SQL one) and `FakeNotifier`. |
| `test_repositories.py` | Checks the history queries' exact window and ordering rules, and that all five tables are created. |
| `rules/test_*.py` | One file per rule with its edge cases, plus `test_worked_examples.py`, which runs every row of the plan's examples table through the real engine. |
| `engine/test_engine.py` | Score aggregation, weights, the 100 cap, level boundaries (39/40, 69/70), broken rules, and YAML overrides. |
| `engine/test_registry.py` | The extensibility test (a rule defined only in the test runs), duplicate-name rejection and discovery. |
| `api/helpers.py` | Request-body builders and the Chennai → London "travel pair" used across API tests. |
| `api/test_transactions.py` | Ingest, validation errors (422), queue placement, one alert per HIGH, detail responses and the rules endpoint. |
| `api/test_reviews.py` | FLAGGED → REVIEWED → CLEARED with history; the 409 and 404 cases. |
| `api/test_flags_and_stats.py` | Queue filters, sorting, pagination and exact stats counts on a known dataset. |
| `notifications/test_notification_service.py` | Idempotency (two calls send one alert), ignoring non-HIGH, and recording failures and crashes. |
| `notifications/test_ses_and_templates.py` | SES request shape via botocore Stubber, client errors, subject format, HTML escaping and the notifier factory. |

### `simulator/`

| File | What it is |
|---|---|
| `generate_transactions.py` | Posts realistic traffic to the running API: baseline accounts plus velocity, amount, travel and combo fraud. Prints a pass/fail table and exits 1 on any mismatch. |

### `frontend/`

| File | What it is |
|---|---|
| `package.json` | React 19, React Router 7 and Vite 7, with `dev`, `build` and `preview` scripts. |
| `vite.config.js` | Dev server on 5173. Proxies `/api` to the backend (`API_TARGET`, default `http://localhost:8000`), so no CORS setup is needed. |
| `index.html` | Page shell that loads `src/main.jsx`. |
| `Dockerfile` | Container that runs the Vite dev server. |
| `src/main.jsx` | Entry point: routes for the queue (`/`), detail (`/transactions/:id`), simulator (`/simulator`) and rules (`/rules`). |
| `src/App.jsx` | Layout: dark navigation bar (queue count badge, alert-mode pill, reviewer name) and the stats strip, polled every 10 s. |
| `src/simulator/scenarios.js` | Browser port of the CLI simulator: the same five scenarios with a seeded generator. Each run tags account IDs so re-runs start clean. |
| `src/styles.css` | All styling: colour tokens with dark mode, badges (HIGH red, MEDIUM amber, LOW grey…), table, panels, responsive layout. |
| `public/how-it-works.html` | Standalone responsive workflow guide: ingestion, detection rules, score example, alerts, review lifecycle, and simulator walkthrough. Copied into production builds. |
| `src/api/client.js` | `fetch` wrapper for every endpoint. It throws `ApiError(status, detail)` with the server's message. |
| `src/hooks/usePolling.js` | Re-runs a loader every N ms and pauses while the browser tab is hidden. |
| `src/utils/format.js` | INR formatting (`en-IN`), local date and time, relative "5 minutes ago", and rule-name labels. |
| `src/pages/QueuePage.jsx` | Review queue: filters kept in the URL, table, pagination, polling, and loading, empty and error-with-retry states. |
| `src/pages/SimulatorPage.jsx` | Pick and run scenarios with a progress bar and a pass/fail results table. When email is on, a confirmation checkbox is required before anything runs. |
| `src/pages/RulesPage.jsx` | Rule cards showing enabled flag, weight and params, plus the LOW/MEDIUM/HIGH score bands. |
| `src/pages/TransactionPage.jsx` | Detail view: amount and badges, transaction facts with a copy-ID button, alert status, rule breakdown, review panel and history. |
| `src/components/StatsBar.jsx` | Summary strip: open flags split by level, reviewed, cleared, clean, and alerts. |
| `src/components/AlertModePill.jsx` | Header pill that shows whether alerts send real email (with today's usage) or only go to the log. |
| `src/components/ManualTransactionForm.jsx` | Simulator form for sending one custom transaction; shows the verdict and reasons inline. |
| `src/components/ReviewerName.jsx` | Header input for the reviewer's name. Review buttons stay disabled until it is set. |
| `src/components/Filters.jsx` | Status tabs, risk-level select, account search and sort select for the queue. |
| `src/components/FlagsTable.jsx` | Queue table. HIGH rows get a red edge; clicking a row (or pressing Enter) opens its detail page. |
| `src/components/Pagination.jsx` | Previous/Next controls with "Page X of Y". |
| `src/components/RiskBadge.jsx` / `StatusBadge.jsx` | Coloured badges that always include the text, so colour never carries meaning alone. |
| `src/components/RuleHitCard.jsx` | One triggered rule: score × weight = weighted score, the reason, and its key numbers (distance/speed, median/ratio/z, count/window). |
| `src/components/ReviewPanel.jsx` | Note box (1,000-character counter) and one button per allowed action. Clear asks for confirmation, and the server's 409 message is shown. |
| `src/components/ReviewHistory.jsx` | Past review actions, newest first: reviewer, action, from → to status, note and time. |
