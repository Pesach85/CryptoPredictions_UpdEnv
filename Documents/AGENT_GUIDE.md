# Agent Guide

## Purpose
Use this repository to evaluate predictive potential of models on crypto datasets.
Do not provide investment advice.

## Recommended Agent Entry
- Workspace instructions: `.github/copilot-instructions.md`
- Custom agent: `.github/agents/quant-research-gate.agent.md`
- Prompt shortcut: `.github/prompts/predictive-research-gate.prompt.md`

## Required Agent Behavior
1. Validate assumptions before editing.
2. Keep experiments reproducible.
3. Prefer minimal, testable code changes.
4. Update `Documents/KB.md` after non-trivial modifications.
5. Always include a `Next Best Decision` section with exactly one immediate, testable action.

## Validation Minimum
- Run static error checks or one executable baseline training run.
- Report metric outputs and limitations.

## Non-Investment Constraint
All outputs must be framed as experimental predictive analysis and software validation.
