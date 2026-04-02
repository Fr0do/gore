"""Tests for CUT semantics in GORE interpreter."""
import unittest
from gore import parse_gore, GoreInterpreter, Var, Atom

class TestCutSemantics(unittest.TestCase):
    def _run(self, src, entry, args=None):
        program = parse_gore(src)
        interp = GoreInterpreter(program)
        atom_args = [Atom(a) for a in args] if args else [Var("X")]
        return interp.run(entry, atom_args, max_solutions=50)

    def test_cut_passes_on_match(self):
        """CUT with matching unification should continue."""
        src = """
check(X):
    X = hello;
    ! X = hello -> check
"""
        sols = self._run(src, "check")
        self.assertEqual(len(sols), 1)
        self.assertEqual(sols[0].resolve(Var("X")).name, "hello")

    def test_cut_kills_branch_on_failure(self):
        """CUT with failing unification should kill the branch."""
        src = """
check(X):
    ? {
        X = a;
        ! X = b -> check
      | X = c
    }
"""
        sols = self._run(src, "check")
        # Branch 0: X=a, then CUT X=b fails → CutException("check")
        # Fork catches (label=="check"), does return → Branch 1 (X=c) never runs.
        # Result: 0 solutions.
        self.assertEqual(len(sols), 0)

    def test_cut_only_kills_matching_label(self):
        """CUT with non-matching label should propagate up."""
        src = """
outer(X):
    ? {
        inner(X)
      | X = fallback
    }

inner(X):
    ? {
        X = a;
        ! X = b -> outer
      | X = c
    }
"""
        sols = self._run(src, "outer")
        # inner branch 0: X=a, CUT X=b fails → CutException("outer")
        # inner's Fork: label "outer" != clause_name "inner" → re-raise
        # outer's Fork: label "outer" == clause_name "outer" → return → kills branch 1 (fallback)
        # Result: 0 solutions
        self.assertEqual(len(sols), 0)

    def test_cut_allows_earlier_branches(self):
        """Branches before the CUT branch should still produce solutions."""
        src = """
check(X):
    ? {
        X = first
      | X = second;
        ! X = nope -> check
      | X = third
    }
"""
        sols = self._run(src, "check")
        # Branch 0: X=first → solution
        # Branch 1: X=second, CUT X=nope fails → CutException("check"), Fork catches → return (stops branch 2)
        # Result: 1 solution (first)
        self.assertEqual(len(sols), 1)
        self.assertEqual(sols[0].resolve(Var("X")).name, "first")

    def test_fork_without_cut(self):
        """Sanity check: FORK without CUT returns all branches."""
        src = """
check(X):
    ? {
        X = a
      | X = b
      | X = c
    }
"""
        sols = self._run(src, "check")
        self.assertEqual(len(sols), 3)

if __name__ == "__main__":
    unittest.main()
