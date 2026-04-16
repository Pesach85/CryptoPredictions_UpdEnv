---
applyTo: "**/*.py"
description: "Use for Python code changes in CryptoPredictions requiring reproducibility, predictive-model rigor, and non-investment framing."
---

When editing Python code in this repository:

- Preserve reproducibility and deterministic behavior when possible.
- Prefer robust error handling over silent failure.
- Avoid hardcoded credentials and machine-specific absolute paths.
- Keep model and dataset integrations optional where dependencies are heavy.
- If behavior changes, update `Documents/KB.md` with short factual notes.
