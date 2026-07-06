#!/usr/bin/env python3
"""
pipeline.py — the HF-facing wrapper. The model proposes; this disposes.
==========================================================================
PLVerifyPipeline is NOT a model and holds no weights. It is a grader:
feed it any model's chain-of-thought math output (or a human's), and it
returns a tiered, priced, sealed verdict — never a bare boolean.

    from pipeline import PLVerifyPipeline
    pipe = PLVerifyPipeline()

    out = pipe("She sells 16 - 3 - 4 = 9 eggs. 9 * 2 = 18. #### 18")
    out["status"]        # CERTIFIED | REFUTED | ABSTAIN
    out["tier"]          # certificates cap at STIPULATED, by construction
    out["final_answer"]  # "18"
    out["reasons"]       # why, when not certified

    batch = pipe([sol1, sol2, ...])          # list in, list out
    print(pipe.report(batch))                # coverage table, markdown
    pipe.manifest_path                       # sealed chain of this session

Composing with a model (the intended deployment):

    answers = [my_model(q) for q in questions]      # ANY model
    verdicts = pipe(answers)
    keep = [v for v in verdicts if v["status"] == "CERTIFIED"]
    # report the honest pair: coverage (len(keep)/len(all)) and
    # accuracy-on-certified — never a single flattering number.

Selective answering in one line: emit the answer only when certified,
abstain otherwise. Abstention is priced in the report, not hidden.
"""
import json, pathlib, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from plverify import verify, seal, replay


class PLVerifyPipeline:
    task = "math-derivation-verification"          # not text-generation

    def __init__(self, manifest_path="plverify_manifest.json"):
        self.chain = []
        self.manifest_path = manifest_path

    def __call__(self, solutions, questions=None):
        single = isinstance(solutions, str)
        sols = [solutions] if single else list(solutions)
        qs = ([questions] if isinstance(questions, str) else
              questions or [None] * len(sols))
        out = []
        for sol, q in zip(sols, qs):
            v = verify(sol, question=q)
            d = v.to_dict()
            seal({"status": v.status, "tier": v.tier,
                  "final": v.final_answer, "n_verified": v.n_verified,
                  "n_refuted": v.n_refuted}, self.chain)
            d["seal"] = self.chain[-1]["sha"]
            out.append(d)
        pathlib.Path(self.manifest_path).write_text(
            json.dumps(self.chain, indent=1))
        return out[0] if single else out

    def report(self, verdicts):
        """Markdown coverage report. The honest pair, never one number."""
        if isinstance(verdicts, dict):
            verdicts = [verdicts]
        n = len(verdicts)
        by = {"CERTIFIED": 0, "REFUTED": 0, "ABSTAIN": 0}
        for v in verdicts:
            by[v["status"]] += 1
        pct = lambda k: f"{100.0 * by[k] / n:.1f}%" if n else "n/a"
        lines = [
            "## PL-Verify report", "",
            f"| n | certified (coverage) | refuted | abstain |",
            f"|---|---|---|---|",
            f"| {n} | {by['CERTIFIED']} ({pct('CERTIFIED')}) "
            f"| {by['REFUTED']} ({pct('REFUTED')}) "
            f"| {by['ABSTAIN']} ({pct('ABSTAIN')}) |", "",
            f"chain: {len(self.chain)} sealed, replay "
            f"{'intact' if replay(self.chain) else 'BROKEN'}", "",
            "_A certificate says: every extracted computation recomputes "
            "and the final answer is produced by one of them. It does NOT "
            "say the reasoning modelled the problem correctly — that is "
            "outside this instrument's theta, and the manifest says so. "
            "Composite certificates cap at STIPULATED._",
        ]
        return "\n".join(lines)


if __name__ == "__main__":
    pipe = PLVerifyPipeline()
    demo = ("Janet sells 16 - 3 - 4 = 9 duck eggs a day. "
            "She makes 9 * 2 = $18 every day. #### 18")
    v = pipe(demo)
    print(json.dumps({k: v[k] for k in
                      ("status", "tier", "final_answer", "seal")}, indent=1))
    print(pipe.report(v))
