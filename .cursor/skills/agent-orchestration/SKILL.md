---
name: agent-orchestration
description: >-
  Orchestrates multi-step CryptoPredictions work cheaply and correctly: plan
  lightly, delegate independent subtasks, verify with evidence, avoid over-refactor.
  Use when running large builds, packaging, audits, multi-platform work, parallel
  agents, quality gates, or when the user says orchestrate, delegate, verify loop,
  autonomous run, or elite/high quality gate for a multi-step task.
---

# Agent orchestration (adapted for Cursor)

Source patterns: [fable-orchestration](https://github.com/per-simmons/fable-orchestration) (architect/delegate + verify) and [chrisboden/cursor-skills](https://github.com/chrisboden/cursor-skills) (skills-first orchestrator). **Model-agnostic** — do not require Fable/Opus; use Cursor Task/subagents and this repo’s skills.

## Loop

1. **Research** — gather facts with tools (repo, CI, data).
2. **Architect** — short plan, one recommendation (not a survey).
3. **Execute** — implement; parallelise independent work.
4. **Verify** — pytest / CLI smoke / install checks; only claim what tools prove.

Architect step ≈ 5–15% of tokens. Do not re-derive settled KB decisions.

## Behaviours (paste kit, project-tuned)

**Act, don’t overplan**
When you have enough information to act, act. Don’t re-litigate settled Decision Gates or narrate options you won’t pursue. Give a recommendation, then execute.

**No unrequested tidying**
Don’t add features, refactors, or abstractions beyond the task. Simplest thing that works. Validate at system boundaries.

**Delegate**
Independent subtasks → parallel Task/subagents. Prefer async; intervene only if off-track or missing context. Don’t predefine rigid “reviewer/explorer” roles unless the task needs them.

**Ground progress claims**
Before reporting progress, audit each claim against a tool result from this session. If tests fail, say so with output.

**Boundaries**
If the user asks for assessment only, report and stop — don’t fix until asked. Before destructive git/ops, confirm evidence supports that action.

**Autonomous run**
User may not answer mid-task. For reversible actions implied by the request, proceed. Don’t end on a plan/promise — do the work. Stop only when done or blocked on user-only input (secrets, product choice).

**Memory**
Store durable lessons in `Documents/KB.md` (or a single lesson note under this skill’s `lessons/` if tiny). Don’t duplicate KB; update or delete wrong notes.

## Effort routing (cost lever)

| Work | Approach |
|------|----------|
| Routine edit / docs | Direct pair-programmer; low ceremony |
| Domain projection / data / volatility | Load matching `.cursor/skills/*` |
| Multi-platform packaging / audit | This skill + parallel subagents + verify |
| Ambiguous architecture | Short architect note in KB, then execute |

Avoid “max effort” loops that over-change the tree.

## Hard don’ts

- Don’t ask the user to “show your reasoning” rituals that burn tokens without shipping.
- Don’t block serially on every subagent when work is independent.
- Don’t send boilerplate research to a heavy architect pass — research first, then decide.
- Don’t violate simulation-only / Decision Gate closures in KB.

## Pre-run checklist

1. Relevant skill under `.cursor/skills/` loaded?
2. Parallelism possible?
3. Verification command identified (`pytest`, CLI smoke, install script)?
4. KB / NBD update planned if non-trivial?
5. Android on-device vs remote FastAPI default respected?

## CryptoPredictions skill map

| Skill | When |
|-------|------|
| `crypto-predictions-projection` | Forward paths, scenarios, Streamlit/API projection |
| `stealth-browser-market-data` | Anti-bot / stealth refresh |
| `elite-quality-gate` | Elite/high quality gate, packaging, multi-platform ship |
| `agent-orchestration` | Large multi-step orchestration (this file) |
