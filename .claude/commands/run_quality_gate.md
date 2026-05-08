Run the full quality gate for the current phase:

```bash
# Backend tests
cd backend && pytest app/tests/ --cov=app --cov-report=term-missing -q

# Frontend tests
cd frontend && npm test

# Security
cd backend && bandit -r app/ -ll
cd frontend && npm audit --audit-level=high
```

Report: tests passed/failed, coverage %, any security findings, and whether the phase completion gate is met.
