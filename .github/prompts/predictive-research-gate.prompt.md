---
description: "Run a complete predictive-research gate for CryptoPredictions: analyze, fix, validate, and document while preserving non-investment scope."
mode: ask
---

Run the predictive-research gate on this workspace with the following constraints:

- Role: senior developer + quantitative/statistical modeling expert.
- Scope: predictive experimentation only, no investment advice.
- Required outputs:
  1. Code/config fixes needed to run robustly.
  2. Validation evidence (command output summary or static checks).
  3. Knowledge-base updates in `Documents/KB.md`.
  4. Developer guidance updates in `Documents/DEV_GUIDE.md` and `Documents/AGENT_GUIDE.md`.
  5. A mandatory `Next Best Decision` section with one deterministic, testable immediate action.

Checklist:
- Remove brittle hardcoded paths/secrets.
- Ensure optional dependencies do not block unrelated models.
- Verify at least one train run for a baseline model.
- Report residual technical debt and next experiments.
