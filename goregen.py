"""
goregen.py — Synthetic data generator for GORE language.

Generates (task, search_tree, solution) triples for LLM training.
Tasks: color enumeration, graph reachability, list membership.

Each example is a dict:
  {
    "program": str,          # .gore source
    "query":   str,          # entry(args...)
    "trace":   list[str],    # execution trace (reasoning steps)
    "solutions": list[dict], # final variable bindings
    "n_solutions": int,
    "tree_depth": int,       # depth of search tree
    "tree_width": int,       # max branching factor
  }
"""

import random
import json
from gore import parse_gore, GoreInterpreter, Atom, Var


# ─── TASK GENERATORS ─────────────────────────────────────────────────────────

def gen_color_task(n_colors=None):
    """Generate a color enumeration task with random palette."""
    palette = ["red", "green", "blue", "yellow", "black",
               "white", "orange", "purple", "cyan", "magenta"]
    n = n_colors or random.randint(2, 6)
    colors = random.sample(palette, n)

    first = colors[0]
    rest_branches = "\n      | ".join(f"X = {c}" for c in colors[1:])
    if rest_branches:
        src = f"""color(X):
    ? {{
        X = {first}
      | {rest_branches}
    }}
"""
    else:
        src = f"""color(X):
    X = {first}
"""
    return src, "color", [], colors

def gen_graph_task(n_nodes=None, n_edges=None):
    """Generate a random DAG and reachability query."""
    n = n_nodes or random.randint(3, 6)
    nodes = [chr(ord('a') + i) for i in range(n)]

    # Random DAG edges (only forward to avoid cycles)
    max_edges = n_edges or random.randint(n - 1, min(n * 2, n * (n - 1) // 2))
    edges = set()
    for i in range(len(nodes) - 1):
        edges.add((nodes[i], nodes[i + 1]))  # ensure connectivity
    while len(edges) < max_edges:
        i, j = random.randint(0, n - 1), random.randint(0, n - 1)
        if i < j:
            edges.add((nodes[i], nodes[j]))

    # Each edge is a FORK branch with two STEPs
    edge_branches = "\n      | ".join(
        f"X = {u}; Y = {v}" for u, v in sorted(edges)
    )

    src = f"""edge(X, Y):
    ? {{
        {edge_branches}
    }}

reachable(X, Y):
    ? {{
        edge(X, Y)
      | edge(X, Z);
        reachable(Z, Y)
    }}
"""
    # Pick a start node and find all reachable nodes via BFS
    start = random.choice(nodes[:-1])
    edge_dict = {}
    for u, v in edges:
        edge_dict.setdefault(u, []).append(v)

    reachable_from_start = set()
    queue = [start]
    while queue:
        curr = queue.pop(0)
        for neighbor in edge_dict.get(curr, []):
            if neighbor not in reachable_from_start:
                reachable_from_start.add(neighbor)
                queue.append(neighbor)

    # Pick a reachable goal (or start itself for trivial case)
    if reachable_from_start:
        goal = random.choice(sorted(reachable_from_start))
    else:
        goal = start  # X = X is always reachable (first branch)

    return src, "reachable", [start, goal], sorted(edges)

def gen_member_task(list_size=None):
    """Generate list membership task."""
    elements = ["a", "b", "c", "d", "e", "f"]
    n = list_size or random.randint(2, 5)
    lst = random.sample(elements, n)

    # Encode list as nested cons: cons(a, cons(b, nil))
    def make_list(items):
        if not items:
            return "nil"
        return f"cons({items[0]}, {make_list(items[1:])})"

    encoded = make_list(lst)

    src = f"""member(X, L):
    ? {{
        H = hd(L);
        ! X = H -> member
      | T = tl(L);
        member(X, T)
    }}

hd(L):
    ? {{
        {chr(10)+"      | ".join(f"L = cons({e}, _T); R = {e}; R = R" for e in lst)}
    }}

tl(L):
    ? {{
        {chr(10)+"      | ".join(f"L = cons(_H, {make_list(lst[i+1:])}); R = {make_list(lst[i+1:])}; R = R" for i, e in enumerate(lst[:-1]))}
    }}
"""
    query_elem = random.choice(lst + ["z"])  # sometimes ask for non-member
    return src, "color", [], lst  # simplified: just enumerate

def _atom_name(i):
    """Generate atom names: a, b, ..., z, aa, ab, ..., az, ba, ..."""
    if i < 26:
        return chr(ord('a') + i)
    return _atom_name(i // 26 - 1) + chr(ord('a') + i % 26)

def gen_simple_fork_task(depth=None, width=None):
    """
    Generate nested FORK structure of given depth and width.
    Pure enumeration — easiest class for curriculum learning.
    """
    d = depth or random.randint(1, 3)
    w = width or random.randint(2, 4)
    atoms = [_atom_name(i) for i in range(w ** d)]

    def make_body(items, cur_depth):
        if cur_depth == 0 or len(items) == 1:
            return f"X = {items[0]}"
        chunk = len(items) // w
        branches = []
        for i in range(w):
            sub = items[i*chunk:(i+1)*chunk] or [items[-1]]
            branches.append(make_body(sub, cur_depth - 1))
        return "? {\n        " + "\n      | ".join(branches) + "\n    }"

    body = make_body(atoms[:w**d], d)
    src = f"""enumerate(X):\n    {body}\n"""
    return src, "enumerate", [], atoms[:w**d]


# ─── DATASET GENERATOR ───────────────────────────────────────────────────────

GENERATORS = [
    gen_color_task,
    gen_simple_fork_task,
    gen_graph_task,
]

def generate_example(generator=None):
    gen = generator or random.choice(GENERATORS)
    src, entry, args, expected = gen()

    try:
        program = parse_gore(src)
        interp = GoreInterpreter(program)
        atom_args = [Atom(a) for a in args]
        solutions = interp.run(entry, atom_args, max_solutions=20)

        return {
            "program": src,
            "query": f"{entry}({', '.join(args)})" if args else f"{entry}(X)",
            "trace": interp.trace,
            "solutions": [s.bindings for s in solutions],
            "n_solutions": len(solutions),
            "tree_depth": max((t.count("  ") for t in interp.trace), default=0),
            "tree_width": sum(1 for t in interp.trace if "FORK" in t),
            "expected": expected,
        }
    except Exception as e:
        return None

def generate_dataset(n=1000, seed=42):
    random.seed(seed)
    dataset = []
    attempts = 0
    while len(dataset) < n and attempts < n * 3:
        ex = generate_example()
        if ex is not None:
            dataset.append(ex)
        attempts += 1
    return dataset


# ─── CURRICULUM ──────────────────────────────────────────────────────────────

def generate_curriculum(n_per_level=200):
    """
    Curriculum by depth and width:
      Level 0: depth=1, width=2  (trivial fork)
      Level 1: depth=1, width=4
      Level 2: depth=2, width=2
      Level 3: depth=2, width=4
      Level 4: depth=3, width=3
    """
    curriculum = []
    levels = [
        (1, 2), (1, 4), (2, 2), (2, 4), (3, 3)
    ]
    for level, (d, w) in enumerate(levels):
        examples = []
        for _ in range(n_per_level * 3):
            if len(examples) >= n_per_level:
                break
            ex = generate_example(lambda: gen_simple_fork_task(depth=d, width=w))
            if ex:
                ex["level"] = level
                ex["depth"] = d
                ex["width"] = w
                examples.append(ex)
        curriculum.extend(examples)
        print(f"Level {level} (d={d}, w={w}): {len(examples)} examples")
    return curriculum


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "sample"

    if mode == "sample":
        print("=== GORE Data Generator ===\n")
        for gen in GENERATORS:
            src, entry, args, expected = gen()
            print(f"--- {gen.__name__} ---")
            print(src)
            program = parse_gore(src)
            interp = GoreInterpreter(program)
            atom_args = [Atom(a) for a in args]
            solutions = interp.run(entry, atom_args)
            print("TRACE:")
            for t in interp.trace:
                print(t)
            print(f"\nSOLUTIONS: {[s.bindings for s in solutions]}")
            print(f"EXPECTED:  {expected}\n")

    elif mode == "dataset":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        print(f"Generating {n} examples...")
        data = generate_dataset(n)
        out = "gore_dataset.jsonl"
        with open(out, "w") as f:
            for ex in data:
                f.write(json.dumps(ex, default=str) + "\n")
        print(f"Saved {len(data)} examples to {out}")

    elif mode == "curriculum":
        print("Generating curriculum dataset...")
        data = generate_curriculum()
        out = "gore_curriculum.jsonl"
        with open(out, "w") as f:
            for ex in data:
                f.write(json.dumps(ex, default=str) + "\n")
        print(f"Saved {len(data)} examples to {out}")
