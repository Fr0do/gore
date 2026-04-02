# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GORE (Graph Of Recursive Execution) — a formal language for verifiable recursive decomposition, bridging theorem proving (Lean/Coq), structured query decomposition (Text-to-SQL), and natural language reasoning. Minimal syntax with zero pretraining leakage, step-level verification via interpreter, and curriculum-by-design.

## Running

```bash
# Interpreter
python gore.py <file.gore> <entry_point>
python gore.py test.gore color

# Data generation
python goregen.py sample                    # Print example programs
python goregen.py dataset 1000             # Generate training examples → gore_dataset.jsonl
python goregen.py curriculum               # Generate curriculum dataset → gore_curriculum.jsonl
```

No build step, no dependencies beyond Python 3.

## Architecture

Two Python files, no external dependencies:

- **`gore.py`** — Full interpreter: tokenizer (regex-based), recursive-descent parser, AST, unification-based environment (`Env` class with immutable bindings + parent pointers), generator-based backtracking interpreter. `CutException` implements labeled pruning.
- **`goregen.py`** — Synthetic data generator. Three task generators: `gen_color_task`, `gen_simple_fork_task`, `gen_graph_task`. Curriculum system with 5 difficulty levels parameterized by `(depth, width)`. Output: JSONL with program, query, trace, solutions.

## Language: 5 Primitives (3 implemented, 2 planned)

1. **STEP** `X = expr` — deterministic unification/binding
2. **FORK** `? { b1 | b2 | ... }` — non-deterministic branching (all branches live simultaneously)
3. **CUT** `! lhs = rhs -> name` — labeled pruning (kills current branch on unification failure)
4. **LET** `X := expr` — deterministic computation (arithmetic, strings, structures) *(planned)*
5. **CALL** `Result = @fn(args)` — external calls with trace logging *(planned)*

## Known Issues / Priorities

Bugs #1–#4 from the previous list are fixed. Current priorities:

- **Priority 1:** LET + CALL primitives in grammar and interpreter; update trace format to 5 node types; update goregen.py
- **Priority 2:** `sql2gore.py` (Spider/BIRD → GORE via CTE trees), `lean2gore.py` (mathlib4/CoqGym → GORE via tactic mapping)
- **Priority 3:** Dr. GRPO + dense reward (`gore_reward`), `gore2sft.py`, `goreeval.py`
- **Priority 4:** Rust VM (`gorevm`) — 1M examples/minute target

## Timeline (NeurIPS 2026 workshop, abstract May 4)

- Now → Apr 14: LET+CALL in interpreter, lean2gore.py prototype
- Apr 14 → Apr 21: Lean pretraining data prep, Dr. GRPO implementation
- Apr 21 → Apr 28: E1 + E2a/E2b experiments
- Apr 28 → May 4: LaTeX draft finalize, abstract submit

## Git Conventions (OUROBOROS protocol)

- Linear history (rebase, not merge). Commit & push by default.
- Prefix: `[feat]`, `[fix]`, `[doc]`, `[infra]`, `[gen]` (for goregen changes)
- `fixes #N` in commits to auto-close issues
- Create issue before any feature/fix code
- Research issues → `Fr0do/gore`, infra issues → `Fr0do/ourosss`

## Cost Discipline

- Opus for planning, architecture, debugging
- Sonnet subagent for implementation (>20 lines of code)
- Haiku subagent for exploration, search, summarization

## Related Repos

- Paper: [Fr0do/gore-paper](https://github.com/Fr0do/gore-paper)
- Protocol: [Fr0do/ourosss](https://github.com/Fr0do/ourosss)

## Key Documentation

- `GORE_MASTER_PLAN.md` — complete research & code plan (single source of truth)
