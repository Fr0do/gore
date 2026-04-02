"""
GORE - Graph Of Recursive Execution
A minimal language for backtracking multi-step reasoning.

Primitives:
  STEP:  VAR = expr          — deterministic binding (unification)
  FORK:  ? { b1 | b2 | ... } — non-deterministic branch (all branches live)
  CUT:   ! VAR = VAR -> NAME  — prune branch if unification fails, return to NAME

File extension: .gore
"""

import re
from dataclasses import dataclass, field
from typing import Any, Optional, Iterator
from copy import deepcopy


# ─── AST ────────────────────────────────────────────────────────────────────

@dataclass
class Atom:
    name: str
    def __repr__(self): return self.name

@dataclass
class Var:
    name: str
    def __repr__(self): return self.name

@dataclass
class Call:
    name: str
    args: list
    def __repr__(self): return f"{self.name}({', '.join(map(repr, self.args))})"

@dataclass
class Step:
    var: str
    expr: Any

@dataclass
class Fork:
    branches: list  # list of Body

@dataclass
class Cut:
    lhs: Any
    rhs: Any
    label: str      # clause name to return to on failure

@dataclass
class Seq:
    stmts: list

@dataclass
class Clause:
    name: str
    params: list
    body: Any

@dataclass
class Program:
    clauses: dict   # name -> list[Clause]


# ─── TOKENIZER ───────────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r"""
    (?P<COMMENT>\#[^\n]*)           |
    (?P<ARROW>->)                   |
    (?P<LPAREN>\()                  |
    (?P<RPAREN>\))                  |
    (?P<LBRACE>\{)                  |
    (?P<RBRACE>\})                  |
    (?P<PIPE>\|)                    |
    (?P<QMARK>\?)                   |
    (?P<BANG>!)                     |
    (?P<COLON>:)                    |
    (?P<SEMI>;)                     |
    (?P<EQ>=)                       |
    (?P<COMMA>,)                    |
    (?P<VAR>[A-Z][a-zA-Z0-9_]*)    |
    (?P<ATOM>[a-z][a-zA-Z0-9_]*)   |
    (?P<WS>\s+)
""", re.VERBOSE)

def tokenize(src: str):
    tokens = []
    for m in TOKEN_RE.finditer(src):
        kind = m.lastgroup
        val  = m.group()
        if kind in ('WS', 'COMMENT'):
            continue
        tokens.append((kind, val))
    return tokens


# ─── PARSER ──────────────────────────────────────────────────────────────────

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return ('EOF', '')

    def consume(self, kind=None):
        tok = self.tokens[self.pos]
        if kind and tok[0] != kind:
            raise SyntaxError(f"Expected {kind}, got {tok}")
        self.pos += 1
        return tok

    def parse_program(self):
        clauses = {}
        while self.peek()[0] != 'EOF':
            c = self.parse_clause()
            clauses.setdefault(c.name, []).append(c)
        return Program(clauses)

    def parse_clause(self):
        name = self.consume('ATOM')[1]
        self.consume('LPAREN')
        params = []
        while self.peek()[0] != 'RPAREN':
            params.append(self.consume('VAR')[1])
            if self.peek()[0] == 'COMMA':
                self.consume('COMMA')
        self.consume('RPAREN')
        self.consume('COLON')
        body = self.parse_body()
        return Clause(name, params, body)

    def parse_body(self):
        stmts = [self.parse_stmt()]
        while self.peek()[0] == 'SEMI':
            self.consume('SEMI')
            if self.peek()[0] in ('RBRACE', 'PIPE', 'EOF'):
                break
            stmts.append(self.parse_stmt())
        if len(stmts) == 1:
            return stmts[0]
        return Seq(stmts)

    def parse_stmt(self):
        kind, val = self.peek()

        if kind == 'QMARK':
            return self.parse_fork()

        if kind == 'BANG':
            return self.parse_cut()

        if kind == 'VAR':
            return self.parse_step()

        raise SyntaxError(f"Unexpected token {self.peek()} at pos {self.pos}")

    def parse_step(self):
        var = self.consume('VAR')[1]
        self.consume('EQ')
        expr = self.parse_expr()
        return Step(var, expr)

    def parse_fork(self):
        self.consume('QMARK')
        self.consume('LBRACE')
        branches = [self.parse_body()]
        while self.peek()[0] == 'PIPE':
            self.consume('PIPE')
            branches.append(self.parse_body())
        self.consume('RBRACE')
        return Fork(branches)

    def parse_cut(self):
        self.consume('BANG')
        lhs = self.parse_expr()
        self.consume('EQ')
        rhs = self.parse_expr()
        self.consume('ARROW')
        label = self.consume('ATOM')[1]
        return Cut(lhs, rhs, label)

    def parse_expr(self):
        kind, val = self.peek()
        if kind == 'VAR':
            self.consume('VAR')
            return Var(val)
        if kind == 'ATOM':
            self.consume('ATOM')
            if self.peek()[0] == 'LPAREN':
                self.consume('LPAREN')
                args = []
                while self.peek()[0] != 'RPAREN':
                    args.append(self.parse_expr())
                    if self.peek()[0] == 'COMMA':
                        self.consume('COMMA')
                self.consume('RPAREN')
                return Call(val, args)
            return Atom(val)
        raise SyntaxError(f"Expected expr, got {self.peek()}")


# ─── ENVIRONMENT ─────────────────────────────────────────────────────────────

class Env:
    """Immutable-style binding environment with unification."""

    def __init__(self, bindings=None, parent=None):
        self.bindings = bindings or {}
        self.parent = parent

    def extend(self, var, val):
        new = Env({**self.bindings, var: val}, self.parent)
        return new

    def lookup(self, var):
        if var in self.bindings:
            val = self.bindings[var]
            seen = {var}
            while isinstance(val, Var):
                if val.name in seen:
                    return val  # circular — return the var itself
                if val.name not in self.bindings:
                    return val
                seen.add(val.name)
                val = self.bindings[val.name]
            return val
        return None

    def resolve(self, expr):
        if isinstance(expr, Var):
            val = self.lookup(expr.name)
            return val if val is not None else expr
        if isinstance(expr, Call):
            return Call(expr.name, [self.resolve(a) for a in expr.args])
        return expr

    def unify(self, lhs, rhs):
        """Returns new Env if unification succeeds, None on failure."""
        l = self.resolve(lhs)
        r = self.resolve(rhs)

        if isinstance(l, Var):
            return self.extend(l.name, r)
        if isinstance(r, Var):
            return self.extend(r.name, l)
        if isinstance(l, Atom) and isinstance(r, Atom):
            return self if l.name == r.name else None
        if isinstance(l, Call) and isinstance(r, Call):
            if l.name != r.name or len(l.args) != len(r.args):
                return None
            env = self
            for la, ra in zip(l.args, r.args):
                env = env.unify(la, ra)
                if env is None:
                    return None
            return env
        return None

    def __repr__(self):
        return f"Env({self.bindings})"


# ─── INTERPRETER ─────────────────────────────────────────────────────────────

class CutException(Exception):
    def __init__(self, label):
        self.label = label

class GoreInterpreter:
    def __init__(self, program: Program):
        self.program = program
        self.trace = []
        self.depth = 0

    def eval_expr(self, expr, env):
        if isinstance(expr, Atom):
            return expr
        if isinstance(expr, Var):
            val = env.resolve(expr)
            return val
        if isinstance(expr, Call):
            args = [self.eval_expr(a, env) for a in expr.args]
            results = list(self._call(expr.name, args, env))
            if results:
                return results[0][0]
            raise RuntimeError(f"Call failed: {expr}")
        return expr

    def _call(self, name, args, env) -> Iterator[tuple]:
        """Yields (result_env, trace) for each solution."""
        if name not in self.program.clauses:
            raise RuntimeError(f"Unknown clause: {name}")

        for clause in self.program.clauses[name]:
            if len(clause.params) != len(args):
                continue
            # Bind params
            local_env = Env()
            ok = True
            for param, arg in zip(clause.params, args):
                new_env = local_env.unify(Var(param), arg)
                if new_env is None:
                    ok = False
                    break
                local_env = new_env

            if not ok:
                continue

            yield from self._exec(clause.body, local_env, name)

    def _exec(self, node, env, clause_name) -> Iterator[tuple]:
        """Execute a body node, yielding (env, done) for each solution path."""

        if isinstance(node, Step):
            val = self.eval_expr(node.expr, env)
            new_env = env.unify(Var(node.var), val)
            if new_env is not None:
                self.trace.append(f"STEP {node.var} = {val}")
                yield new_env, True
            return

        if isinstance(node, Fork):
            self.trace.append(f"FORK ({len(node.branches)} branches)")
            for i, branch in enumerate(node.branches):
                self.trace.append(f"  branch[{i}]")
                try:
                    yield from self._exec(branch, env, clause_name)
                except CutException as e:
                    if e.label == clause_name:
                        return
                    raise
            return

        if isinstance(node, Cut):
            lhs = self.eval_expr(node.lhs, env)
            rhs = self.eval_expr(node.rhs, env)
            new_env = env.unify(lhs, rhs)
            if new_env is None:
                self.trace.append(f"CUT failed → {node.label}")
                raise CutException(node.label)
            self.trace.append(f"CUT ok: {lhs} = {rhs}")
            yield new_env, True
            return

        if isinstance(node, Seq):
            yield from self._exec_seq(node.stmts, env, clause_name)
            return

        raise RuntimeError(f"Unknown node: {node}")

    def _exec_seq(self, stmts, env, clause_name) -> Iterator[tuple]:
        if not stmts:
            yield env, True
            return
        for env2, _ in self._exec(stmts[0], env, clause_name):
            yield from self._exec_seq(stmts[1:], env2, clause_name)

    def run(self, clause_name, args, max_solutions=10):
        self.trace = []
        self.depth = 0
        solutions = []
        # If no args provided, pass a fresh Var to collect results
        if not args:
            args = [Var("X")]
        for env, _ in self._call(clause_name, args, Env()):
            solutions.append(env)
            if len(solutions) >= max_solutions:
                break
        return solutions


# ─── CLI ─────────────────────────────────────────────────────────────────────

def parse_gore(src: str) -> Program:
    tokens = tokenize(src)
    parser = Parser(tokens)
    return parser.parse_program()

def run_gore(src: str, entry: str, args: list, verbose=False):
    program = parse_gore(src)
    interp = GoreInterpreter(program)
    atom_args = [Atom(a) for a in args]
    solutions = interp.run(entry, atom_args)
    if verbose:
        print("=== TRACE ===")
        for line in interp.trace:
            print(line)
        print()
    print(f"=== SOLUTIONS ({len(solutions)}) ===")
    for i, sol in enumerate(solutions):
        print(f"  [{i}] {sol.bindings}")
    return solutions


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: gore.py <file.gore> <entry> [args...]")
        sys.exit(1)

    src = open(sys.argv[1]).read()
    entry = sys.argv[2]
    args = sys.argv[3:]
    run_gore(src, entry, args, verbose=True)
