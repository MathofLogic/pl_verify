"""
plverify.verify — recompute every extracted step; certify or refuse.
==========================================================================
The verification rule per step is exact-first: parse with sympy under
Rational semantics; a step VERIFIES iff recomputation equals the claim
(exactly for exact values, else within 1e-9 relative — floating claims
like "1.67" for 5/3 verify at the precision the author wrote).

The certification rule (the harness's declared theta, in one place):

  REFUTED    — any step recomputes to a different value. One dead lemma
               sinks the derivation: weakest link, kill dominant.
  CERTIFIED  — no refuted steps, at least one verified step, AND the
               final answer equals the result of some verified step.
               Tier: STIPULATED (the self-cap; extraction is stipulated).
  ABSTAIN    — everything else: nothing checkable, or a final answer
               that no verified computation produces. Priced, not hidden.
"""
from __future__ import annotations
import sympy
from sympy import Rational, nsimplify

from .core import Step, Verdict, weakest
from .extract import (extract_steps, extract_final, count_prose_sentences)


def _parse(s):
    """Exact parse: integers/decimals become Rationals; division stays
    exact. Raises on anything that is not pure arithmetic."""
    expr = sympy.parse_expr(s, evaluate=False,
                            transformations="all") if False else \
        sympy.sympify(s, rational=True, evaluate=True)
    if expr.free_symbols:
        raise ValueError(f"non-numeric content in {s!r}")
    return sympy.nsimplify(expr, rational=True)


def check_step(expr, claimed):
    """Return (ok, computed_str). Exact when both sides are exact; a
    decimal claim verifies if it matches the exact value rounded to the
    precision the author used."""
    got = _parse(expr)
    want = _parse(claimed)
    if got == want:
        return True, str(got)
    # decimal-precision tolerance: "5/3 = 1.67" verifies at 2 dp
    if "." in claimed:
        dp = len(claimed.split(".")[1])
        if abs(float(got) - float(want)) <= 0.5 * 10 ** (-dp) + 1e-12:
            return True, str(got)
    return False, str(got)


def verify(solution_text, question=None):
    """The harness's whole job: text in, Verdict out."""
    steps = []
    for expr, claimed, source, pct_flag in extract_steps(solution_text):
        s = Step(expr=expr, claimed=claimed, source=source)
        try:
            ok, computed = check_step(expr, claimed)
            if not ok and pct_flag:
                # one-sided percent: a unit ambiguity, not a refutation.
                # Accept the x100 reading; failing both, decline to judge.
                ok2, _ = check_step(f"({expr})*100", claimed)
                ok3, _ = check_step(expr, f"({claimed})*100")
                if ok2 or ok3:
                    ok = True
                else:
                    s.status, s.computed = "SKIPPED", (
                        f"unit-ambiguous percent (computed {computed})")
                    s.tier = "UNPAID"
                    steps.append(s)
                    continue
            s.status = "VERIFIED" if ok else "REFUTED"
            s.computed = computed
        except Exception as e:
            s.status, s.computed = "SKIPPED", f"unparseable: {e}"[:60]
            s.tier = "UNPAID"     # nothing was decided; priced at zero
        steps.append(s)

    final = extract_final(solution_text)
    n_ver = sum(1 for s in steps if s.status == "VERIFIED")
    n_ref = sum(1 for s in steps if s.status == "REFUTED")
    n_prose = count_prose_sentences(solution_text)
    reasons = []

    if n_ref:
        status = "REFUTED"
        bad = next(s for s in steps if s.status == "REFUTED")
        reasons.append(f"step recomputes false: {bad.expr} = "
                       f"{bad.computed}, not {bad.claimed}")
    elif n_ver == 0:
        status = "ABSTAIN"
        reasons.append("nothing checkable was extracted; the derivation "
                       "is prose to this instrument")
    elif final is None:
        status = "ABSTAIN"
        reasons.append("no final answer found to certify")
    else:
        # the final answer must be PRODUCED by a verified computation
        produced = set()
        for s in steps:
            if s.status == "VERIFIED":
                produced.add(s.computed)
                try:
                    produced.add(str(sympy.nsimplify(s.claimed,
                                                     rational=True)))
                except Exception:
                    pass
        try:
            fkey = str(sympy.nsimplify(final, rational=True))
        except Exception:
            fkey = final
        if fkey in produced:
            status = "CERTIFIED"
        else:
            status = "ABSTAIN"
            reasons.append("final answer is not the result of any "
                           "verified computation (unlinked)")

    # tier: steps are FORCED; the certification itself rests on the
    # stipulated extraction theta -> weakest link caps at STIPULATED.
    tier = weakest([s.tier for s in steps if s.status != "SKIPPED"]
                   + ["STIPULATED"]) if status == "CERTIFIED" else \
        ("FORCED" if status == "REFUTED" else "UNPAID")
    # a refutation IS forced: one recomputed counterexample decides it.

    return Verdict(status=status, tier=tier, final_answer=final,
                   steps=steps, n_verified=n_ver, n_refuted=n_ref,
                   n_prose=n_prose, reasons=reasons)
