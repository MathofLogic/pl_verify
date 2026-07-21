"""
plv_checks.py — the /pl_verify check registry.
==========================================================================
Named, executable checks backing the root claims.py ledger; the gate
runs every one. The emphasis is deliberate: the sealing machinery —
the component whose job is tamper-evidence — gets the most checks,
because it was the least tested part of this repo until the lineage
audit named that as the family blind spot.
"""
from __future__ import annotations
import json, os, pathlib, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

GOOD = "She sells 16 - 3 - 4 = 9 eggs. 9 * 2 = 18. #### 18"
BAD = "She sells 16 - 3 - 4 = 8 eggs. 8 * 2 = 16. #### 16"
VAGUE = "The answer feels like it should be forty-two. #### 42"


def _pipe(path):
    from pipeline import PLVerifyPipeline
    return PLVerifyPipeline(manifest_path=str(path))


def chk_pipeline_verdict_triad():
    """The pipeline returns the three verdicts on their exemplars:
    CERTIFIED on a recomputable derivation, REFUTED on a wrong step,
    ABSTAIN where nothing checkable extracts."""
    with tempfile.TemporaryDirectory() as td:
        p = _pipe(pathlib.Path(td) / "m.json")
        got = [p(GOOD)["status"], p(BAD)["status"], p(VAGUE)["status"]]
        return got == ["CERTIFIED", "REFUTED", "ABSTAIN"]


def chk_pipeline_chain_replays():
    """The manifest the pipeline writes is a sha-linked chain that
    replays by seal arithmetic alone."""
    from plverify import replay
    with tempfile.TemporaryDirectory() as td:
        mp = pathlib.Path(td) / "m.json"
        p = _pipe(mp)
        p([GOOD, BAD, VAGUE])
        return replay(json.loads(mp.read_text())) and \
            len(json.loads(mp.read_text())) == 3


def chk_pipeline_resumes_intact_history():
    """A second session over an intact manifest continues the chain
    instead of clobbering it — history accumulates."""
    from plverify import replay
    with tempfile.TemporaryDirectory() as td:
        mp = pathlib.Path(td) / "m.json"
        _pipe(mp)(GOOD)
        _pipe(mp)(BAD)
        chain = json.loads(mp.read_text())
        return len(chain) == 2 and replay(chain)


def chk_pipeline_refuses_broken_history():
    """A tampered manifest suspends sealing: verdicts still flow, the
    seal reads SUSPENDED with a named rider, and the broken file is
    preserved byte-for-byte as evidence."""
    with tempfile.TemporaryDirectory() as td:
        mp = pathlib.Path(td) / "m.json"
        _pipe(mp)(GOOD)
        d = json.loads(mp.read_text())
        s = d[0]["sha"]
        d[0]["sha"] = ("0" if s[0] != "0" else "1") + s[1:]
        mp.write_text(json.dumps(d, indent=1))
        before = mp.read_bytes()
        out = _pipe(mp)(BAD)
        return (out["status"] == "REFUTED"
                and out["seal"] == "SUSPENDED"
                and "history_rider" in out
                and mp.read_bytes() == before)


def chk_refuted_names_the_step():
    """REFUTED is FORCED and names the offending computation with what
    it actually equals — one exhibited counterexample decides."""
    with tempfile.TemporaryDirectory() as td:
        out = _pipe(pathlib.Path(td) / "m.json")(BAD)
        return (out["tier"] == "FORCED"
                and any("9" in str(r) for r in out.get("reasons", [])))


def chk_certified_caps_stipulated():
    """CERTIFIED never grades itself above STIPULATED — which text
    counts as a checkable step is the harness's own theta."""
    with tempfile.TemporaryDirectory() as td:
        out = _pipe(pathlib.Path(td) / "m.json")(GOOD)
        return out["status"] == "CERTIFIED" and out["tier"] == "STIPULATED"


def chk_committed_manifest_replays():
    """The committed calibration manifest replays independently."""
    from plverify import replay
    mp = ROOT / "manifests" / "plverify_manifest.json"
    chain = json.loads(mp.read_text())
    return replay(chain) and len(chain) >= 3


CHECKS = {
    "pipeline_verdict_triad": chk_pipeline_verdict_triad,
    "pipeline_chain_replays": chk_pipeline_chain_replays,
    "pipeline_resumes_intact_history": chk_pipeline_resumes_intact_history,
    "pipeline_refuses_broken_history": chk_pipeline_refuses_broken_history,
    "refuted_names_the_step": chk_refuted_names_the_step,
    "certified_caps_stipulated": chk_certified_caps_stipulated,
    "committed_manifest_replays": chk_committed_manifest_replays,
}
