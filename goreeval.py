"""
goreeval.py — Eval harness for GORE reasoning traces.

Compares model predictions against interpreter ground truth.

Usage:
    python goreeval.py <predictions.jsonl>           # Evaluate predictions
    python goreeval.py --generate <dataset.jsonl>     # Generate gold answers for a dataset
"""

import json
import sys
from gore import parse_gore, GoreInterpreter, Atom, Var


def run_gold(program_src, query_str, max_solutions=50):
    """Run interpreter to get ground truth trace and solutions."""
    # Parse query: "name(arg1, arg2)" or "name(X)"
    name = query_str.split("(")[0]
    args_str = query_str.split("(")[1].rstrip(")")
    args = []
    for a in args_str.split(","):
        a = a.strip()
        if not a:
            continue
        if a[0].isupper():
            args.append(Var(a))
        else:
            args.append(Atom(a))

    program = parse_gore(program_src)
    interp = GoreInterpreter(program)
    solutions = interp.run(name, args, max_solutions=max_solutions)

    sol_dicts = []
    for sol in solutions:
        bindings = {}
        for k, v in sol.bindings.items():
            resolved = sol.resolve(Var(k))
            bindings[k] = repr(resolved)
        sol_dicts.append(bindings)

    return interp.trace, sol_dicts


def compare_traces(gold_trace, pred_trace):
    """Compare traces line-by-line, return accuracy."""
    if not gold_trace:
        return 1.0 if not pred_trace else 0.0
    matches = 0
    for i, gold_line in enumerate(gold_trace):
        if i < len(pred_trace) and pred_trace[i].strip() == gold_line.strip():
            matches += 1
    return matches / len(gold_trace)


def compare_solutions(gold_sols, pred_sols):
    """Compare solution sets (order-insensitive), return accuracy."""
    if not gold_sols:
        return 1.0 if not pred_sols else 0.0

    # Normalize: convert dicts to frozensets for comparison
    def normalize(sol):
        return frozenset(sorted(sol.items()))

    gold_set = {normalize(s) for s in gold_sols}
    pred_set = {normalize(s) for s in pred_sols}

    if not gold_set:
        return 1.0 if not pred_set else 0.0

    correct = len(gold_set & pred_set)
    return correct / len(gold_set)


def evaluate(predictions_path):
    """Evaluate predictions against interpreter ground truth."""
    results = []
    with open(predictions_path) as f:
        for line_num, line in enumerate(f, 1):
            ex = json.loads(line)
            try:
                gold_trace, gold_sols = run_gold(ex["program"], ex["query"])
                pred_trace = ex.get("model_trace", [])
                pred_sols = ex.get("model_solutions", [])

                trace_acc = compare_traces(gold_trace, pred_trace)
                sol_acc = compare_solutions(gold_sols, pred_sols)
                exact = trace_acc == 1.0 and sol_acc == 1.0

                results.append({
                    "line": line_num,
                    "query": ex["query"],
                    "trace_acc": trace_acc,
                    "sol_acc": sol_acc,
                    "exact": exact,
                    "gold_n": len(gold_sols),
                    "pred_n": len(pred_sols),
                })
            except Exception as e:
                results.append({
                    "line": line_num,
                    "query": ex.get("query", "?"),
                    "error": str(e),
                })

    # Summary
    valid = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]

    if valid:
        avg_trace = sum(r["trace_acc"] for r in valid) / len(valid)
        avg_sol = sum(r["sol_acc"] for r in valid) / len(valid)
        exact_count = sum(1 for r in valid if r["exact"])
        print(f"=== GORE Eval Results ===")
        print(f"Total: {len(results)} | Valid: {len(valid)} | Errors: {len(errors)}")
        print(f"Trace accuracy:    {avg_trace:.1%}")
        print(f"Solution accuracy: {avg_sol:.1%}")
        print(f"Exact match:       {exact_count}/{len(valid)} ({exact_count/len(valid):.1%})")
    else:
        print("No valid results.")

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for r in errors[:5]:
            print(f"  Line {r['line']}: {r['error']}")

    return results


def generate_gold(dataset_path):
    """Add gold trace and solutions to a dataset file."""
    output_path = dataset_path.replace(".jsonl", "_gold.jsonl")
    count = 0
    with open(dataset_path) as f, open(output_path, "w") as out:
        for line in f:
            ex = json.loads(line)
            try:
                trace, sols = run_gold(ex["program"], ex["query"])
                ex["gold_trace"] = trace
                ex["gold_solutions"] = sols
                out.write(json.dumps(ex, default=str) + "\n")
                count += 1
            except Exception as e:
                ex["gold_error"] = str(e)
                out.write(json.dumps(ex, default=str) + "\n")
    print(f"Generated gold for {count} examples → {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--generate":
        generate_gold(sys.argv[2])
    else:
        evaluate(sys.argv[1])
