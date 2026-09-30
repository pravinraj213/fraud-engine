# fraud-rule-engine

Fraud rule engine (FastAPI + SQLAlchemy + SQLite) with a React (Vite) reviewer console and AWS SES alerts.
The full spec is docs/IMPLEMENTATION_PLAN.md. Follow it exactly; if something is ambiguous, ask before inventing.
Progress and decisions are logged in docs/DEVLOG.md; keep it and the README file guide up to date.

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
