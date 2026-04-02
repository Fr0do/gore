# GORE — Agent Prompt

## What is GORE

GORE (Graph Of Recursive Execution) is a minimal Turing-complete programming language
designed for backtracking multi-step reasoning. It is intentionally ML-friendly:
every program is a verifiable search tree, making it ideal for synthetic training data generation.

File extension: `.gore`
Interpreter: `gore.py`
Generator: `goregen.py`

---

## Language Specification

### Three primitives only

```
STEP:  VAR = expr           # deterministic unification/binding
FORK:  ? { b1 | b2 | ... } # non-deterministic branch (all branches live simultaneously)
CUT:   ! lhs = rhs -> name  # prune this branch if unification fails, return to clause `name`
```

### Grammar (complete)

```
program  ::= clause*
clause   ::= ATOM '(' VARS ')' ':' body
body     ::= stmt | stmt ';' body
stmt     ::= VAR '=' expr          # STEP
           | '?' '{' body ('|' body)* '}'   # FORK
           | '!' expr '=' expr '->' ATOM    # CUT
expr     ::= VAR | ATOM | ATOM '(' expr* ')'
```

- `VAR` = uppercase identifier (X, Y, Head, Tail...)
- `ATOM` = lowercase identifier (red, cons, nil, edge...)
- Sequences use `;` separator
- No arithmetic, no types, no built-ins — only unification

### Core semantic: unification

`X = expr` means: unify X with expr. If contradiction → branch dies.
This gives you pattern matching, argument passing, and conditionals for free.

---

## Current Implementation

### `gore.py` — Python interpreter

Classes:
- `Atom`, `Var`, `Call` — value types
- `Step`, `Fork`, `Cut`, `Seq`, `Clause`, `Program` — AST nodes
- `Env` — immutable unification environment with occurs-check-safe lookup
- `GoreInterpreter` — generator-based backtracking interpreter
- `parse_gore(src: str) -> Program` — full parser
- `run_gore(src, entry, args, verbose)` — convenience runner

Usage:
```bash
python gore.py test.gore color          # enumerate all colors
python gore.py myprog.gore path a d    # find paths from a to d
```

### `goregen.py` — Synthetic data generator

Generates `(program, query, trace, solutions)` tuples for LLM training.

Task types implemented:
- `gen_color_task(n_colors)` — enumeration with random palette
- `gen_simple_fork_task(depth, width)` — nested FORK trees, curriculum-ready

Output format (JSONL):
```json
{
  "program": "...",
  "query": "enumerate(X)",
  "trace": ["FORK (3 branches)", "  branch[0]", "STEP X = a", ...],
  "solutions": [{"X": "a"}, {"X": "b"}, {"X": "c"}],
  "n_solutions": 3,
  "tree_depth": 2,
  "tree_width": 1,
  "level": 0
}
```

Curriculum levels (by search tree complexity):
```
Level 0: depth=1, width=2   # trivial fork
Level 1: depth=1, width=4
Level 2: depth=2, width=2
Level 3: depth=2, width=4
Level 4: depth=3, width=3   # needs fix — see TODOs
```

Usage:
```bash
python goregen.py sample                # print examples to stdout
python goregen.py dataset 1000         # generate 1000 examples → gore_dataset.jsonl
python goregen.py curriculum           # curriculum dataset → gore_curriculum.jsonl
```

---

## TODOs for coding agent

### Priority 1 — Fix bugs

1. **Level 4 curriculum generates 0 examples** — bug in `gen_simple_fork_task` 
   when `depth=3, width=3`. The recursive `make_body` slicing is off.
   Fix: rewrite `make_body` to correctly partition `w^d` atoms into `w` equal chunks
   at each recursion level.

2. **CUT semantics incomplete** — `CUT` currently raises `CutException` which is caught
   in `_exec(Fork)`. But CUT should only kill the *current branch*, not all siblings.
   Verify the exception propagation is correct for nested FORKs.

### Priority 2 — New task generators

3. **`gen_graph_task`** — graph reachability is stubbed but broken (the `neighbor` clause
   generation is incorrect). Rewrite using proper FORK over edges:
   ```gore
   reachable(X, Y):
       ? {
           X = Y
         | ? { X = a; Z = b | X = b; Z = c | ... };
           reachable(Z, Y)
       }
   ```

4. **`gen_list_member_task`** — membership in a cons-list. Encode list as 
   `cons(a, cons(b, nil))`. The `member` clause uses CUT to stop on first match or
   recurse into tail. This exercises both FORK and CUT together.

5. **`gen_decompose_task`** — decompose a "prompt" (represented as a tree of atoms)
   into subproblems. This is the core intended use case of GORE. Design the encoding.

### Priority 3 — Rust VM

6. **`gorevm` in Rust** — port the interpreter to Rust for high-throughput generation.
   Target: 1M examples/minute.
   
   Architecture:
   ```
   src/
     main.rs       # CLI
     lexer.rs      # tokenizer
     parser.rs     # recursive descent → AST
     env.rs        # persistent hash-map environment (use im-rs crate)
     interp.rs     # generator-style interpreter using explicit stack
     types.rs      # Term enum: Atom, Var, Compound
   ```
   
   Key design decision: use an **explicit worklist stack** instead of Rust generators
   (generators are unstable). Each stack frame = (node, env, clause_name).
   
   Recommended crates:
   - `im` — immutable data structures for Env
   - `logos` — fast lexer
   - `clap` — CLI
   - `serde_json` — JSONL output

### Priority 4 — ML pipeline

7. **Tokenizer design** — design a BPE-friendly tokenization scheme where:
   - Each GORE keyword (`FORK`, `STEP`, `CUT`, `?`, `!`, `->`) is a single token
   - Atom names are single tokens
   - The trace format mirrors the program structure

8. **SFT format** — convert JSONL to training format:
   ```
   INPUT:  <program>\n<query>
   OUTPUT: <trace>\n<solutions>
   ```
   Write `gore2sft.py` that converts `gore_curriculum.jsonl` → HuggingFace Dataset.

9. **Eval harness** — given a model output (predicted trace + solutions),
   verify correctness by running the actual interpreter and comparing solution sets.
   Write `goreeval.py`.

---

## Research context

GORE is designed as a controlled experimental environment for studying backtracking
reasoning in small LLMs. Key properties:

- **Zero pretraining leakage** — novel syntax, no overlap with existing corpora
- **Verifiable ground truth** — interpreter provides exact solutions
- **Infinite OOD** — compositional structure means depth/width generalization is testable
- **Dense reward signal** — every STEP/FORK/CUT in the trace is a verifiable intermediate step
- **Curriculum by design** — tree depth and width are explicit difficulty axes

Intended experiments:
1. Train micro-LLM (GPT-2 scale) on curriculum levels 0→4
2. Test OOD generalization to depth=4, width=5 (unseen combinations)
3. Compare: SFT on traces vs GRPO with interpreter-based reward
4. Measure: does explicit search tree representation improve backtracking vs implicit CoT?

Connection to Spectral-R1: GORE provides a clean ablation environment where
spectral properties of activations during reasoning can be studied without
natural language noise.
