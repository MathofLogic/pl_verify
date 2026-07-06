#!/usr/bin/env python3
"""
bench/run_gsm8k.py — calibrate the harness on GSM8K, honestly.
==========================================================================
What this measures (and what it does not):

This is a CALIBRATION of the instrument, not an evaluation of any model.
GSM8K reference solutions are known-good derivations; corrupting one
computation in each produces known-bad ones. Running the harness over
both characterises the instrument itself:

  clean pass      — certification coverage on known-good derivations,
                    and certified-answer agreement with gold (#### N)
  corrupted pass  — catch rate: corrupted derivations must NOT certify
                    (REFUTED preferred; ABSTAIN acceptable; CERTIFIED is
                    a soundness failure and fails the build)
  stripped pass   — the same, with <<>> calculator annotations removed:
                    the free-text extractor working alone, which is the
                    regime real model outputs live in

The model-evaluation column is a DECLARED STUB. No model ran here; no
model claim is made. To fill it: generate solutions with any model, feed
them through plverify.verify, and report the coverage/accuracy pair.

Every run seals a manifest (PL chain format) to bench/out/.
"""
import argparse, json, pathlib, random, re, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from plverify import verify, seal, replay
from plverify.extract import strip_annotations, ANNOT


def load(path, n, seed):
    rows = [json.loads(l) for l in pathlib.Path(path).read_text()
            .splitlines() if l.strip()]
    random.Random(seed).shuffle(rows)
    return rows[:n]


def gold_of(answer_text):
    m = re.search(r"####\s*(-?[\d,]+(?:\.\d+)?)", answer_text)
    return m.group(1).replace(",", "") if m else None


def corrupt(answer_text, seed):
    """Flip the RESULT of one calculator annotation — a wrong computation
    a grader must catch. Returns None if there is nothing to corrupt."""
    ms = list(ANNOT.finditer(answer_text))
    if not ms:
        return None
    m = random.Random(seed).choice(ms)
    expr, res = m.group(1), m.group(2).strip()
    try:
        bumped = str(int(float(res.replace(",", ""))) + 1)
    except ValueError:
        return None
    return (answer_text[:m.start()] + f"<<{expr}={bumped}>>"
            + answer_text[m.end():])


def run(rows, mode):
    stats = {"n": 0, "CERTIFIED": 0, "REFUTED": 0, "ABSTAIN": 0,
             "cert_correct": 0, "cert_wrong": 0}
    for r in rows:
        text = r["answer"]
        gold = gold_of(text)
        if mode == "corrupted":
            text = corrupt(text, seed=hash(r["question"]) & 0xffff)
            if text is None:
                continue
        if mode == "stripped":
            text = strip_annotations(text)
        v = verify(text, question=r["question"])
        stats["n"] += 1
        stats[v.status] += 1
        if v.status == "CERTIFIED" and gold is not None:
            ok = False
            try:
                ok = abs(float(v.final_answer) - float(gold)) < 1e-9
            except (TypeError, ValueError):
                ok = v.final_answer == gold
            stats["cert_correct" if ok else "cert_wrong"] += 1
    return stats


def pct(a, b):
    return f"{100.0 * a / b:.1f}%" if b else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "bench/data/"
                                          "gsm8k_test_sample.jsonl"))
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seed", type=int, default=20260706)
    a = ap.parse_args()

    rows = load(a.data, a.n, a.seed)
    out = ROOT / "bench/out"
    out.mkdir(exist_ok=True)
    chain, t0 = [], time.time()
    print(f"\n  PL-Verify calibration — GSM8K sample n={len(rows)} "
          f"(seed {a.seed})\n  " + "-" * 66)

    results = {}
    for mode in ("clean", "corrupted", "stripped"):
        s = run(rows, mode)
        results[mode] = s
        seal({"mode": mode, **s}, chain)
        cov = pct(s["CERTIFIED"], s["n"])
        print(f"  {mode:<10} n={s['n']:<4} certified={cov:<7} "
              f"refuted={pct(s['REFUTED'], s['n']):<7} "
              f"abstain={pct(s['ABSTAIN'], s['n'])}")
        if mode == "clean":
            print(f"  {'':10} certified-answer agreement with gold: "
                  f"{pct(s['cert_correct'], s['CERTIFIED'])} "
                  f"({s['cert_wrong']} disagreements)")
        if mode in ("corrupted",):
            caught = s["REFUTED"] + s["ABSTAIN"]
            print(f"  {'':10} catch rate (corrupted must not certify): "
                  f"{pct(caught, s['n'])}  "
                  f"[soundness failures: {s['CERTIFIED']}]")

    hard = results["corrupted"]["CERTIFIED"]
    verdict = "PASS" if hard == 0 else "FAIL"
    seal({"verdict": f"{verdict}/STIPULATED",
          "soundness_failures": hard,
          "non_claim": "no model was evaluated; the model column is a "
                       "declared stub"}, chain)
    (out / "manifest.json").write_text(json.dumps(chain, indent=1))
    print("  " + "-" * 66)
    print(f"  verdict {verdict}/STIPULATED   chain {len(chain)} sealed, "
          f"replay={'intact' if replay(chain) else 'BROKEN'}   "
          f"{time.time() - t0:.1f}s")
    print("  NOT claimed: any model performance. This calibrated the "
          "instrument;\n  the model column is a declared stub until a "
          "model is actually run.\n")
    sys.exit(0 if hard == 0 else 1)


if __name__ == "__main__":
    main()
