# GORE — Deep Research Agent Prompt
# Task: Write a complete LaTeX draft for NeurIPS 2026 workshop submission

---

## Your Task

Write a complete LaTeX paper draft for **GORE: Graph Of Recursive Execution**, a minimal
Turing-complete language designed as a controlled training environment for studying
backtracking reasoning in small LLMs.

Target venue: **NeurIPS 2026 workshop** (reasoning / RL for LLMs track).
Submission type: workshop paper, 4–8 pages + references.
Abstract deadline: May 4, 2026.

Use the official NeurIPS LaTeX style (`neurips_2026.sty` or fall back to `neurips_2024.sty`).
The draft should be complete and compilable, with all sections filled in — not placeholders.
Where experimental results are not yet available, write results as `\textbf{TBD}` with a
descriptive caption explaining what the table/figure will show.

---

## Paper Positioning

### Core Claim
A novel synthetic programming language (GORE) provides a uniquely clean experimental
environment for studying backtracking reasoning in LLMs, with zero pretraining leakage,
verifiable ground truth at every step, and explicit OOD axes (tree depth × width).

### Why This Matters
Existing work on reasoning in LLMs suffers from a fundamental confound: models trained
on Python, math, or natural language may be retrieving memorized patterns rather than
learning to reason. GORE eliminates this confound by design.

### Relation to Prior Work — Key Papers to Cite and Position Against

The agent should search for and cite the following (use web search as needed):

1. **GORE vs Prolog**: GORE is semantically similar to Prolog (unification + backtracking)
   but with two key differences: (a) the search tree is a first-class syntactic object,
   not an interpreter side-effect; (b) CUT is local and labeled, not a global side-effect.
   Cite: Warren (1983) WAM, Colmerauer & Roussel (1993) Prolog history.

2. **Controlled synthetic environments for reasoning**:
   - ARC (Chollet 2019) — abstract reasoning, but no formal verifier
   - BabyAI (Chevalier-Boisvert et al. 2019) — grounded, but NL-polluted
   - SCAN (Lake & Baroni 2018) — compositional generalization, but no search
   - GSM8K, MATH — math reasoning, heavy pretraining leakage
   - Argue: GORE is the first environment designed specifically for *backtracking* with
     formal verifiability at every intermediate step.

3. **RL for LLM reasoning**:
   - GRPO (Shao et al. 2024) — cite as baseline training method
   - DAPO (Yu et al. 2025) — cite as improved variant
   - DeepSeek-R1 (DeepSeek 2025) — cite as motivation for RL-based reasoning
   - STaR (Zelikman et al. 2022) — self-taught reasoner, cite for SFT baseline comparison

4. **Spectral / mechanistic analysis of reasoning**:
   - Elhage et al. (2021) "A Mathematical Framework for Transformer Circuits" — Anthropic
   - Olah et al. (2020) "Zoom In: An Introduction to Circuits" — Anthropic
   - Henighan et al. (2023) on feature geometry
   - Geva et al. (2021) "Transformer Feed-Forward Layers Are Key-Value Memories"
   - Argue: GORE enables cleaner mechanistic analysis because activation patterns
     during FORK vs CUT vs STEP are structurally distinct and interpreter-verifiable.

5. **Architecture**: Briefly mention YOCO (Sun et al. 2024, NeurIPS 2024 oral) as a
   natural fit for multi-turn GORE (program in self-decoder, trace in cross-decoder),
   positioned as future work.

6. **Esolang / formal language tradition**:
   - Brainfuck (Urban Müller 1993) — minimal Turing-complete, 8 commands
   - Unlambda — combinatory logic as language
   - Argue: GORE follows the esolang tradition of minimalism but is the first designed
     with ML training as primary use case.

---

## Paper Structure

### Abstract (150 words)
Cover: (1) problem — confound between retrieval and reasoning in LLM training;
(2) method — GORE language with 3 primitives, Turing-complete, zero pretraining leakage;
(3) key property — explicit search tree as first-class object enables dense reward signal;
(4) experiments — SFT vs GRPO on curriculum, OOD generalization, spectral analysis;
(5) result — [TBD, frame as: "preliminary results suggest..."].

### 1. Introduction
- Open with: the fundamental problem of measuring reasoning vs retrieval in LLMs
- Gap: no existing synthetic environment designed for *backtracking* with step-level verification
- Contribution list (use \begin{itemize}):
  1. GORE language specification — 3 primitives, formal grammar, Turing-completeness proof
  2. Python interpreter (gore.py) + Rust VM (gorevm) for high-throughput data generation
  3. Curriculum dataset with explicit difficulty axes (depth × width)
  4. Experimental framework: 4 ablations (E1–E4) connecting to Spectral-R1

### 2. Background
Subsections:
- 2.1 Backtracking in formal systems (Prolog, WAM, And-Or trees)
- 2.2 Synthetic environments for reasoning (BabyAI, ARC, SCAN) — 1 paragraph each
- 2.3 RL for LLM reasoning (GRPO, STaR) — setup for E2

### 3. The GORE Language

#### 3.1 Syntax and Semantics
Present the full grammar in a \texttt{grammar} or \texttt{alltt} environment:

```
program  ::= clause*
clause   ::= atom '(' vars ')' ':' body
body     ::= stmt | stmt ';' body
stmt     ::= VAR '=' expr
           | '?' '{' body ('|' body)* '}'
           | '!' expr '=' expr '->' atom
expr     ::= VAR | atom | atom '(' expr* ')'
```

Explain each primitive formally:
- **STEP** `X = expr`: unification. If contradiction, branch dies. One sentence on
  why unification subsumes pattern matching + conditionals + argument passing.
- **FORK** `? { b₁ | b₂ | ... }`: non-deterministic branch. All branches are live
  simultaneously. The search tree is explicit in the syntax.
- **CUT** `! lhs = rhs -> name`: local pruning. If unification fails, the current
  branch is killed and control returns to clause `name`. Contrast with Prolog's
  global cut.

#### 3.2 Execution Model
Describe the generator-based backtracking interpreter. Key insight: execution of a
GORE program produces a **trace** — a sequence of (node_type, env, result) tuples
that is itself a verifiable object. The trace IS the chain-of-thought.

Include a small worked example (color enumeration):
```
color(X):
    ? { X = red | X = green | X = blue }
```
Show the full trace for query `color(X)`:
```
FORK (3 branches)
  branch[0]: STEP X = red   → solution {X: red}
  branch[1]: STEP X = green → solution {X: green}
  branch[2]: STEP X = blue  → solution {X: blue}
```

#### 3.3 Turing Completeness
Sketch the proof: encode a Turing machine as a GORE program. Key steps:
- State = atom
- Tape = recursive cons-cell structure
- Transition function = clause with FORK over all (state, symbol) pairs
- Halting = CUT on halt state

Formal theorem in \begin{theorem}...\end{theorem}.

#### 3.4 Properties Relevant to ML Training

Present as a comparison table (\begin{table}):

| Property              | GORE                  | Python/CoT          | Prolog              |
|-----------------------|-----------------------|---------------------|---------------------|
| Pretraining leakage   | Zero                  | High                | Low                 |
| Ground truth          | Interpreter-exact     | Human annotation    | Interpreter-exact   |
| OOD axis              | depth × width         | Undefined           | Undefined           |
| Reward signal         | Per STEP/FORK/CUT     | End only            | End only            |
| Search tree           | Explicit, syntactic   | Implicit            | Implicit            |
| Curriculum            | By design             | Manual              | Manual              |
| BPE-friendly          | Yes (designed for)    | No                  | No                  |

### 4. Dataset and Curriculum

#### 4.1 Task Types
Describe the three task families in the dataset:
1. **Enumeration** — pure FORK trees, no CUT. Difficulty = depth × width.
2. **Graph reachability** — FORK over edges + recursive clauses. Tests CUT for pruning.
3. **List membership** — cons-cell encoding, CUT for early termination.

For each: formal definition, example program, example trace, difficulty parameterization.

#### 4.2 Curriculum Design
5 levels, parameterized by (depth d, width w):
- Level 0: (1, 2) — 2 solutions, trivial
- Level 1: (1, 4) — 4 solutions
- Level 2: (2, 2) — 4 solutions, nested
- Level 3: (2, 4) — 16 solutions, nested wide
- Level 4: (3, 3) — 27 solutions, deep nested

OOD test set: (4, 5) — never seen during training.

#### 4.3 Statistics
Table: for each level, report n_programs, avg_trace_length, avg_n_solutions,
avg_tree_depth, avg_tree_width. Values: \textbf{TBD} (will be computed from
gore_curriculum.jsonl).

### 5. Experiments

Frame as four ablations. For each: hypothesis, setup, metric, expected result (where TBD).

#### 5.1 E1: SFT on Traces (Baseline)
- **Hypothesis**: A model trained to predict traces can generalize to deeper trees OOD.
- **Setup**: GPT-2 (124M) trained on curriculum levels 0–3. Eval on level 4 + OOD (4,5).
- **Metric**: Exact solution set match (interpreter-verified), trace edit distance.
- **Baseline**: Random, greedy search, GPT-2 fine-tuned on Prolog traces.
- **Result**: \textbf{TBD}

#### 5.2 E2: GRPO with Interpreter Reward
- **Hypothesis**: Dense reward signal (per-step) outperforms sparse reward (end-only)
  for learning backtracking.
- **Setup**: Same model as E1, trained with GRPO. Reward = 1.0 for correct STEP/FORK/CUT,
  0.0 for incorrect, -1.0 for dead branch that should have survived.
- **Compare**: E1 vs E2 on same eval set.
- **Result**: \textbf{TBD}
- **Note**: Cite GRPO (Shao et al. 2024) and DAPO (Yu et al. 2025).

#### 5.3 E3: Spectral Analysis of Reasoning Steps
- **Hypothesis**: FORK, CUT, and STEP activations occupy geometrically distinct
  subspaces in the residual stream. This is measurable and interpretable.
- **Setup**: Extract residual stream activations at each token corresponding to a
  FORK/CUT/STEP node. Apply PCA + probing classifiers.
- **Metric**: Linear probing accuracy for node type prediction; singular value
  spectrum of activation matrices during each node type.
- **Connection**: This is the core ablation for Spectral-R1 — GORE provides a clean
  environment where the ground-truth reasoning structure is known, enabling causal
  attribution of spectral changes to specific reasoning operations.
- **Result**: \textbf{TBD}

#### 5.4 E4: Transfer to Natural Language (Preliminary)
- **Hypothesis**: Backtracking ability learned on GORE transfers to NL multi-hop QA.
- **Setup**: GORE-pretrained model fine-tuned on MuSiQue (Trivedi et al. 2022).
  Compare to model trained directly on MuSiQue from scratch.
- **Metric**: MuSiQue accuracy, number of reasoning hops completed.
- **Status**: Preliminary — frame as "we leave full evaluation to future work, but
  initial results suggest..."
- **Result**: \textbf{TBD}

### 6. Discussion

Subsections:
- **6.1 Limitations**: (a) GORE is purely symbolic — no grounding to natural language
  semantics; (b) Turing-completeness proof is constructive but programs are small;
  (c) Transfer to NL (E4) is the weakest link.
- **6.2 GORE as a Research Tool**: Describe intended use by other researchers —
  as a benchmark for reasoning architectures, as a reward environment for RL,
  as a probe environment for mechanistic interpretability.
- **6.3 Future Work**: 
  - Multi-turn GORE (recursive task decomposition)
  - YOCO architecture (Sun et al. 2024) as natural fit for program-in-self-decoder,
    trace-in-cross-decoder
  - Scaling to larger models
  - Harder task types (constraint satisfaction, planning)

### 7. Conclusion
3 paragraphs: (1) problem recap, (2) GORE summary, (3) broader implications for
reasoning research.

---

## LaTeX Requirements

### Style
Use NeurIPS 2026 style. If not available, use:
```latex
\usepackage{neurips_2024}
```

### Required Packages
```latex
\usepackage{amsmath, amsthm, amssymb}
\usepackage{booktabs}          % for \toprule, \midrule, \bottomrule in tables
\usepackage{listings}          % for code blocks
\usepackage{algorithm, algpseudocode}  % for pseudocode
\usepackage{tikz}              % for any diagrams
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{cleveref}          % for \cref
```

### Listings Setup
Configure listings for GORE syntax highlighting:
```latex
\lstdefinelanguage{GORE}{
  keywords={},
  morecomment=[l]{\#},
  sensitive=true,
  literate={?}{{{\color{red}?}}}1
           {!}{{{\color{red}!}}}1
           {->}{{{\color{red}->}}}2
           {|}{{{\color{gray}|}}}1
}
\lstset{language=GORE, basicstyle=\ttfamily\small, frame=single}
```

### Theorem Environments
```latex
\newtheorem{theorem}{Theorem}
\newtheorem{lemma}{Lemma}
\newtheorem{definition}{Definition}
\newtheorem{proposition}{Proposition}
```

### File Structure
Produce a single compilable `gore_paper.tex` with everything inline (no \input).
Bibliography inline as \begin{thebibliography} or use a `gore.bib` file — your choice,
but must compile with `pdflatex gore_paper.tex`.

---

## Key Claims to Make Precisely

1. **Turing-completeness**: Formal theorem with proof sketch. Do not hand-wave.

2. **Zero pretraining leakage**: Argue formally. GORE syntax uses no tokens that appear
   in any known training corpus. The only prior art (Prolog) uses different syntax and
   different semantics for CUT.

3. **Dense reward signal**: Formalize the reward function:
   ```
   r(step) = +1  if step is correct (matches interpreter)
   r(step) = -1  if step is incorrect
   r(branch) = 0 if branch is correctly pruned by CUT
   r(branch) = -1 if branch is incorrectly pruned
   ```

4. **OOD formalization**: Define OOD formally as programs with (d, w) outside the
   training distribution. Prove that the number of valid programs grows as O(w^d),
   giving infinite OOD test cases.

---

## What NOT to Do

- Do not write "GORE is inspired by..." — claim priority directly.
- Do not hedge on Turing-completeness — prove it.
- Do not frame E4 (NL transfer) as a main result — it is preliminary.
- Do not cite YOCO as a contribution of this paper — it is future work.
- Do not write placeholder sections like "experiments will be conducted" —
  write concrete setup even where results are TBD.
- Do not use \textit{} for emphasis — use \textbf{} consistently.
- Do not use bullet lists in the main text — use prose with \emph{} for key terms.

---

## Author / Affiliation Placeholder
```latex
\author{
  Maxim Kurkin \\
  Skoltech / AIRI FusionBrain Lab \\
  \texttt{m.kurkin@skoltech.ru}
}
```

---

## Connection to Spectral-R1

This paper is designed to function as both a standalone contribution AND as an ablation
section within Spectral-R1 (NeurIPS 2026 main track). The connection points:

- E3 (spectral analysis) is the bridge — results from GORE feed directly into
  Spectral-R1's main claim about spectral properties of reasoning activations.
- The GORE dataset is a clean probe: unlike NL tasks, the ground-truth reasoning
  structure is known, enabling causal attribution.
- If results are strong, E3 can be promoted to a main section in Spectral-R1 with
  GORE as the controlled ablation environment.

Frame the paper so that it reads naturally as either standalone or as a component.
Do not mention Spectral-R1 by name in the paper itself.

---

## Deliverable

A single file `gore_paper.tex` that:
1. Compiles with `pdflatex` without errors
2. Is 6–8 pages in NeurIPS format (excluding references)
3. Has all sections filled with real prose (no placeholder text except \textbf{TBD}
   for actual experimental numbers)
4. Passes a basic sanity check: abstract ≤ 150 words, introduction ≤ 1 page,
   related work ≤ 1 page, method ≥ 2 pages, experiments ≥ 1.5 pages
5. Bibliography has ≥ 20 real citations with correct BibTeX entries
   (use web search to find arXiv IDs and verify author lists)
