# Fraud Rule Engine — Implementation Plan

Sep 30, 2026 · @REC

This plan specifies everything Claude Code needs to build fraud-rule-engine in ten core phases plus five hardening phases, each ending in passing tests.

## How to use this plan with Claude Code

Give Claude Code this plan as a file in the repo and have it build one phase at a time, stopping for your review after each. One giant "build everything" prompt produces code you can't check.

Export this doc as Markdown and save it in the repo as docs/IMPLEMENTATION_PLAN.md.

Create CLAUDE.md in the repo root with this content. Claude Code reads it automatically at the start of every session:

# fraud-rule-engine

Fraud rule engine (FastAPI + SQLAlchemy + SQLite) with a React (Vite) reviewer console and AWS SES alerts.
The full spec is docs/IMPLEMENTATION_PLAN.md. Follow it exactly; if something is ambiguous, ask before inventing.

## Rules for working in this repo
- Build only the phase I ask for. Stop at the end of the phase and summarise what changed.
- Every phase ends with `pytest` passing. Show me the test output.
- Never modify app/engine/engine.py to add or change a fraud rule. Rules live only in app/engine/rules/.
- Never hard-code secrets, emails or AWS keys. Read everything from app/config.py (which reads backend/.env).
- Never call real AWS in tests. Use LogNotifier, a fake notifier, or botocore Stubber.
- All timestamps are timezone-aware UTC. Money is Decimal, never float.
- Type hints on every function. Keep functions small; no business logic in routers.

## Commands
- Backend: cd backend && uvicorn app.main:app --reload
- Tests:   cd backend && pytest -q
- Frontend: cd frontend && npm run dev
- Simulator: python simulator/generate_transactions.py --scenario all

Start Claude Code in the repo root and give it the kickoff prompt:

Read CLAUDE.md and docs/IMPLEMENTATION_PLAN.md. Implement Phase 0 only.
When done, run the tests, show me the output, list every file you created,
and stop. Do not start Phase 1.

For each later phase, send: Implement Phase N from the plan. Same rules: tests passing, list files, stop.

Before moving on, check the phase's acceptance criteria yourself and commit: git commit -m "Phase N: <name>". A commit per phase means any bad phase can be rolled back cleanly.

## Architecture

Every transaction takes one path: the API asks the rule engine for a score, stores the transaction and verdict together, and hands HIGH scores to a background alert task.

system architecture · 7 components

The console only ever talks to the API. The rule engine never writes to the database; it reads history through SqlHistoryProvider, and the service layer does the writing.

Backend package layout (extends the setup guide's tree with the service and repository layers):

backend/app/
├── main.py  config.py  database.py  enums.py  models.py  schemas.py
├── api/            # routers: health.py, transactions.py, flags.py, stats.py, rules.py
├── services/       # transaction_service.py, review_service.py, query_service.py, notification_service.py
├── repositories/   # transactions.py, assessments.py, reviews.py, notifications.py, history.py
├── engine/         # base.py, registry.py, engine.py, config.py, geo_utils.py, rules/
└── notifications/  # base.py, log.py, ses.py, factory.py, templates.py

## Tech stack and conventions

The stack is deliberately small: every dependency below has a clear job, and nothing else should be added without a reason.

| Area | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Type hints everywhere |
| API | FastAPI + Uvicorn | All routes under /api |
| ORM | SQLAlchemy 2.0, synchronous | Mapped[...] / mapped_column style |
| Database | SQLite file backend/fraud.db | Tables created on startup with create_all |
| Validation | Pydantic v2 | Separate *In and *Out schemas |
| Settings | pydantic-settings reading backend/.env | Single Settings object in app/config.py |
| Rule config | backend/rules.yaml via PyYAML | Enable/disable, weights and parameters per rule |
| AWS | boto3, sesv2 client, region ap-south-1 | Only inside notifications/ses.py |
| Tests | pytest + FastAPI TestClient (httpx) | Temp SQLite database per test |
| Frontend | React + Vite + React Router | Plain CSS, no UI framework |
| Simulator | Python script using httpx | Sends transactions to the running API |



Conventions Claude Code must follow:

Layering: routers (api/) → services (services/) → repositories (repositories/) → models. Routers only parse input and return output.

Money: Decimal in Python, Numeric(12, 2) in the database, serialised as a string in JSON.

Time: store UTC with timezone; the API accepts ISO 8601 and returns ISO 8601 with Z.

IDs: UUID4 strings for every primary key.

Enums: Python str enums shared by models and schemas (RiskLevel, ReviewStatus, ReviewAction).

Currency: single currency, INR, stored per transaction for display only. No conversion.

Logging: standard logging module, one logger per module, no print in app code.

Add these to requirements.txt on top of the setup guide's list: pyyaml.

## Data model

Five tables: the raw transaction, one risk assessment per transaction, the rule hits behind that assessment, the reviewer's actions, and the notification record that prevents duplicate alerts.

transactions — one row per incoming transaction, never edited after insert.

| Column | Type | Notes |
|---|---|---|
| id | String(36), PK | UUID4 |
| account_id | String(64), indexed | The card or account the transaction belongs to |
| amount | Numeric(12, 2) | Must be > 0 |
| currency | String(3) | Default INR |
| merchant | String(128) |  |
| latitude | Float | −90 to 90 |
| longitude | Float | −180 to 180 |
| location_label | String(128), nullable | Human-readable, e.g. "Chennai, IN" |
| occurred_at | DateTime(timezone=True), indexed | When the transaction happened; rules use this |
| created_at | DateTime(timezone=True) | When the API received it |



Add a composite index on (account_id, occurred_at); the velocity, amount and geo queries all filter on it.

risk_assessments — the engine's verdict, one per transaction.

| Column | Type | Notes |
|---|---|---|
| id | String(36), PK |  |
| transaction_id | FK → transactions.id, unique | 1:1 |
| total_score | Integer | 0–100 |
| risk_level | Enum RiskLevel | NONE, LOW, MEDIUM, HIGH |
| status | Enum ReviewStatus, indexed | CLEAN, FLAGGED, REVIEWED, CLEARED |
| evaluated_at | DateTime(timezone=True) |  |
| updated_at | DateTime(timezone=True) | Changes on every review action |



rule_hits — one row per rule that triggered. Rules that did not trigger are not stored.

| Column | Type | Notes |
|---|---|---|
| id | String(36), PK |  |
| assessment_id | FK → risk_assessments.id, indexed |  |
| rule_name | String(64) | Registry name, e.g. velocity |
| score | Integer | 0–100, before weighting |
| weight | Float | Weight used at evaluation time |
| reason | String(255) | One sentence a reviewer can read |
| details | JSON | Rule-specific numbers, e.g. distance and speed |



review_actions — append-only audit trail.

| Column | Type | Notes |
|---|---|---|
| id | String(36), PK |  |
| assessment_id | FK → risk_assessments.id, indexed |  |
| action | Enum ReviewAction | REVIEWED, CLEARED |
| from_status | Enum ReviewStatus |  |
| to_status | Enum ReviewStatus |  |
| reviewer | String(64) | Name typed in the console |
| note | Text, nullable | Max 1000 characters |
| created_at | DateTime(timezone=True) |  |



notifications — at most one alert per assessment.

| Column | Type | Notes |
|---|---|---|
| id | String(36), PK |  |
| assessment_id | FK → risk_assessments.id, unique | The unique constraint is what guarantees no duplicate alerts |
| channel | String(16) | ses or log |
| status | String(16) | PENDING, SENT or FAILED |
| provider_message_id | String(128), nullable | SES MessageId |
| error | Text, nullable | Error message when FAILED |
| created_at | DateTime(timezone=True) |  |



Status lifecycle. A transaction with no triggered rules is saved as CLEAN and never appears in the review queue. Any triggered rule makes it FLAGGED. Reviewers can then move it only along these transitions; anything else returns HTTP 409.

| From | Action | To | Meaning |
|---|---|---|---|
| FLAGGED | REVIEWED | REVIEWED | Investigated and confirmed or escalated as suspicious |
| FLAGGED | CLEARED | CLEARED | False positive; the transaction is legitimate |
| REVIEWED | CLEARED | CLEARED | Later found to be legitimate |



CLEARED is final. Keep the allowed transitions in one dictionary in services/review_service.py so the rule is defined in exactly one place.

## Rule engine design

The engine only knows the Rule interface: rules register themselves, are discovered by scanning app/engine/rules/, and are configured from rules.yaml. Adding a rule means adding one file; engine.py is never edited.

Core types — app/engine/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar, Protocol


@dataclass(frozen=True)
class TransactionData:
    id: str
    account_id: str
    amount: Decimal
    merchant: str
    latitude: float
    longitude: float
    occurred_at: datetime
    location_label: str | None = None


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    triggered: bool
    score: int = 0            # 0-100, before weighting
    reason: str = ""          # one sentence for the reviewer
    details: dict[str, Any] = field(default_factory=dict)


class HistoryProvider(Protocol):
    """Read-only view of the account's STORED transactions.
    The transaction being evaluated is not stored yet, so it is never returned."""

    def count_in_window(self, account_id: str, start: datetime, end: datetime) -> int: ...
    def recent_amounts(self, account_id: str, at: datetime, limit: int) -> list[Decimal]: ...
    def previous_transaction(self, account_id: str, at: datetime) -> TransactionData | None: ...


class Rule(ABC):
    name: ClassVar[str]
    description: ClassVar[str]
    default_params: ClassVar[dict[str, Any]] = {}

    def __init__(self, params: dict[str, Any] | None = None, weight: float = 1.0) -> None:
        self.params = {**self.default_params, **(params or {})}
        self.weight = weight

    @abstractmethod
    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult: ...

History semantics: count_in_window counts stored transactions with start <= occurred_at <= end. recent_amounts returns amounts with occurred_at <= at, newest first. previous_transaction returns the latest stored transaction with occurred_at <= at. Implement it as SqlHistoryProvider in repositories/history.py, and as InMemoryHistoryProvider in tests/fakes.py for unit tests.

Registry and auto-discovery — app/engine/registry.py

RULE_REGISTRY: dict[str, type[Rule]] = {}

def register_rule(cls: type[Rule]) -> type[Rule]:
    if cls.name in RULE_REGISTRY:
        raise ValueError(f"Duplicate rule name: {cls.name}")
    RULE_REGISTRY[cls.name] = cls
    return cls

def discover_rules(package: str = "app.engine.rules") -> None:
    """Import every module in the rules package so their @register_rule decorators run."""
    pkg = importlib.import_module(package)
    for module in pkgutil.iter_modules(pkg.__path__):
        if not module.name.startswith("_"):
            importlib.import_module(f"{package}.{module.name}")

Configuration — backend/rules.yaml

scoring:
  medium_threshold: 40      # LOW below this, MEDIUM from here
                            # HIGH comes from HIGH_RISK_THRESHOLD in .env (default 70)
rules:
  velocity:
    enabled: true
    weight: 1.0
    params: { window_minutes: 10, max_transactions: 5 }
  unusual_amount:
    enabled: true
    weight: 1.0
    params: { min_history: 5, lookback: 50, z_threshold: 3.0, median_multiplier: 5, absolute_threshold: 100000 }
  impossible_travel:
    enabled: true
    weight: 1.0
    params: { max_speed_kmh: 900, min_distance_km: 100 }

A rule found by discovery but missing from the YAML runs enabled, with weight 1.0 and its default_params, so a new rule works by adding its file alone. A YAML entry naming an unknown rule logs a warning and is ignored.

Engine — app/engine/engine.py

RuleEngine.from_config(path, settings) calls discover_rules(), reads the YAML, and instantiates every enabled rule. It is built once at startup (FastAPI lifespan), stored on app.state.engine, and injected through a get_engine dependency.

evaluate(txn, history) -> EngineResult runs every rule. A rule that raises is logged with logger.exception and skipped, so one broken rule never blocks ingestion.

total_score = min(100, round(sum(hit.score * rule.weight for each triggered rule))).

Risk level and status:

| Condition | risk_level | status |
|---|---|---|
| No rule triggered | NONE | CLEAN |
| Triggered, score below medium_threshold (40) | LOW | FLAGGED |
| Score from 40 up to HIGH_RISK_THRESHOLD − 1 | MEDIUM | FLAGGED |
| Score ≥ HIGH_RISK_THRESHOLD (70) | HIGH | FLAGGED |



EngineResult holds total_score, risk_level, status, the list of hits (each a RuleResult plus the weight used) and should_notify = risk_level == HIGH.

describe() returns name, description, enabled, weight and params for every rule; GET /api/rules exposes it.

## The three rules

Each rule is one file in app/engine/rules/, decorated with @register_rule, with a fixed score formula so tests can assert exact numbers. Put the haversine helper in app/engine/geo_utils.py, outside the scanned rules package.

### Velocity — rules/velocity.py, name velocity

Too many transactions on one account in a short window suggests a stolen card being drained.

count = history.count_in_window(account_id, occurred_at − window_minutes, occurred_at) + 1 (the +1 is the current transaction).

Triggered when count > max_transactions. Exactly max_transactions is allowed.

score = min(100, 40 + 15 × (count − max_transactions − 1)). With the defaults: 6 → 40, 7 → 55, 8 → 70, 9 → 85, 10+ → 100.

Reason: 7 transactions in 10 minutes (limit 5).

Details: count, window_minutes, max_transactions.

### Unusual amount — rules/unusual_amount.py, name unusual_amount

An amount far above what this account normally spends is suspicious; accounts without history fall back to a fixed limit.

amounts = history.recent_amounts(account_id, occurred_at, lookback).

Cold start (len(amounts) < min_history): triggered when amount >= absolute_threshold, score 50. Reason: INR 150,000.00 exceeds the INR 100,000.00 limit for accounts with little history (3 prior transactions).

With history: compute mean, population stdev and median (convert to float for statistics).

ratio = amount / median.

z = (amount − mean) / stdev when stdev > 0. When stdev == 0, skip the z test and use the ratio test only, so a history of identical amounts doesn't flag INR 1 more.

Triggered when z >= z_threshold or ratio >= median_multiplier.

Score 80 when z >= 2 × z_threshold or ratio >= 2 × median_multiplier; otherwise 50.

Reason: INR 48,000.00 is 12.0× this account's median of INR 4,000.00 (z-score 9.4).

Details: amount, mean, median, stdev, z_score (null when stdev is 0), ratio, history_size. Store numbers as floats rounded to 2 decimals.

### Impossible travel — rules/impossible_travel.py, name impossible_travel

Two transactions too far apart to travel between in the time available mean one of them is not the real cardholder.

prev = history.previous_transaction(account_id, occurred_at). None → not triggered.

distance_km = haversine(prev, txn) with Earth radius 6371 km.

distance_km < min_distance_km → not triggered. This ignores GPS noise and nearby merchants.

hours = (occurred_at − prev.occurred_at).total_seconds() / 3600. When hours <= 0 the speed is treated as infinite.

Triggered when speed_kmh = distance_km / hours > max_speed_kmh (900 km/h is roughly airliner cruising speed).

Score 90 when speed is infinite or > 2 × max_speed_kmh; otherwise 70. Either way it reaches HIGH alone, because impossible travel is the strongest single signal.

Reason: Chennai, IN → London, GB: 8,210 km in 45 min (10,947 km/h, max 900). Fall back to rounded coordinates when a label is missing.

Details: previous_transaction_id, previous_location, distance_km, minutes_between, speed_kmh (null when infinite), simultaneous (true when hours <= 0). JSON cannot store infinity.

### Worked examples (use these as test cases)

| Scenario | Rules triggered | Total | Level |
|---|---|---|---|
| 6 transactions in 10 min, normal amounts | velocity 40 | 40 | MEDIUM |
| 8 transactions in 10 min | velocity 70 | 70 | HIGH |
| Amount 6× median, z = 4 | unusual_amount 50 | 50 | MEDIUM |
| Amount 12× median | unusual_amount 80 | 80 | HIGH |
| New account, INR 150,000 | unusual_amount 50 (cold start) | 50 | MEDIUM |
| Chennai then London 45 min later | impossible_travel 90 | 90 | HIGH |
| Chennai then Bengaluru (≈290 km) 6 h later | none | 0 | NONE, CLEAN |
| 7 in 10 min (55) + amount 6× median (50) | velocity + unusual_amount | 100 (capped) | HIGH |



## API specification

Seven endpoints under /api cover ingestion, the review queue, the review action and two read-only views; errors use FastAPI's default {"detail": ...} body.

| Method | Path | Purpose | Success | Errors |
|---|---|---|---|---|
| GET | /api/health | Liveness check | 200 {"status": "ok"} |  |
| POST | /api/transactions | Ingest, evaluate, store, maybe alert | 201 detail | 422 invalid body |
| GET | /api/flags | Review queue (non-CLEAN only) | 200 {items, total} | 422 bad filter |
| GET | /api/transactions/{id} | Full detail for one transaction | 200 detail | 404 |
| POST | /api/transactions/{id}/review | Mark reviewed or cleared | 200 detail | 404, 409, 422 |
| GET | /api/stats | Counts for the console header | 200 |  |
| GET | /api/rules | Registered rules and their config | 200 list |  |



Also add CORSMiddleware allowing http://localhost:5173, so the console works even without the Vite proxy.

### POST /api/transactions

Request body (TransactionIn):

{
  "account_id": "ACC-1001",
  "amount": "4999.00",
  "currency": "INR",
  "merchant": "Croma Electronics",
  "latitude": 13.0827,
  "longitude": 80.2707,
  "location_label": "Chennai, IN",
  "occurred_at": "2026-10-01T09:15:00Z"
}

Validation: account_id 1–64 chars; amount > 0 with at most 2 decimals; currency 3 uppercase letters, default INR; merchant 1–128 chars; latitude and longitude in range; location_label optional; occurred_at optional, defaults to now (UTC), and naive datetimes are treated as UTC.

Flow inside services/transaction_service.py:

Convert the request to TransactionData with a new UUID.

engine.evaluate(txn, SqlHistoryProvider(session)). This runs before the insert, so history never contains the current transaction.

Insert the transaction, the assessment and its rule hits in one commit.

If should_notify, add notification_service.notify_high_risk(assessment_id) as a FastAPI BackgroundTasks task.

Return the detail response with status 201.

### GET /api/flags

| Query param | Values | Default |
|---|---|---|
| status | FLAGGED, REVIEWED, CLEARED, ALL | FLAGGED |
| risk_level | LOW, MEDIUM, HIGH | any |
| account_id | exact match | any |
| sort | score (score desc, then newest), newest | score |
| limit | 1–200 | 50 |
| offset | ≥ 0 | 0 |



ALL means every non-CLEAN status. Each item (FlagSummaryOut) has: transaction_id, account_id, amount, currency, merchant, location_label, occurred_at, total_score, risk_level, status, rules_triggered (list of rule names), notification_status (SENT, FAILED or null).

### Detail response (TransactionDetailOut)

Returned by POST /api/transactions, GET /api/transactions/{id} and the review endpoint:

{
  "transaction": { "id": "…", "account_id": "ACC-1001", "amount": "4999.00", "currency": "INR",
                   "merchant": "…", "latitude": 51.5072, "longitude": -0.1276,
                   "location_label": "London, GB", "occurred_at": "…", "created_at": "…" },
  "assessment": { "total_score": 90, "risk_level": "HIGH", "status": "FLAGGED",
                  "evaluated_at": "…", "updated_at": "…" },
  "rule_hits": [
    { "rule_name": "impossible_travel", "score": 90, "weight": 1.0, "weighted_score": 90,
      "reason": "Chennai, IN → London, GB: 8,210 km in 45 min (10,947 km/h, max 900)",
      "details": { "distance_km": 8210.4, "minutes_between": 45, "speed_kmh": 10947.2 } }
  ],
  "reviews": [],
  "notification": { "channel": "ses", "status": "SENT", "created_at": "…", "error": null },
  "allowed_actions": ["REVIEWED", "CLEARED"]
}

reviews is newest first. notification is null when no alert was sent. allowed_actions comes from the transition table, so the console never hard-codes the rules.

### POST /api/transactions/{id}/review

Body: {"action": "REVIEWED" | "CLEARED", "reviewer": "Priya", "note": "Called customer, confirmed card stolen"}. reviewer 1–64 chars; note optional, up to 1000 chars.

In one commit: check the transition (409 with Cannot mark a CLEARED transaction as REVIEWED if not allowed, also 409 for CLEAN transactions), update status and updated_at, and append a review_actions row. Returns the updated detail.

### GET /api/stats

{
  "by_status": { "CLEAN": 120, "FLAGGED": 14, "REVIEWED": 3, "CLEARED": 6 },
  "flagged_by_level": { "LOW": 2, "MEDIUM": 7, "HIGH": 5 },
  "notifications": { "SENT": 5, "FAILED": 0 }
}

flagged_by_level counts only FLAGGED items, since that is the open queue.

## Notifications

A HIGH assessment sends exactly one alert, in a background task, through whichever Notifier the NOTIFIER setting selects; a failed send is recorded, never raised into the request.

Interface — app/notifications/base.py

@dataclass(frozen=True)
class AlertPayload:
    assessment_id: str
    transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    merchant: str
    location_label: str | None
    occurred_at: datetime
    total_score: int
    risk_level: str
    hits: list[tuple[str, int, str]]   # (rule_name, score, reason)
    console_url: str                   # f"{CONSOLE_BASE_URL}/transactions/{transaction_id}"


@dataclass(frozen=True)
class SendResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class Notifier(ABC):
    channel: ClassVar[str]

    @abstractmethod
    def send_high_risk_alert(self, alert: AlertPayload) -> SendResult: ...

Implementations

| Class | File | Behaviour |
|---|---|---|
| LogNotifier | notifications/log.py | Logs the rendered text body at WARNING level; always succeeds. Default for local work and tests. |
| SESNotifier | notifications/ses.py | boto3.Session(profile_name=AWS_PROFILE or None, region_name=AWS_REGION).client("sesv2"), created once. Calls send_email with FromEmailAddress=SES_SENDER_EMAIL, ToAddresses=[ALERT_RECIPIENT_EMAIL] and a Simple message with both Text and Html bodies. Catches ClientError and BotoCoreError and returns SendResult(False, error=...). |



get_notifier(settings) in notifications/factory.py returns the right class. It fails at startup, not at first alert, when NOTIFIER is unknown or when NOTIFIER=ses and the sender or recipient address is empty.

Idempotent send — services/notification_service.py, notify_high_risk(assessment_id)

Open a fresh SessionLocal(). The request's session is already closed when a background task runs.

Load the assessment with its transaction and hits. Return if it is not HIGH.

Insert a notifications row with status="PENDING" and commit. If the unique constraint on assessment_id fails (IntegrityError), roll back and return: an alert was already claimed. This claim-first step is what makes duplicates impossible, even if the task runs twice.

Build the AlertPayload, call the notifier, then update the row to SENT with the MessageId, or FAILED with the error.

Wrap everything in try/except Exception with logger.exception; this function never raises.

Alert email — notifications/templates.py

Three pure functions, render_subject, render_text and render_html, each taking an AlertPayload, so they are easy to unit-test.

Subject: [HIGH RISK 90] ACC-1001 · INR 4,999.00 at Croma Electronics

Body, in this order: score and level; amount, merchant, location and time (UTC); one line per rule hit with its score and reason; an "Open in reviewer console" link to console_url; a footer saying the alert was generated automatically.

The HTML version uses a simple table with inline styles (email clients ignore <style> blocks) and escapes every user-supplied value with html.escape.

## Reviewer console and transaction simulator

The console has two pages, a queue and a transaction detail view; the simulator produces every fraud pattern on demand, so the whole system can be demoed in under a minute.

### Console file layout

frontend/src/
├── main.jsx                 # BrowserRouter + routes
├── App.jsx                  # layout: header, stats bar, reviewer name, <Outlet/>
├── api/client.js            # fetch wrapper; throws ApiError(status, detail)
├── pages/
│   ├── QueuePage.jsx        # route "/"
│   └── TransactionPage.jsx  # route "/transactions/:id"
├── components/
│   ├── StatsBar.jsx         ├── RiskBadge.jsx      ├── StatusBadge.jsx
│   ├── Filters.jsx          ├── FlagsTable.jsx     ├── Pagination.jsx
│   ├── RuleHitCard.jsx      ├── ReviewPanel.jsx    ├── ReviewHistory.jsx
│   └── ReviewerName.jsx
├── hooks/usePolling.js      # re-runs a loader every N ms, pauses when the tab is hidden
├── utils/format.js          # INR via Intl.NumberFormat('en-IN'), local date-time, relative time
└── styles.css

### Header (on every page)

Stats bar from GET /api/stats: open flagged total, open HIGH / MEDIUM / LOW, reviewed, cleared, alerts sent and failed.

Reviewer name: a small input saved to localStorage under reviewerName. Review buttons stay disabled, with a hint, until a name is set.

### Queue page /

Filters: status tabs (Flagged, the default, then Reviewed, Cleared, All), a risk level select, an account ID search and a sort select (Highest risk, Newest). Keep filters in the URL query string with useSearchParams, so refresh and back navigation preserve them.

Table columns: Risk (badge + score), Time, Account, Amount, Merchant, Location, Rules (one chip per triggered rule), Status, Alert (sent / failed / none). HIGH rows get a red left border. Clicking a row opens the detail page.

Pagination: Previous / Next with 50 per page and "Showing 1–50 of 132".

Refresh: poll every 15 seconds, plus a Refresh button and an "Updated 5 s ago" label.

States: loading placeholder rows; empty state No transactions match these filters; an error banner with a Retry button.

### Transaction page /transactions/:id

Back link to the queue that keeps the previous filters.

Header: amount, merchant, risk badge with score, status badge.

Transaction facts: account, time, location with coordinates, currency, transaction ID with a copy button.

Risk breakdown: one RuleHitCard per hit showing rule name, score × weight = weighted score, the reason sentence, and the key details. For impossible_travel, show previous location, distance, time between and speed; for unusual_amount, median, ratio and z-score; for velocity, count and window.

Alert line: "Alert emailed at 10:42" / "Alert failed: …" / nothing.

Review panel: a note box with a 1000-character counter and one button per allowed_actions entry: Mark reviewed ("Confirmed or escalated as suspicious") and Clear ("Legitimate, false positive"). Clear asks for confirmation. On success, re-fetch and show a short success message; on 409, show the server's message and re-fetch.

Review history: newest first, with reviewer, action, from → to status, note and time.

Colour never carries meaning alone: every badge also has its text. HIGH is red, MEDIUM amber, LOW grey; FLAGGED amber, REVIEWED blue, CLEARED green.

### Simulator — simulator/generate_transactions.py

A command-line script using httpx that posts to the running API and prints a pass/fail table, so it doubles as an end-to-end test.

python simulator/generate_transactions.py --scenario all --base-url http://localhost:8000 --seed 42

It keeps a fixed list of cities (Chennai, Mumbai, Delhi, Bengaluru, Kolkata, London, Dubai, Singapore) with coordinates, and a list of merchants. Every occurred_at is set explicitly, relative to now.

| Scenario | Account(s) | What it sends | Expected final result |
|---|---|---|---|
| baseline | ACC-1001 to ACC-1010 | 20 transactions each over the past 30 days in a home city, INR 200–5,000 | All CLEAN |
| velocity | ACC-2001 | 10 baseline transactions, then 8 in 6 minutes | Last one HIGH (score 70) |
| amount | ACC-3001, ACC-3002 | ACC-3001: baseline, then INR 60,000. ACC-3002: brand-new account, INR 150,000 | HIGH (80); MEDIUM (50) |
| travel | ACC-4001 | Baseline in Chennai, a Chennai purchase 45 min ago, then London now | HIGH (90) |
| combo | ACC-5001 | Baseline, then 7 transactions in 5 minutes, the last one INR 20,000 | HIGH (capped at 100) |
| all | all of the above | Runs every scenario in order | Every row passes |



The script exits with code 1 if any actual risk level differs from the expected one. Running it twice adds more history; delete backend/fraud.db and restart the API for a clean demo.

## Testing plan

Tests never touch real AWS or the real fraud.db: rules use an in-memory history, API tests use a temporary SQLite file, and SES is stubbed. Target at least 85% line coverage on app/engine/ and app/services/ (pytest --cov=app, adding pytest-cov).

Fixtures — tests/conftest.py and tests/fakes.py

InMemoryHistoryProvider: holds a list of TransactionData and implements the three history methods with the exact semantics above.

make_txn(**overrides): a factory with sensible defaults (Chennai, INR 1,000, now).

client: a TestClient whose app uses a temporary SQLite file, overrides NOTIFIER to a FakeNotifier that records every alert it receives, and builds the engine from a test rules.yaml.

Unit tests — rules (tests/rules/)

| Rule | Cases |
|---|---|
| velocity | exactly 5 in window → not triggered; 6 → 40; 8 → 70; 12 → 100 (cap); transactions just outside the window are not counted; other accounts are not counted |
| unusual_amount | cold start below and at the absolute threshold; ratio exactly 5 with z below 6 → 50; ratio 10 → 80; z ≥ 3 with a low ratio → 50; all-identical history (stdev 0) with a slightly higher amount → not triggered; lower-than-usual amount → not triggered |
| impossible_travel | no previous transaction; distance under 100 km → not triggered; Chennai → Bengaluru in 6 h → not triggered; Chennai → London in 45 min → 90; same timestamp, 500 km apart → 90 with simultaneous: true; speed between 900 and 1800 km/h → 70 |
| geo_utils | haversine Chennai → London within 1% of 8,200 km; same point → 0 |



Unit tests — engine and registry (tests/engine/)

Score aggregation, weighting and the cap at 100; each risk-level boundary (39/40, 69/70).

A rule that raises is skipped and the others still run.

Disabled rules in YAML do not run; YAML params override defaults; an unknown rule name in YAML only warns.

Extensibility test (the one that proves the requirement): inside the test, define a DummyRule with @register_rule, build a new engine, and assert it runs, without touching engine.py. Clean the registry up afterwards with a fixture.

Registering two rules with the same name raises ValueError.

API integration tests (tests/api/)

POST a normal transaction → 201, CLEAN, absent from /api/flags.

POST the travel pair → second one HIGH, listed first in /api/flags, FakeNotifier received exactly one alert.

Validation: negative amount, latitude 95, 3-decimal amount, empty merchant → 422.

Review: FLAGGED → REVIEWED → CLEARED succeeds and writes two review_actions; CLEARED → REVIEWED → 409; reviewing a CLEAN transaction → 409; unknown ID → 404.

Filters and sorting on /api/flags; limit and offset; /api/stats counts after a known set of inserts; /api/rules lists all three rules.

Notification tests (tests/notifications/)

notify_high_risk called twice for one assessment → one alert and one notifications row.

Notifier returns failure → row is FAILED with the error; nothing raises.

SESNotifier with botocore.stub.Stubber: correct FromEmailAddress, recipient, subject and both bodies; a stubbed ClientError becomes SendResult(success=False).

Templates: the subject format; HTML escapes <script> in a merchant name; the console link is present.

Frontend: no automated tests required. Use the manual checklist in the build phases, driven by the simulator.

## Build phases

Ten phases, backend first: each builds on the last and ends with passing tests and a commit. Hand Claude Code one phase at a time and tick its "Done when" boxes yourself before moving on.

### Phase 0 — Scaffold

Build: the full backend/app/ package tree (api/, engine/rules/, notifications/, services/, repositories/, each with __init__.py); config.py with a Settings class covering every .env variable; database.py with engine, SessionLocal, Base and a get_db dependency; main.py with a lifespan that creates tables, CORS, and GET /api/health; rules.yaml; pytest.ini with pythonpath = .; one health test.

☐ uvicorn app.main:app --reload starts with no errors

☐ http://localhost:8000/api/health returns {"status": "ok"}

☐ pytest -q passes

### Phase 1 — Data model and repositories

Build: enums in app/enums.py; the five models with indexes and the unique constraints; repository functions for insert and query; SqlHistoryProvider.

☐ Deleting fraud.db and restarting recreates all five tables

☐ Tests confirm count_in_window, recent_amounts and previous_transaction follow the exact semantics in this plan

### Phase 2 — Rule engine core

Build: base.py, registry.py, config loading, engine.py with EngineResult and describe(), tests/fakes.py. No real rules yet.

☐ Aggregation, level-boundary and broken-rule tests pass

☐ The extensibility test passes: a rule defined only in the test file runs without editing engine.py

### Phase 3 — The three rules

Build: geo_utils.py, velocity.py, unusual_amount.py, impossible_travel.py and their tests.

☐ Every row of the worked-examples table is an automated test, and all pass

☐ git diff for this phase shows no change to engine.py

### Phase 4 — API and services

Build: Pydantic schemas, transaction_service, review_service with the transition table, query and stats functions, and all seven routes. The engine is created in the lifespan. Leave a clearly marked hook where Phase 5 will schedule the alert.

☐ All API integration tests pass (alert assertions are added in Phase 5)

☐ In Swagger at /docs, posting the Chennai → London pair returns HIGH for the second transaction

### Phase 5 — Notifications

Build: base.py, log.py, ses.py, factory.py, templates.py, notification_service.py; wire the background task; add notification data to the detail and flags responses.

☐ Notification tests pass, including the double-call idempotency test

☐ With NOTIFIER=log, a HIGH transaction prints the alert in the server log

☐ With NOTIFIER=ses, a real alert email arrives in the verified inbox

### Phase 6 — Simulator

Build: simulator/generate_transactions.py with every scenario and the pass/fail summary.

☐ On a fresh database, --scenario all prints every row as passing and exits 0

### Phase 7 — Console: layout and queue page

Build: routing, api/client.js, header with stats bar and reviewer name, filters in the URL, table, pagination, polling, and loading, empty and error states.

☐ After running the simulator, the queue shows flagged items sorted by risk, HIGH first

☐ Each filter changes the list and survives a page refresh

☐ Stopping the backend shows the error banner, and Retry recovers once it restarts

### Phase 8 — Console: detail page and review actions

Build: TransactionPage, rule hit cards, review panel driven by allowed_actions, review history.

☐ Rule hit cards show the reason and details for each of the three rules

☐ Flagged → Mark reviewed → Clear works, and both actions appear in the history with the note

☐ A cleared transaction shows no action buttons

☐ Actions are disabled until a reviewer name is set

### Phase 9 — Documentation and polish

Build: README.md (next section) and docs/ADDING_A_RULE.md; remove dead code and stray prints; run pytest and the simulator one last time.

☐ A fresh clone set up by following only the README works end to end

☐ Following ADDING_A_RULE.md adds a working fourth rule without editing engine.py

## Hardening phases (10–14)

Five more phases lift the four metrics that scored below 8. Each one replaces a specific weak point from the core build rather than adding features. Run them only after Phase 9 passes; each ends with passing tests and a commit, like the core phases.

| Metric | Before | After | What fixes it |
|---|---|---|---|
| Reliability | 6 | 9 | Outbox worker with retries replaces background tasks; idempotent ingestion; per-account locking; optimistic review locking; migrations; readiness checks |
| Security | 5 | 8 | Reviewer login with roles; API keys for ingestion; lockout and rate limits; masked alert emails; tighter IAM; secret and dependency scanning in CI |
| Rule realism | 6 | 8 | Outlier-proof amount statistics; travel rule ignores online purchases; short and long velocity windows; new card-testing rule; shadow mode; per-rule precision from reviewer decisions |
| Scalability | 5 | 8 | Postgres; stateless API running several workers; worker replicas that never double-send; keyset pagination; targeted indexes; data retention; a measured load test |



Why not 10: no machine-learning model, device or IP signals (realism); no MFA or SSO (security); rules still run inside the request, and nothing is partitioned or streamed (scalability). Those belong to a real production system, not this project.

Order matters: Phase 10 comes first because Postgres provides the row-locking features that Phases 11 and 14 depend on.

New packages: alembic, psycopg[binary], argon2-cffi, pyjwt, slowapi; dev-only ruff, pip-audit, locust. New .env variables are listed in the phase that introduces them.

### Phase 10 — Postgres, migrations and Docker Compose

Move the real database to Postgres, manage its schema with Alembic, and run the whole system with one command. SQLite stays supported for quick local runs and unit tests.

Portable column types in models.py, so one model file works on both databases:

JSON().with_variant(JSONB(), "postgresql") for rule_hits.details.

Enum(..., native_enum=False, length=16) for every enum. Enums are stored as strings, so adding a value later needs no enum migration.

Engine setup in database.py, chosen from DATABASE_URL:

Postgres: pool_size=10, max_overflow=20, pool_pre_ping=True.

SQLite: check_same_thread=False, and a connect event that runs PRAGMA journal_mode=WAL and PRAGMA busy_timeout=5000, so readers don't block the writer.

Alembic: run alembic init migrations inside backend/. env.py reads the URL from Settings and uses Base.metadata. Autogenerate 0001_initial, then read it and fix anything autogenerate got wrong. Remove create_all from app startup; tests may still use create_all on their temp database.

backend/Dockerfile: python:3.12-slim, install requirements, copy app/, migrations/, alembic.ini and rules.yaml, and run as a non-root user.

frontend/Dockerfile: multi-stage. Build with Node, then serve dist/ from nginx:alpine. nginx.conf proxies /api/ to http://api:8000 and falls back to index.html for client-side routes.

docker-compose.yml in the repo root:

| Service | Image / build | Purpose |
|---|---|---|
| db | postgres:16 | Named volume pgdata; healthcheck pg_isready |
| migrate | backend image | Runs alembic upgrade head once, after db is healthy |
| api | backend image | uvicorn app.main:app --host 0.0.0.0 --port 8000; starts after migrate succeeds |
| worker | backend image | Added in Phase 11 |
| frontend | frontend image | nginx on host port 8080 |



AWS credentials in containers: mount the host's AWS folder read-only into api (and later worker), for example ${HOME}/.aws:/home/app/.aws:ro. On Windows, use the full path to %USERPROFILE%\.aws. Never bake keys into an image.

New .env variables: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, and a DATABASE_URL of the form postgresql+psycopg://USER:PASSWORD@db:5432/DB inside Compose (localhost instead of db when the API runs outside Docker).

☐ docker compose up --build serves the console at http://localhost:8080, and it lists data from the API

☐ alembic check reports no difference between models and migrations

☐ The simulator's --scenario all passes against Postgres

☐ Data survives docker compose down followed by up (without -v)

☐ pytest still passes on SQLite

### Phase 11 — Reliability

No alert is lost when the server stops, no duplicate request creates a duplicate transaction, and two simultaneous requests can't hide each other from the rules. Migration 0002_reliability carries every schema change below.

A. Outbox worker replaces background tasks

The alert becomes a database row written in the same commit as the assessment, and a separate worker process sends it. If anything crashes, the row is still there and gets sent later.

notifications gains attempts (int, default 0), next_attempt_at, locked_until (nullable), last_error, sent_at and updated_at. Status values become PENDING, SENT and DEAD; migrate any old FAILED row to PENDING. Add a partial index on (next_attempt_at) where status = 'PENDING'.

transaction_service: when the result is HIGH, insert a PENDING notification with next_attempt_at = now in the same commit. Remove BackgroundTasks completely.

app/worker.py, run as python -m app.worker. It loops every OUTBOX_POLL_SECONDS and calls a testable process_batch(now):

Claim up to 10 due rows in one short transaction, then set locked_until = now + OUTBOX_LEASE_SECONDS and commit. On Postgres the claim query ends in FOR UPDATE SKIP LOCKED, so several workers never take the same row.

SELECT id FROM notifications
WHERE status = 'PENDING' AND next_attempt_at <= now()
  AND (locked_until IS NULL OR locked_until < now())
ORDER BY next_attempt_at
LIMIT 10
FOR UPDATE SKIP LOCKED;

Send each row outside any database transaction.

Record: success → SENT with sent_at and the message ID. A retryable failure (throttling, timeouts, network, 5xx) → attempts + 1, last_error, and next_attempt_at = now + 1 min × 2^(attempts − 1), capped at 60 min, with ±20% jitter. After OUTBOX_MAX_ATTEMPTS → DEAD. A permanent failure (MessageRejected, MailFromDomainNotVerified, AccessDenied) → DEAD at once.

On SIGTERM, finish the current row and exit cleanly.

Each loop upserts a worker_heartbeats row (worker_id, last_seen).

Delivery is at-least-once: if a worker dies after SES accepts an email but before it records SENT, the lease expires and the email is sent again. State this in the README; a duplicate alert is better than a missing one.

POST /api/notifications/{id}/retry moves a DEAD row back to PENDING with attempts = 0 (409 for any other status). Phase 12 restricts it to admins.

/api/stats gains outbox: {pending, dead, oldest_pending_seconds} and worker_last_seen_seconds. The console header shows a warning when the worker hasn't been seen for over 30 seconds or anything is DEAD.

Compose gets a worker service running python -m app.worker, with the same AWS mount as api.

B. Idempotent ingestion

Payment systems resend requests after timeouts. Without protection, one retried purchase counts twice and can trigger the velocity rule by itself.

TransactionIn gains optional external_id (1–64 chars). transactions gains external_id (unique, nullable) and payload_hash (SHA-256 of the request body as canonical JSON: sorted keys, amount as a string).

Known external_id with the same hash → return the stored detail with 200 and header Idempotent-Replay: true. Same external_id with a different hash → 409 external_id already used with different data.

Two identical requests at the same moment: the second insert fails on the unique constraint. Catch IntegrityError, roll back, and return the stored row as a replay.

The simulator sends a UUID external_id with every transaction, and a new --retry-test flag sends each one twice to show that the replay creates nothing new.

C. One account at a time

Two transactions for the same account arriving together would each be evaluated without seeing the other. Evaluation and insert therefore run inside one database transaction holding a per-account lock:

repositories/locks.py → lock_account(session, account_id). On Postgres it runs SELECT pg_advisory_xact_lock(hashtextextended(:account_id, 0)), which only blocks requests for the same account and is released automatically at commit or rollback.

On SQLite it does nothing. Instead, database.py uses SQLAlchemy's documented pysqlite recipe (set the driver's isolation_level = None on connect, then emit BEGIN IMMEDIATE on each begin event), so every transaction takes the database write lock.

transaction_service order: begin → lock_account → evaluate → insert transaction, assessment, hits and outbox row → commit.

D. Two reviewers, one transaction

risk_assessments gains version (int, not null, default 1), configured as SQLAlchemy's version_id_col, so every update checks and increments it.

The detail response includes version. The review body requires expected_version; a mismatch, or SQLAlchemy's StaleDataError, returns 409 This transaction was updated by someone else. Reload and try again.

The console re-fetches on that 409 and shows the message above the review panel.

E. Health, timeouts, logs and errors

GET /api/health/live always returns 200 (keep /api/health as an alias). GET /api/health/ready checks SELECT 1, that the database is at the Alembic head revision, and that the notifier is configured; it returns 503 with the failing check named.

SES client: botocore.config.Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 3, "mode": "standard"}).

Request-ID middleware: reuse the incoming X-Request-ID or create a UUID, add it to every log line through a contextvars logging filter, and return it as a response header.

LOG_FORMAT=json switches to one-JSON-object-per-line logs with a small logging.Formatter subclass (no new dependency).

A global exception handler returns 500 {"detail": "Internal error", "request_id": "..."}. Tracebacks go only to the logs.

The engine logs a warning when a single rule takes more than 50 ms.

New .env variables: OUTBOX_POLL_SECONDS=2, OUTBOX_LEASE_SECONDS=60, OUTBOX_MAX_ATTEMPTS=6, LOG_FORMAT=text.

Tests to add: a HIGH ingest creates one PENDING row and sends nothing during the request; a notifier that fails twice then succeeds ends SENT after 3 attempts at the right backoff times (inject the clock); a permanent error goes straight to DEAD; an expired lease is reclaimed; replay returns 200 with one stored row; a changed payload returns 409; two reviews with the same expected_version → the second gets 409; /ready returns 503 with a broken database URL. Behind a postgres pytest marker: 10 threads posting for one account at once → the highest velocity count recorded is 10.

☐ Stopping the worker, creating a HIGH transaction, then starting the worker still delivers the alert

☐ With a wrong sender address, the alert ends DEAD with a readable error, and the console shows it

☐ --retry-test in the simulator creates no duplicate transactions

☐ Two browser tabs reviewing the same transaction: the second gets the "updated by someone else" message

☐ Every log line for one request shares its request ID

### Phase 12 — Security

Every request is authenticated: reviewers log in, machines use API keys, and the audit trail records who really acted instead of a typed name. Migration 0003_security adds users, api_keys and audit_events, plus review_actions.reviewer_id.

A. Who can call what

| Endpoint | Public | API key | REVIEWER | ADMIN |
|---|---|---|---|---|
| GET /api/health/* | yes |  |  |  |
| POST /api/auth/login | yes (rate limited) |  |  |  |
| POST /api/auth/logout, GET /api/auth/me |  |  | yes | yes |
| POST /api/transactions |  | yes |  |  |
| GET /api/flags, /api/transactions/{id}, /api/stats, /api/rules, /api/rules/metrics |  |  | yes | yes |
| POST /api/transactions/{id}/review |  |  | yes | yes |
| POST /api/notifications/{id}/retry |  |  |  | yes |



Implement this as FastAPI dependencies, require_user(*roles) and require_api_key, attached to each router. A missing or invalid credential returns 401; the wrong role returns 403.

B. Reviewer login

users: id, username (unique, 3–32 chars), password_hash, role (ADMIN or REVIEWER), is_active, failed_logins, locked_until, token_version (int), created_at, last_login_at.

Passwords: Argon2id via argon2-cffi PasswordHasher, minimum 12 characters. When the username doesn't exist, still verify against a fixed dummy hash, so response time doesn't reveal which usernames exist.

POST /api/auth/login returns the generic Invalid username or password on any failure. After 5 failures the account is locked for 15 minutes.

On success, set cookie fre_session: a JWT (PyJWT, HS256, JWT_SECRET) with sub, role, tv (the user's token_version), iat and exp = SESSION_HOURS (default 8). Cookie flags: HttpOnly, SameSite=Strict, Path=/api, and Secure when COOKIE_SECURE=true. JavaScript never sees the token, so an XSS bug can't steal it.

Every authenticated request loads the user and rejects the token when the user is inactive or tv ≠ token_version. Deactivating a user or bumping token_version ends all their sessions immediately.

POST /api/auth/logout clears the cookie. GET /api/auth/me returns {username, role}.

CSRF: SameSite=Strict does most of the work. In addition, middleware rejects POST, PUT, PATCH and DELETE requests carrying the session cookie with 403 unless the Origin header is in ALLOWED_ORIGINS.

The review body loses reviewer. The service takes the user from the token and stores both reviewer_id and a reviewer name snapshot.

C. API keys for ingestion

api_keys: id, name, prefix (first 8 characters, for lookup and display), key_hash (SHA-256), is_active, created_at, last_used_at.

Clients send X-API-Key. Look the key up by prefix, compare hashes with secrets.compare_digest, and update last_used_at.

The simulator reads its key from --api-key or the FRE_API_KEY environment variable.

D. Admin command line — python -m app.cli

create-user --username priya --role REVIEWER prompts for the password twice. There are no default accounts or passwords anywhere.

deactivate-user --username priya

create-api-key --name simulator prints the full key once; only its hash is stored.

revoke-api-key --prefix ab12cd34

E. Limits and hardening

slowapi rate limits: login 10 per minute per IP; ingestion 600 per minute per API key; everything else 120 per minute per IP. Storage comes from RATE_LIMIT_STORAGE_URI (default memory://; see Phase 14).

Request bodies over 64 KB → 413.

Response headers: X-Content-Type-Options: nosniff, X-Frame-Options: DENY, Referrer-Policy: no-referrer, and Cache-Control: no-store on /api. The nginx config adds Content-Security-Policy: default-src 'self'; frame-ancestors 'none'.

/docs and /openapi.json are served only when DOCS_ENABLED=true. Compose sets it to false.

CORS allows only ALLOWED_ORIGINS, with credentials.

audit_events (append-only; no endpoint can change it): login success and failure, logout, user and API-key creation or revocation, notification retries. Each row has event_type, user_id, ip, details and created_at.

Logs carry transaction IDs, never full request bodies, and never passwords, tokens or keys.

F. Less data in email

Email is the least protected place this data goes. Alerts now mask the account (••••1001), leave out coordinates, and drop the account from the subject: [HIGH RISK 90] INR 4,999.00 at Croma Electronics. Full details live behind the console login.

G. Tighter AWS permissions

Replace the IAM user's policy so it can send only from the alert address:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "arn:aws:ses:ap-south-1:<ACCOUNT_ID>:identity/*",
      "Condition": { "StringEquals": { "ses:FromAddress": "<SES_SENDER_EMAIL>" } }
    }
  ]
}

Rotate the access key every 90 days. When deployed on AWS, use an IAM role on the server instead of any access key.

H. Continuous checks — .github/workflows/ci.yml

Backend job: ruff check, pytest, pip-audit -r requirements.txt.

Frontend job: npm ci, npm run build, npm audit --audit-level=high.

Secrets job: gitleaks over the full history.

I. Console changes

Add a /login page and an AuthContext filled from /api/auth/me. Any 401 redirects to /login and returns to the original page after login. The header shows the username, role and a Logout button; the typed reviewer-name box is removed. Admins see a Retry button on DEAD alerts.

New .env variables: JWT_SECRET (generate with python -c "import secrets; print(secrets.token_urlsafe(48))"), SESSION_HOURS=8, COOKIE_SECURE=false (true behind HTTPS), ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8080, DOCS_ENABLED=true, RATE_LIMIT_STORAGE_URI=memory://. The app refuses to start when JWT_SECRET is shorter than 32 characters.

Tests to add: every protected route returns 401 without credentials; a REVIEWER gets 403 on retry; an API key can't read flags and a session can't ingest; a wrong password 5 times locks the account; an unknown username takes about as long as a wrong password; a token with an old tv is rejected; a cross-origin POST with the cookie gets 403; the review stores the logged-in user; alert emails contain no full account ID or coordinates.

☐ The console can't be used without logging in, and Logout really ends the session

☐ review_actions shows the logged-in user, not a typed name

☐ The simulator fails with 401 without its API key and works with it

☐ CI passes on GitHub with no high-severity audit findings and no secrets detected

☐ Sending from any other address fails with the new IAM policy

### Phase 13 — Smarter rules

The rules stop being fooled by the three things that cause most false alarms in simple fraud systems: one past big purchase skewing an account's average, online purchases reporting the merchant's location instead of the cardholder's, and fixed single windows. A fourth rule arrives without touching engine.py, and reviewer decisions now measure how good each rule is. Migration 0004_rules adds transactions.channel (default POS) and rule_hits.shadow (default false).

A. Richer input and history

TransactionIn, transactions and TransactionData gain channel: POS (card present in a shop), ATM, or ONLINE (card not present). Default POS.

HistoryProvider gains two optional arguments, so existing rules keep working unchanged:

count_in_window(account_id, start, end, max_amount=None) counts only amounts ≤ max_amount when given.

previous_transaction(account_id, at, channels=None) considers only the given channels when given.

B. Unusual amount, version 2 (same file and name; new parameters)

Mean and standard deviation are dragged around by a single past big purchase. Median and MAD (median absolute deviation) ignore outliers, and working in log space fits how spending varies: a jump from ₹200 to ₹400 is as unusual as one from ₹2,000 to ₹4,000.

unusual_amount:
  params: { min_history: 5, lookback: 50, mz_threshold: 3.5, min_mad: 0.1,
            max_multiplier: 3, high_ratio: 10, min_amount: 5000, absolute_threshold: 100000 }

Cold start (fewer than min_history past amounts): unchanged, score 50 at or above absolute_threshold.

amount < min_amount → not triggered. Small purchases are not worth a reviewer's time.

Take h = ln(past amounts), med = median(h), mad = max(median(|h − med|), min_mad).

Modified z-score mz = 0.6745 × (ln(amount) − med) / mad. The 0.6745 constant and the 3.5 cut-off are the standard Iglewicz–Hoaglin outlier test.

Triggered when mz ≥ mz_threshold, or when amount ≥ max_multiplier × the account's largest past amount.

ratio = amount / e^med (the typical amount). Score 80 when ratio ≥ high_ratio, otherwise 50.

Details: modified_z, typical_amount, ratio, largest_past_amount, history_size.

The same amount now gets a different verdict for a steady spender and a variable one, which is the point of the change. These replace the old unusual_amount rows in the worked examples:

Steady history (10 amounts): 800, 900, 950, 1,000, 1,000, 1,050, 1,100, 1,200, 1,300, 1,500 → typical ≈ INR 1,025, log MAD ≈ 0.103.

Variable history (10 amounts): 300, 700, 1,200, 1,800, 2,500, 2,600, 3,200, 3,900, 4,500, 5,000 → typical ≈ INR 2,550, log MAD ≈ 0.497.

| History | Amount (INR) | Modified z | ≥ 3 × largest? | Result |
|---|---|---|---|---|
| Steady | 4,000 | not computed | not checked | Below min_amount → not triggered |
| Steady | 6,000 | 11.6 | yes (4,500) | Ratio 5.9 → 50, MEDIUM |
| Steady | 15,000 | 17.6 | yes | Ratio 14.6 → 80, HIGH |
| Variable | 6,000 | 1.2 | no (15,000) | Not triggered |
| Variable | 15,000 | 2.4 | yes (exactly 15,000) | Ratio 5.9 → 50, MEDIUM |
| Variable | 60,000 | 4.3 | yes | Ratio 23.5 → 80, HIGH |



C. Impossible travel, version 2

An online purchase's location is usually the merchant's server or head office, not the cardholder, so comparing it with a shop purchase creates false alarms.

If the current transaction is ONLINE, the rule does not trigger (details: skipped: "online").

Otherwise compare with previous_transaction(..., channels={"POS", "ATM"}). Everything else is unchanged.

Test: POS in Chennai, ONLINE "London" 10 minutes later, then POS in London 30 minutes after that → only the third transaction is flagged, measured against Chennai.

D. Velocity, version 2

One window misses slow draining. The rule takes a list of windows, scores each with the existing formula, and keeps the highest; the reason names the worst window.

velocity:
  params:
    windows:
      - { minutes: 10, max_count: 5 }
      - { minutes: 1440, max_count: 25 }

Old single-window parameters (window_minutes, max_transactions) still load as a one-item list.

E. New rule: card testing — rules/card_testing.py, name card_testing

Criminals often check a stolen card with a few tiny charges before a large one. This rule is added as one new file, which proves the extensibility requirement a second time with a real rule.

card_testing:
  params: { window_minutes: 15, small_amount: 100, min_small_count: 3, big_amount: 2000 }

prior_small = history.count_in_window(account_id, occurred_at − window, occurred_at, max_amount=small_amount).

Current amount ≤ small_amount: triggered when prior_small + 1 ≥ min_small_count, score 60.

Current amount ≥ big_amount: triggered when prior_small ≥ min_small_count, score 90. This is the moment that matters.

Reason: 3 charges under INR 100 in 15 min, then INR 25,000.00.

New simulator scenario card_testing (ACC-6001): baseline, three charges of INR 10–50 within 5 minutes, then INR 25,000 → expected HIGH.

F. Shadow mode

A new rule should prove itself before it can flag anyone. Each rule in rules.yaml gets mode: active | shadow (default active).

Shadow hits are stored with shadow = true but add nothing to the score, level or status. If only shadow rules fire, the transaction stays CLEAN with its hits saved.

The detail page shows shadow hits greyed out and labelled "shadow".

ADDING_A_RULE.md gains the launch process: ship in shadow, watch its volume and precision for a week, then switch it to active.

G. Rule precision from reviewer decisions

Reviewers already record whether each flag was real (REVIEWED) or a false alarm (CLEARED). This turns those decisions into a score for each rule.

GET /api/rules/metrics?days=30 returns per rule: hits, shadow_hits, confirmed (flags now REVIEWED), cleared, pending (still FLAGGED), and precision = confirmed / (confirmed + cleared), or null with no decisions yet. One GROUP BY over rule_hits joined to risk_assessments.

A flag with several rules counts for each of them; say so on the page.

New console page /rules: a table of rules with mode, weight, parameters (read-only), 30-day hits, shadow hits and precision, plus one line of guidance: low precision means the rule mostly flags legitimate spending, so raise its threshold or lower its weight.

Tests to add: every row of the new amount table; ONLINE skip and the three-step travel case; the 24-hour velocity window; both card-testing scores; a shadow hit leaves the score unchanged; only-shadow hits leave the transaction CLEAN; metrics on a fixed dataset with known decisions; old velocity config still loads.

☐ git diff for this phase shows no change to engine.py, apart from shadow-mode handling

☐ Simulator --scenario all, including card_testing, passes

☐ Clearing and confirming a few flags visibly changes precision on the /rules page

☐ Switching card_testing to shadow and restarting stops it from flagging, while its hits still appear greyed out

### Phase 14 — Scale, and prove it

Run several API processes and workers safely, keep the busiest queries on indexes, stop the database from growing forever, and replace "it should scale" with measured numbers. Migration 0005_scale adds the indexes.

A. Several processes, one truth

The API is already stateless: sessions live in cookies, and the rule engine is read-only. Run it as uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 (API_WORKERS in Compose).

Rate-limit counters must be shared between processes. Add a redis:7 service to Compose and set RATE_LIMIT_STORAGE_URI=redis://redis:6379/0. memory:// stays the default for local runs.

Workers scale with docker compose up --scale worker=2. SKIP LOCKED from Phase 11 guarantees each alert is claimed once.

Connection budget: Postgres allows 100 connections by default. Set DB_POOL_SIZE=5 and DB_MAX_OVERFLOW=5 per process: 4 API processes × 10 + 2 workers × 10 = 60 at most, leaving headroom for migrations and admin sessions.

B. Indexes for the hot paths

| Query | Index |
|---|---|
| Rule history (every ingest) | transactions (account_id, occurred_at DESC) INCLUDE (amount, channel), replacing the Phase 1 composite index |
| Open queue, sorted by risk | risk_assessments (total_score DESC, evaluated_at DESC, id) where status = 'FLAGGED' |
| Other status tabs | risk_assessments (status, evaluated_at DESC) |
| Rule metrics | rule_hits (rule_name, assessment_id) |
| Outbox claim | the partial index from Phase 11 |



The queue's "newest" sort switches from occurred_at to evaluated_at so it stays within one table and one index. Confirm with EXPLAIN ANALYZE on a database of at least 100,000 transactions that each query above uses an index scan, and paste the plans into docs/PERFORMANCE.md.

C. Keyset pagination for the queue

Offset pagination slows down on later pages and skips or repeats rows when new flags arrive mid-browse.

GET /api/flags drops offset and returns next_cursor: an opaque base64 of the last row's sort key (total_score, evaluated_at, id).

The next page adds cursor=... and filters with a row comparison, for example WHERE (total_score, evaluated_at, id) < (:score, :evaluated_at, :id) for the risk sort. Both Postgres and SQLite support row values.

total is returned only on the first page (no cursor).

The console keeps a stack of cursors for Previous and Next.

Test: page through 237 rows while inserting new flags between requests; every original row appears exactly once.

D. Cheaper polling

GET /api/stats and the first page of GET /api/flags return an ETag computed from the latest updated_at and row count for that filter. The console sends If-None-Match and gets a body-less 304 when nothing changed. Server-sent events are left as a stretch goal.

E. Data retention

python -m app.cli purge --older-than-days 180 deletes CLEAN transactions older than the cutoff, with their assessments, in batches of 5,000 rows per commit.

It never deletes FLAGGED, REVIEWED or CLEARED records; those are evidence.

An account idle longer than the cutoff simply starts again from the amount rule's cold start. Document this.

Schedule it daily (cron on the host, or a Compose service with a sleep loop). RETENTION_DAYS sets the default.

F. Load test — loadtest/locustfile.py

User classes: an ingest client across 1,000 accounts (95% normal purchases; 5% velocity bursts, impossible travel, large amounts and card testing) and 10 reviewers polling /api/flags and /api/stats every 15 seconds.

Use a dedicated API key. Make the ingestion limit configurable (INGEST_RATE_LIMIT, default 600/minute) and raise it for the test run only, or the Phase 12 limit will cap the test.

Run: locust -f loadtest/locustfile.py --headless -u 200 -r 20 -t 2m --host http://localhost:8080 --csv loadtest/results/run1.

Targets on a laptop running the full Compose stack (4 API workers, 2 queue workers, one Postgres): at least 150 ingest requests per second, p95 latency under 200 ms, 0% errors, and the outbox backlog empty within 60 seconds of the run ending. These are targets, not promises: record the actual numbers, the machine's CPU and RAM, and whether each target was met in docs/PERFORMANCE.md and the README. If a target is missed, profile with py-spy and fix the biggest cost before touching settings.

☐ With --scale worker=2, every HIGH transaction from a load test has exactly one SENT notification row and one alert

☐ EXPLAIN ANALYZE plans in docs/PERFORMANCE.md show index scans for all five hot queries

☐ The keyset pagination test passes

☐ purge leaves every non-CLEAN record in place

☐ docs/PERFORMANCE.md contains a real load-test result with machine details

## Definition of done, README and stretch goals

The project is done when every requirement below points to working code and a passing test or a manual check.

| Requirement | Where it is met | Proof |
|---|---|---|
| Rule engine for transaction risk | app/engine/engine.py | Engine tests |
| Velocity, unusual amount, impossible travel rules | app/engine/rules/ | Rule tests + worked examples |
| New rules without modifying the core | Registry, auto-discovery, rules.yaml | Extensibility test + ADDING_A_RULE.md |
| Persist transactions and fraud flags | SQLite, five tables | API tests; fraud.db survives restarts |
| React reviewer console | frontend/ | Phase 7–8 checks |
| Display flagged transactions | Queue page + GET /api/flags | Simulator run, then the queue |
| Mark reviewed or cleared | Review panel + POST /api/transactions/{id}/review | Review tests + Phase 8 check |
| AWS SES alert above the high-risk threshold | SESNotifier + idempotent notification_service | Stubber tests + a real email received |



README.md must contain, in this order: a one-paragraph overview; the architecture diagram; quick start (clone, backend, frontend, simulator, in under 10 commands); environment variables; how scoring and risk levels work; the API table; running tests; AWS SES setup (short, linking the setup guide); design decisions and trade-offs; known limitations.

docs/ADDING_A_RULE.md walks through adding this fourth rule as the worked example. One new file, no other changes:

# app/engine/rules/blocked_merchant.py
from app.engine.base import Rule, RuleResult, TransactionData, HistoryProvider
from app.engine.registry import register_rule


@register_rule
class BlockedMerchantRule(Rule):
    name = "blocked_merchant"
    description = "Transaction at a merchant on the blocked list."
    default_params = {"merchants": ["Shady Crypto Exchange"]}

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        blocked = {m.lower() for m in self.params["merchants"]}
        if txn.merchant.lower() in blocked:
            return RuleResult(self.name, True, 60, f"Merchant '{txn.merchant}' is on the blocked list")
        return RuleResult(self.name, False)

Known limitations to state honestly in the README. After Phase 9 only: no reviewer authentication, SQLite, alerts lost if the server stops mid-send, offset pagination. Phases 10–14 remove all of those. What remains after Phase 14: no MFA or single sign-on; one shared JWT signing secret; at-least-once alert delivery, so a rare duplicate email is possible; single currency; rules run inside the ingest request; no machine-learning, device or IP signals; one Postgres instance with no replicas or partitioning.

Stretch goals, only after Phase 14:

☐ SNSNotifier publishing to a topic (NOTIFIER=sns, SNS_TOPIC_ARN) to show the notifier layer is pluggable too

☐ Live queue updates with server-sent events backed by Postgres LISTEN/NOTIFY

☐ TOTP-based MFA for reviewer logins

☐ Multi-currency support with a daily exchange-rate table

☐ Dashboard charts: flags per hour and hits per rule

☐ Deploy on AWS: ECS Fargate for API and worker, RDS Postgres, an IAM role for SES instead of access keys