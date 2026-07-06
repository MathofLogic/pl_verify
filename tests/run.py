#!/usr/bin/env python3
"""tests/run.py — the PL-Verify build gate.

Three layers, all mandatory:

  1. FIXTURES     every behaviour the harness claims, exhibited on a
                  hand-built case: certify, refute, abstain (two ways),
                  chains pairwise, one-sided percents skip-not-refute,
                  unicode dashes, mixed numbers, frozen originals,
                  seal/replay tamper detection, determinism.
  2. CALIBRATION  the vendored 250-problem GSM8K sample re-run live.
                  Soundness invariants are hard:
                    - corrupted derivations NEVER certify (0 tolerance)
                    - certified answers agree with gold 100%
                    - clean-pass refutations are EXACTLY the known,
                      manually verified dataset error (the $32-$20=$300
                      typo in the raw GSM8K test split) — any other
                      refutation of a reference solution is a false
                      refutation and fails this build.
  3. HONESTY      the model column is a stub and must SAY so: the bench
                  output must contain the non-claim.
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from plverify import verify, seal, replay
from plverify.extract import strip_annotations

fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail else ""))
    if not ok:
        fails.append(name)


print("FIXTURES")
good = ("Janet sells 16 - 3 - 4 = <<16-3-4=9>>9 eggs a day.\n"
        "She makes 9 * 2 = $<<9*2=18>>18 every day.\n#### 18")
v = verify(good)
check("clean derivation certifies at STIPULATED (the self-cap)",
      v.status == "CERTIFIED" and v.tier == "STIPULATED"
      and v.final_answer == "18")
v2 = verify(good.replace("<<9*2=18>>", "<<9*2=19>>"))
check("one corrupted step refutes, FORCED (a recomputed counterexample "
      "decides it)", v2.status == "REFUTED" and v2.tier == "FORCED")
check("prose-only derivations abstain (nothing checkable)",
      verify("It follows from symmetry. #### 42").status == "ABSTAIN")
check("an unlinked final abstains (right words, no verified producer)",
      verify("Well 2 + 2 = 4 as we know. #### 42").status == "ABSTAIN")
ch = verify("So 2 * 4 + 3 * 6 = 8 + 18 = 26. #### 26")
check("chains verify pairwise and the chain end links the final",
      ch.status == "CERTIFIED" and ch.n_verified == 2)
chb = verify("So 2 * 4 + 3 * 6 = 8 + 19 = 26. #### 26")
check("a false middle link sinks the chain (weakest link)",
      chb.status == "REFUTED")
check("one-sided percents verify under the x100 reading",
      verify("The box has 100 * 20% = 20 more pods. #### 20").status
      == "CERTIFIED")
check("unit-ambiguous percents are SKIPPED, never refuted",
      all(s.status != "REFUTED"
          for s in verify("She saves 20% = 45 dollars").steps))
check("en-dash subtraction parses (1 \u2013 3/4 = 1/4)",
      verify("make up 1 \u2013 3/4 = 1/4 of the total. #### 42")
      .n_verified == 1)
check("mixed-number claims parse (5 - 1 - 1/2 = 3 1/2)",
      verify("he had 5 - 1 - 1/2 = 3 1/2 hours left. #### 42")
      .n_verified == 1)
check("algebra variables are prose to this instrument (2x + 4 skipped)",
      verify("so 2x + 4 - 4 = 28 gives x = 12").n_verified == 0
      or all(s.status != "REFUTED"
             for s in verify("so 2x + 4 - 4 = 28").steps))
check("verify() is deterministic (same text, identical verdict dict)",
      verify(good).to_dict() == verify(good).to_dict())

chain = []
seal({"a": 1}, chain)
seal({"a": 2}, chain)
tam = json.loads(json.dumps(chain))
tam[0]["a"] = 99
check("seal/replay: intact chain replays; tampered chain breaks",
      replay(chain) and not replay(tam))

print("\nCALIBRATION (vendored 250-problem GSM8K sample, live)")
KNOWN_DATASET_ERRORS = {("32 - 20", "300")}   # verified against raw split
rows = [json.loads(l) for l in
        (ROOT / "bench/data/gsm8k_test_sample.jsonl").read_text()
        .splitlines()]
import re


def gold_of(t):
    m = re.search(r"####\s*(-?[\d,]+(?:\.\d+)?)", t)
    return m.group(1).replace(",", "") if m else None


cert = agree = refuted_bad = 0
for r in rows:
    v = verify(r["answer"])
    if v.status == "CERTIFIED":
        cert += 1
        if abs(float(v.final_answer) - float(gold_of(r["answer"]))) < 1e-9:
            agree += 1
    if v.status == "REFUTED":
        bad = next(s for s in v.steps if s.status == "REFUTED")
        if (bad.expr, bad.claimed) not in KNOWN_DATASET_ERRORS:
            refuted_bad += 1
check(f"coverage on reference solutions is high (got {cert}/250)",
      cert >= 220)
check("certified answers agree with gold 100%", agree == cert,
      f"{agree}/{cert}")
check("zero false refutations: every refuted reference solution is a "
      "known, manually verified dataset error", refuted_bad == 0)

corrupted_cert = 0
from bench.run_gsm8k import corrupt
for r in rows:
    t = corrupt(r["answer"], seed=hash(r["question"]) & 0xffff)
    if t and verify(t).status == "CERTIFIED":
        corrupted_cert += 1
check("SOUNDNESS: corrupted derivations never certify (0 tolerance)",
      corrupted_cert == 0)

print("\nHONESTY")
r = subprocess.run([sys.executable, str(ROOT / "bench/run_gsm8k.py")],
                   capture_output=True, text=True, timeout=300)
check("bench exits 0 and prints the model-column non-claim",
      r.returncode == 0 and "NOT claimed: any model performance"
      in r.stdout)

print("\n" + ("BUILD PASSED — sound, calibrated, and honest about it"
              if not fails else f"BUILD FAILED: {fails}"))
sys.exit(1 if fails else 0)
