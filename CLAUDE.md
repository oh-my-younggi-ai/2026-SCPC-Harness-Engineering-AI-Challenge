# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

This is a **competition workspace for SCPC 2026 AI Challenge** (Samsung Collegiate Programming Challenge, AI track), run on DACON. It is **not** a normal software project — there is no git repo, no build system, and no application to ship.

The deliverable is an **AI Agent Harness**: participant-authored Python logic that reads a `task` JSON (a simplified personal-device agent request) and emits a **structured decision** JSON. The harness is run over 700 public screening tasks to produce a single `submission.csv`, which DACON scores against server-held answers.

The core skill being evaluated is *agent decision logic* — how consistently the harness reads task state, session memory, and policy/safety signals — **not** model size or external API power. External LLM APIs and network calls are **forbidden** (see Rules below).

## Layout

- `data/SCPC2026_Final_baseline.ipynb` — the authoritative reference. Contains the full pipeline: data load, `FixedSLMClient` facade, `FinalHarness` (the part participants improve), local runner, local scorer, and `submission.csv` writer. **Start here.**
- `data/dev_tasks.jsonl` (120) — public dev tasks, JSONL (one task per line).
- `data/dev_answers.json` — reference answers for the 120 dev tasks. Used only for local scoring/format checks. **Never** include in a submission or read to hardcode screening answers.
- `data/screening_tasks.jsonl` (700) — the real leaderboard tasks; **no answers provided**.
- `data/submission_schema.json` — JSON Schema the submission must satisfy.
- `data/sample_submission.csv` — the exact CSV shape (BOM + UTF-8, one column `submission`, one data row, whole answer JSON in the single cell).
- `data/TERMS_GUIDE.md` — authoritative glossary of every task/answer field and enum. Read it before touching harness logic.
- `public_rules/` — `introduction.md`, `rules.md`, `scoring.md`. Constraints that can disqualify a submission.

## Running / development

Python only. There is no test runner or lint config — the notebook *is* the harness.

- **Develop**: edit `FinalHarness` (and its module-level helpers) inside `SCPC2026_Final_baseline.ipynb`, cell 7.
- **Local check**: run cells top-to-bottom. Cell 13 runs the harness over dev tasks and scores it via `score_dev_submission` against `dev_answers.json`.
- **Produce submission**: the final cell writes `submission.csv` for the 700 screening tasks.
- **Top-rank verification**: winners may be asked to submit a standalone `harness.py` exposing `FinalHarness.answer_task(task, session)` plus a README. Keep the notebook logic cleanly extractable into a plain module (no notebook-only state).

When editing the notebook programmatically, prefer NotebookEdit / a JSON-safe approach over hand-editing the `.ipynb`.

## Architecture: the decision pipeline

`FinalHarness.answer_task(task, session)` returns one answer dict. The runner (`run_harness`) drives it:

1. Tasks are **sorted by `(session_id, turn_index, id)`** and executed in that order.
2. A per-`session_id` dict is threaded through every turn — this is your **session memory**. Carry-over state (resolved targets, prior consent, memory writes) must be persisted here so later turns in the same session can use it.
3. Before the harness sees a task, `participant_task_view` strips any `expected_*` / `*_rubric` / `answer` keys — do not rely on scoring fields being present at runtime.

Recommended internal decomposition (baseline follows this): `choose_focal` → `infer_target` → `decide_control` → `build_content_scope` → `build_policy` → `build_plan_events` → `update_session_memory`.

### FixedSLMClient facade

`slm.summarize_task(task)` is a **fixed, local, keyword-based evidence extractor** (risk flags, redaction/confirmation hints, audit tags). It is *not* an answer oracle — it does not decide `focal_id`, `target`, `control`, etc. Treat its output as auxiliary signals to combine with your own parsing. It must stay local; the submission `meta` asserts this and it is verified.

### Answer shape

```json
{
  "focal_id": "obj_...",          // id of the central object to act on
  "target": "target_...",         // final recipient / channel / app / store
  "control": "proceed|amend|hold|ask",
  "content_scope": {"mode": "raw|summary|redacted|status_only|none",
                    "allowed_fields": [], "excluded_fields": [],
                    "requires_user_confirmation": false},
  "policy": {"risk_flags": [], "violations": [], "requires_confirmation": false},
  "plan_events": [ {"verb": "...", "target": "...", "args": {...}} ],  // ≤18
  "user_response": "...", "audit_tags": [], "counterfactual": "..."
}
```

`plan_events` verbs come from `available_actions` (read, verify, redact, summarize, dispatch, guard, clarify, update, schedule, toggle, pay). Order matters and is scored; e.g. on revoked consent or a security alert, `guard` must precede `dispatch`. `args` are normalized into the public ontology documented in `TERMS_GUIDE.md` ("plan_events args 공개 ontology") — use those keys/values, don't invent labels.

## Scoring model — this drives design priorities

Local scoring (`score_dev_submission`, cell 11) mirrors the axes/weights the server uses and is **hierarchical and gated**. Understand this before optimizing anything:

- `focal_id` is a **hard gate**. If `focal_id` is wrong, `target` and `control` score 0.
- `content_scope`, `policy`, and `plan` are gated by `dependent = target × control` (both must be exactly right, or all three score 0).
- Weights: focal 0.18, control 0.18, plan 0.18, content_scope 0.17, policy 0.13, target 0.12, semantic_response 0.04.

**Implication: getting `focal_id` and then `target`+`control` right is worth far more than polishing scope/policy/plan, because those are zeroed out when the gates fail.** Prioritize robust focal/target/control resolution first.

Notes: sub-fields use exact-match on modes/booleans and **F1 over sets** for `allowed_fields`, `excluded_fields`, `risk_flags`, `violations`. Plan scoring blends unordered + ordered recall and penalizes extra events. The local scorer is intentionally conservative (it ignores `semantic_response` and some server-side partial credit), so real leaderboard scores may run slightly higher. The plan reference lives under `expected_events` in `dev_answers.json` (compared against your `plan_events`).

## Rules that can disqualify (from `public_rules/rules.md`)

- **No external LLM API, no network calls, no arbitrary external models.** Only the provided `FixedSLMClient`. `meta` must be: `fixed_slm_policy: "local_fixed_slm_only"`, `uses_external_api: false`, `model_id: "scpc-final-fixed-slm-local-facade"`. Recommended `temperature: 0.0`, `seed: 42`.
- **No hardcoding.** Do not key logic on specific `task_id` / `session_id`, do not memorize dev example strings/record values, do not build a lookup table tuned to the public set. The harness must generalize to unseen task streams; reproducibility/generalization is verified for top ranks.
- **No data leakage.** Do not analyze screening answer distributions or hand-label evaluation content.
- Submission: file `submission.csv`, UTF-8, single column `submission`, single data row, the entire answer JSON (top-level per `submission_schema.json`) in that one cell. JSON files are not accepted. Max 5 submissions/day.

## Submission JSON constraints

Each answer must include all of `focal_id, target, control, content_scope, policy, plan_events`. `control` ∈ {proceed, amend, hold, ask}; `content_scope.mode` ∈ {raw, summary, redacted, status_only, none}; `plan_events` ≤ 18 items, each with `verb`/`target`/`args`. The screening payload must contain answers for **exactly** the 700 screening task ids (no missing, no extra).
