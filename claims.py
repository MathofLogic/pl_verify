"""
claims.py — the /pl_verify ledger, priced by the Atlas LEDGER plate.
==========================================================================
Checked claims name entries in plv_checks:CHECKS, run by the gate.
Calibration numbers are cited to the gate that recomputes them on the
bundled slice; model-performance claims do not exist here, by design.
"""

SECTIONS = [
    ("The verdict triad", [
        {"claim": "the pipeline returns CERTIFIED / REFUTED / ABSTAIN "
                  "on their exemplars — never a bare boolean",
         "check": "pipeline_verdict_triad", "tier": "FORCED"},
        {"claim": "REFUTED is FORCED and names the step with what it "
                  "actually recomputes to — one counterexample decides",
         "check": "refuted_names_the_step", "tier": "FORCED"},
        {"claim": "CERTIFIED caps itself at STIPULATED: what counts as "
                  "a checkable step is this instrument's own theta",
         "check": "certified_caps_stipulated", "tier": "FORCED"},
    ]),
    ("The sealing machinery (the formerly untested part)", [
        {"claim": "every session's manifest is a sha-linked chain that "
                  "replays by seal arithmetic alone",
         "check": "pipeline_chain_replays", "tier": "FORCED"},
        {"claim": "a new session over an intact manifest continues the "
                  "chain — history accumulates, it is not clobbered",
         "check": "pipeline_resumes_intact_history", "tier": "FORCED"},
        {"claim": "a tampered manifest suspends sealing: verdicts flow, "
                  "seals read SUSPENDED, the file is preserved as "
                  "evidence byte-for-byte",
         "check": "pipeline_refuses_broken_history", "tier": "FORCED"},
        {"claim": "the committed calibration manifest replays "
                  "independently of the pipeline that wrote it",
         "check": "committed_manifest_replays", "tier": "FORCED"},
    ]),
    ("Calibration (recomputed by the gate on the bundled slice)", [
        {"claim": "coverage on reference solutions is at least 220/250 "
                  "with certified-vs-gold agreement at 100% and zero "
                  "false refutations",
         "cite": "tests/run.py CALIBRATION section (recomputed every "
                 "build)", "tier": "EMPIRICAL"},
        {"claim": "corrupted derivations never certify (0 tolerance, "
                  "recomputed every build)",
         "cite": "tests/run.py SOUNDNESS section", "tier": "EMPIRICAL"},
    ]),
    ("Standing stipulations", [
        {"claim": "no model-performance claim exists here: the grader "
                  "grades; whichever model produced the text is out of "
                  "frame",
         "cite": "bench/run_gsm8k.py non-claims", "tier": "STIPULATED"},
        {"claim": "free-text extraction is deliberately conservative: "
                  "ambiguous text abstains rather than risking a false "
                  "refutation — coverage is spent to buy soundness",
         "cite": "plverify/extract.py guard comments",
         "tier": "STIPULATED"},
    ]),
]
