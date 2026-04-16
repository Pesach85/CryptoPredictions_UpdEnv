# CryptoPredictions Workspace Instructions

## Mission
This repository is used for predictive experimentation on crypto market time series.
Do not produce investment advice. Focus on model quality, reproducibility, statistical rigor, and transparent reporting.

## Operating Rules
- Prioritize reproducible experiments over quick hacks.
- Prefer local CSV datasets and deterministic settings (`random_state`) for comparisons.
- Treat trading/backtesting outputs as simulation only.
- When changing model behavior, update documentation and KB in `Documents/KB.md`.
- Keep changes minimal and backwards-compatible unless a breaking change is explicitly requested.

## Quality Gate
For any non-trivial change:
1. Verify config portability (no machine-specific absolute paths).
2. Run at least one training command or static validation.
3. Record findings and decisions in `Documents/KB.md`.
4. If dependencies are optional, fail gracefully with clear errors.

## Research Focus
When evaluating results, include:
- Error metrics (`MAE`, `RMSE`, `SMAPE`, `MAPE`, `MASE`, `MSLE`)
- Directional metrics (`accuracy_score`, `precision_score`, `recall_score`, `f1_score`)
- Data split assumptions and leakage risks
- Residual risks and next experiments

## Next Best Decision Policy
- Always provide a `Next Best Decision` section in outputs.
- The section must contain 1 clear recommended action for the immediate next step.
- Recommendation must be deterministic, testable, and aligned with reproducibility constraints.
