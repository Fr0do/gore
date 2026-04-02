"""
lean2gore.py — Lean4 tactic trace → GORE converter

Mapping:
  cases / rcases / induction / match  → FORK  (branching)
  exact / rfl / trivial / assumption   → STEP  (deterministic binding)
  contradiction / absurd / exfalso     → CUT   (prune on failure)
  apply / refine / exact?             → CALL  (clause invocation)
  have / simp / rw / ring / omega / norm_num / linarith / nlinarith
  / constructor / intro / intros / use → LET   (local binding / simplification)

Usage:
  python lean2gore.py --demo
  python lean2gore.py --file proof.lean
  python lean2gore.py --batch ./lean_proofs/
  python lean2gore.py --file proof.lean --entry my_lemma --run
"""

import re
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

# ── Import gore.py from same directory ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gore as gore_module


# ─── TACTIC MAP ──────────────────────────────────────────────────────────────
# Maps Lean4 tactic names → GORE statement type
# Types: FORK | STEP | CUT | CALL | LET

TACTIC_MAP: dict[str, str] = {
    # Branching / case analysis → FORK
    "cases":        "FORK",
    "rcases":       "FORK",
    "induction":    "FORK",
    "match":        "FORK",
    "fin_cases":    "FORK",
    "interval_cases":"FORK",
    "split":        "FORK",
    "by_cases":     "FORK",

    # Deterministic closure → STEP
    "exact":        "STEP",
    "rfl":          "STEP",
    "trivial":      "STEP",
    "assumption":   "STEP",
    "decide":       "STEP",
    "native_decide":"STEP",
    "norm_cast":    "STEP",
    "tauto":        "STEP",

    # Contradiction / pruning → CUT
    "contradiction":"CUT",
    "absurd":       "CUT",
    "exfalso":      "CUT",
    "no_confusion": "CUT",
    "simp_all":     "CUT",

    # Clause invocation → CALL
    "apply":        "CALL",
    "refine":       "CALL",
    "exact?":       "CALL",
    "specialize":   "CALL",
    "revert":       "CALL",

    # Local binding / rewriting → LET
    "have":         "LET",
    "simp":         "LET",
    "rw":           "LET",
    "rewrite":      "LET",
    "ring":         "LET",
    "omega":        "LET",
    "norm_num":     "LET",
    "linarith":     "LET",
    "nlinarith":    "LET",
    "constructor":  "LET",
    "intro":        "LET",
    "intros":       "LET",
    "use":          "LET",
    "push_neg":     "LET",
    "ext":          "LET",
    "funext":       "LET",
    "congr":        "LET",
    "field_simp":   "LET",
}


# ─── PARSE TACTIC ────────────────────────────────────────────────────────────

def parse_tactic(line: str) -> tuple[str, str]:
    """
    Parse a single Lean4 tactic line into (tactic_name, args_string).

    Examples:
      "  apply Nat.add_comm"      → ("apply", "Nat.add_comm")
      "  rfl"                     → ("rfl", "")
      "  have h : n + 0 = n := …" → ("have", "h : n + 0 = n := …")
      "  cases n with"            → ("cases", "n with")
    """
    stripped = line.strip()
    # Remove leading "· " (focus dot) or "|" branch markers
    stripped = re.sub(r'^[·\|]\s*', '', stripped).strip()
    # Remove trailing comments
    stripped = re.sub(r'\s*--.*$', '', stripped).strip()

    if not stripped:
        return ("", "")

    # Match tactic name (may contain ? or _)
    m = re.match(r'^([a-zA-Z_][a-zA-Z0-9_?]*)\b(.*)', stripped)
    if not m:
        return ("unknown", stripped)

    name = m.group(1)
    args = m.group(2).strip()
    return (name, args)


# ─── SANITIZE NAME ───────────────────────────────────────────────────────────

def sanitize_name(s: str) -> str:
    """
    Convert an arbitrary string to a valid GORE atom.

    GORE atoms: [a-z][a-zA-Z0-9_]*
    Strategy:
      - lowercase the first character if uppercase
      - replace dots, colons, spaces, hyphens → underscores
      - strip all other non-alphanumeric/underscore chars
      - ensure starts with lowercase letter
      - truncate to 32 chars to keep output readable
    """
    if not s:
        return "anon"

    # Lean qualified names: Nat.add_comm → nat_add_comm
    s = s.replace(".", "_").replace(":", "_").replace(" ", "_").replace("-", "_")
    # Remove anything else that's not word-char
    s = re.sub(r'[^\w]', '', s)
    # Must start with lowercase letter
    if not s:
        return "anon"
    if s[0].isdigit():
        s = "n" + s
    if s[0].isupper():
        s = s[0].lower() + s[1:]
    # Collapse repeated underscores
    s = re.sub(r'_+', '_', s).strip('_')
    if not s:
        return "anon"
    return s[:32]


# ─── TACTIC TO GORE ──────────────────────────────────────────────────────────

def tactic_to_gore(line: str, counter: list[int]) -> Optional[str]:
    """
    Convert a single Lean4 tactic line to a GORE statement string.

    counter is a mutable [int] used to generate fresh variable names.
    Returns None for blank/comment lines.

    GORE statement forms produced:
      STEP:  V = atom
      LET:   V := expr
      CUT:   ! V = atom -> fail
      CALL:  name(V)       — as a CallStmt
      FORK:  ? { branch_a | branch_b }   — simplified two-branch fork
    """
    name, args = parse_tactic(line)
    if not name:
        return None

    gore_type = TACTIC_MAP.get(name)
    if gore_type is None:
        # Unknown tactic → treat as LET (safe fallback)
        gore_type = "LET"

    counter[0] += 1
    idx = counter[0]
    var = f"V{idx}"

    # Sanitize the args into a valid atom/call name
    if args:
        # Extract the first token of args as the "target"
        first_arg = args.split()[0] if args.split() else args
        atom = sanitize_name(first_arg)
    else:
        atom = sanitize_name(name)

    if gore_type == "STEP":
        # V = atom
        return f"{var} = {atom}"

    elif gore_type == "LET":
        # V := atom
        return f"{var} := {atom}"

    elif gore_type == "CUT":
        # ! V = atom -> fail
        return f"! {var} = {atom} -> fail"

    elif gore_type == "CALL":
        # atom(V)  — call as a statement
        call_name = atom if atom else sanitize_name(name)
        return f"{call_name}({var})"

    elif gore_type == "FORK":
        # ? { branch_a | branch_b }
        # Generate two named sub-branches from args
        arg_atoms = [sanitize_name(a) for a in args.split()] if args.split() else ["base", "step"]
        # Ensure at least two branches for FORK syntax
        while len(arg_atoms) < 2:
            arg_atoms.append(f"branch{idx}")
        b1, b2 = arg_atoms[0], arg_atoms[1]
        c1, c2 = counter[0] + 1, counter[0] + 2
        counter[0] += 2
        return f"? {{ V{c1} = {b1} | V{c2} = {b2} }}"

    # Should never reach here
    return f"{var} := {sanitize_name(name)}"


# ─── PROOF TO GORE ───────────────────────────────────────────────────────────

def proof_to_gore(steps: list[str], name: str) -> str:
    """
    Convert a list of Lean4 tactic lines to a full GORE program string.

    Produces a single clause named `name` with one parameter (Goal)
    and a sequential body of GORE statements derived from each tactic.

    Steps that produce FORK nodes are rendered inline (GORE has no
    separate sub-clause syntax for branches in this simplified model).

    Returns a string ready to be parsed by gore.parse_gore().
    """
    clause_name = sanitize_name(name)
    counter = [0]  # mutable counter threaded through tactic_to_gore

    gore_stmts: list[str] = []
    for line in steps:
        stmt = tactic_to_gore(line, counter)
        if stmt is not None:
            gore_stmts.append(stmt)

    if not gore_stmts:
        # Empty proof — just bind goal to proved
        gore_stmts = ["V1 = proved"]

    # Join with semicolons
    body = ";\n  ".join(gore_stmts)

    program = f"# Generated by lean2gore.py\n"
    program += f"# Source lemma: {name}\n\n"
    program += f"{clause_name}(Goal):\n  {body}\n"
    return program


# ─── DEMO ────────────────────────────────────────────────────────────────────

NAT_ADD_COMM_LEAN = """\
-- Lean4 tactic proof of Nat.add_comm
theorem nat_add_comm (n m : Nat) : n + m = m + n := by
  induction n with
  | zero =>
    simp
  | succ n ih =>
    rw [Nat.succ_add]
    rw [Nat.add_succ]
    exact congrArg Nat.succ ih
""".strip().splitlines()


def run_demo():
    print("=" * 60)
    print("lean2gore DEMO — nat_add_comm")
    print("=" * 60)
    print()

    # Show source
    print("── Lean4 source ──────────────────────────────────────────")
    for line in NAT_ADD_COMM_LEAN:
        print(line)
    print()

    # Extract tactic lines (skip theorem declaration and comments)
    tactic_lines = []
    in_proof = False
    for line in NAT_ADD_COMM_LEAN:
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if ":= by" in line or stripped == "by":
            in_proof = True
            continue
        if in_proof:
            tactic_lines.append(line)

    # Show parsed tactics
    print("── Parsed tactics ────────────────────────────────────────")
    for line in tactic_lines:
        name, args = parse_tactic(line)
        if name:
            gore_type = TACTIC_MAP.get(name, "LET")
            print(f"  {name!r:20s} args={args!r:30s} → {gore_type}")
    print()

    # Convert
    gore_src = proof_to_gore(tactic_lines, "nat_add_comm")

    print("── Generated GORE ────────────────────────────────────────")
    print(gore_src)

    # Verify it parses with gore.py
    print("── Verification (gore.parse_gore) ───────────────────────")
    try:
        program = gore_module.parse_gore(gore_src)
        clause_names = list(program.clauses.keys())
        total_clauses = sum(len(v) for v in program.clauses.values())
        print(f"  OK — parsed {total_clauses} clause(s): {clause_names}")

        # Run it
        interp = gore_module.GoreInterpreter(program)
        solutions = interp.run("nat_add_comm", [gore_module.Atom("goal")])
        print(f"  OK — {len(solutions)} solution(s) found")
        for i, sol in enumerate(solutions):
            print(f"       [{i}] {sol.bindings}")
        print()
        print("  Execution trace:")
        for t in interp.trace:
            print(f"    {t}")
    except Exception as e:
        print(f"  FAIL — {e}")
        raise

    print()
    print("=" * 60)
    print("Demo complete.")
    print("=" * 60)


# ─── FILE MODE ───────────────────────────────────────────────────────────────

def convert_file(path: Path, entry: Optional[str] = None, run: bool = False) -> str:
    """
    Read a .lean file, extract tactic lines from the first `by` block,
    and return the GORE source string.
    """
    src = path.read_text()
    lines = src.splitlines()

    # Detect lemma/theorem name
    name = entry
    if name is None:
        for line in lines:
            m = re.match(r'^\s*(?:theorem|lemma)\s+(\w+)', line)
            if m:
                name = m.group(1)
                break
        if name is None:
            name = path.stem

    # Extract tactic body
    tactic_lines = []
    in_proof = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        if re.search(r':=\s*by\b', line) or stripped == "by":
            in_proof = True
            continue
        if in_proof:
            # Stop at next top-level declaration
            if re.match(r'^(?:theorem|lemma|def|example|#)', stripped) and stripped:
                break
            tactic_lines.append(line)

    gore_src = proof_to_gore(tactic_lines, name)
    return gore_src


# ─── BATCH MODE ──────────────────────────────────────────────────────────────

def run_batch(directory: Path):
    """
    Convert all .lean files in a directory tree to .gore files.
    Prints a summary table.
    """
    lean_files = list(directory.rglob("*.lean"))
    if not lean_files:
        print(f"No .lean files found in {directory}")
        return

    print(f"Found {len(lean_files)} .lean file(s) in {directory}")
    print()

    ok, fail = 0, 0
    for lf in lean_files:
        out_path = lf.with_suffix(".gore")
        try:
            gore_src = convert_file(lf)
            # Validate
            gore_module.parse_gore(gore_src)
            out_path.write_text(gore_src)
            print(f"  OK  {lf.name:40s} → {out_path.name}")
            ok += 1
        except Exception as e:
            print(f"  ERR {lf.name:40s}   {e}")
            fail += 1

    print()
    print(f"Done: {ok} converted, {fail} failed.")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="lean2gore — convert Lean4 tactic traces to GORE programs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--demo",  action="store_true", help="Run built-in nat_add_comm demo")
    parser.add_argument("--file",  type=Path,           help="Convert a single .lean file")
    parser.add_argument("--batch", type=Path,           help="Convert all .lean files in a directory")
    parser.add_argument("--entry", type=str,            help="Override lemma name for --file mode")
    parser.add_argument("--run",   action="store_true", help="Run the generated GORE program after conversion")
    parser.add_argument("--out",   type=Path,           help="Output .gore file path (default: stdout)")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if args.batch:
        run_batch(args.batch)
        return

    if args.file:
        gore_src = convert_file(args.file, entry=args.entry, run=args.run)

        if args.out:
            args.out.write_text(gore_src)
            print(f"Written to {args.out}")
        else:
            print(gore_src)

        if args.run:
            entry = sanitize_name(args.entry or args.file.stem)
            print(f"\n── Running GORE entry '{entry}' ──")
            try:
                program = gore_module.parse_gore(gore_src)
                interp = gore_module.GoreInterpreter(program)
                solutions = interp.run(entry, [gore_module.Atom("goal")])
                print(f"Solutions ({len(solutions)}):")
                for i, sol in enumerate(solutions):
                    print(f"  [{i}] {sol.bindings}")
                print("Trace:")
                for t in interp.trace:
                    print(f"  {t}")
            except Exception as e:
                print(f"Runtime error: {e}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
