# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GORE (Graph Of Recursive Execution) — minimal Turing-complete programming language for studying backtracking multi-step reasoning in LLMs. Novel syntax with zero pretraining leakage, verifiable ground truth via interpreter, and curriculum-by-design.

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

## Language: Three Primitives

1. **STEP** `X = expr` — deterministic unification/binding
2. **FORK** `? { b1 | b2 | ... }` — non-deterministic branching (all branches live simultaneously)
3. **CUT** `! lhs = rhs -> name` — labeled pruning (kills current branch on unification failure)

No arithmetic, no types, no built-ins — only unification.

## Known Issues (Priority Order)

1. Level 4 curriculum (`depth=3, width=3`) generates 0 examples — off-by-one in `make_body` atom partitioning
2. CUT semantics: `CutException` propagation in nested FORKs needs verification
3. `gen_graph_task` — graph reachability is stubbed but broken
4. Rust VM port (`gorevm`) planned for 1M examples/minute throughput

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

- `GORE_AGENT_PROMPT.md` — complete language spec, grammar, API docs, and prioritized TODOs
- `GORE_RESEARCH_AGENT_PROMPT.md` — NeurIPS 2026 workshop paper instructions (Spectral-R1)
