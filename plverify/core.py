"""
plverify.core — tiers, verdicts, and the sealed chain.
==========================================================================
The vocabulary is Propagation Logic's, unchanged:

  FORCED > EMPIRICAL > CONDITIONAL > STIPULATED > UNPAID

and one addition this harness needs: a step can be REFUTED — provably
false by recomputation — which is not a tier but a kill. Verdicts compose
by weakest link, and the composite CERTIFICATION CAPS AT STIPULATED,
because the harness is built of stipulations (which text counts as a
checkable step is a theta the extractor chose). A verifier that graded
its own certificates FORCED would be lying about its own extraction.

The seal format is byte-compatible with the PL kernel's chain
(sha256(prev + json(body, sort_keys=True))[:16]) so manifests from this
harness replay under pl.replay unchanged.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass, field, asdict

TIER_ORDER = ("FORCED", "EMPIRICAL", "CONDITIONAL", "STIPULATED", "UNPAID")


def weakest(tiers):
    paid = [t for t in tiers if t != "UNPAID"]
    if not paid:
        return "UNPAID"
    return max(paid, key=TIER_ORDER.index)


@dataclass
class Step:
    """One checkable claim extracted from a derivation."""
    expr: str                    # the expression as extracted, e.g. "16-3-4"
    claimed: str                 # the claimed result, e.g. "9"
    source: str                  # "annotation" | "freetext"
    status: str = "PENDING"      # VERIFIED | REFUTED | SKIPPED
    computed: str = ""           # what recomputation actually got
    tier: str = "FORCED"         # a VERIFIED/REFUTED step is FORCED either
                                 # way: the recomputation decides it
    falsifier: str = ("recompute expr with exact rationals; "
                      "certificate dies if it differs from `claimed`")


@dataclass
class Verdict:
    """The harness's judgment on one derivation. Never a bare boolean."""
    status: str                  # CERTIFIED | REFUTED | ABSTAIN
    tier: str                    # certificate tier (caps at STIPULATED)
    final_answer: str | None
    steps: list = field(default_factory=list)
    n_verified: int = 0
    n_refuted: int = 0
    n_prose: int = 0             # sentences with nothing checkable
    reasons: list = field(default_factory=list)
    non_claims: tuple = (
        "NOT claimed: that a CERTIFIED derivation used sound reasoning — "
        "only that every extracted computation recomputes and the final "
        "answer is produced by one of them. Semantics (did the equations "
        "model the problem?) is not checkable by this harness.",
        "NOT claimed: that ABSTAIN means wrong. It means unverifiable "
        "by this instrument: nothing checkable was extracted, or the "
        "final answer is not linked to a verified computation.",
        "NOT claimed: that extraction is complete. Which text counts as "
        "a checkable step is the harness's stipulated theta; missed "
        "steps lower coverage, never soundness.",
    )

    def to_dict(self):
        d = asdict(self)
        d["steps"] = [asdict(s) for s in self.steps]
        return d


def seal(body, chain):
    """Append body to an in-memory chain, PL-kernel byte format."""
    prev = chain[-1]["sha"] if chain else "GENESIS"
    sha = hashlib.sha256((prev + json.dumps(body, sort_keys=True))
                         .encode()).hexdigest()[:16]
    chain.append({**body, "sha_prev": prev, "sha": sha})
    return chain[-1]


def replay(chain):
    """True iff every link recomputes. Identical to the kernel's replay."""
    prev = "GENESIS"
    for g in chain:
        body = {k: v for k, v in g.items() if k not in ("sha", "sha_prev")}
        want = hashlib.sha256((prev + json.dumps(body, sort_keys=True))
                              .encode()).hexdigest()[:16]
        if g["sha_prev"] != prev or g["sha"] != want:
            return False
        prev = g["sha"]
    return True
