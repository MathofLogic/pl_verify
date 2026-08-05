# PL-Verify

**The model proposes; PL disposes. A verification harness for math derivations — never a solver, always a grader. Verdicts are tiered, priced, and sealed.**

PL-Verify is what you attach to a math benchmark run instead of trusting
it. Feed it any model's chain-of-thought output (or a human's, or a
dataset's reference solutions) and it recomputes every checkable step
with exact rational arithmetic, then returns one of three verdicts —
never a bare boolean:

- **CERTIFIED** — every extracted computation recomputes, and the final
  answer is *produced by* one of them. Tier: **STIPULATED**, always —
  the self-cap. Which text counts as a checkable step is the harness's
  own stipulated θ, and a verifier that graded its certificates FORCED
  would be lying about its extraction.
- **REFUTED** — some step recomputes to a different value. Tier:
  **FORCED** — one exhibited counterexample decides it, weakest link,
  and the offending step is named in the verdict with what it actually
  equals.
- **ABSTAIN** — unverifiable by this instrument: nothing checkable
  extracted, or a final answer no verified computation produces.
  Abstention is priced in every report, never hidden.

It is **not an LLM and holds no weights**. It parses no natural language
semantics. It cannot tell you whether the equations modelled the word
problem correctly — and its manifest says so, in every verdict, as a
standing non-claim.

## Measured before claimed

The instrument was calibrated on the **full GSM8K test split (n = 1319,
openai/grade-school-math, MIT)** before this README was written. Three
passes: the reference solutions as-is (*clean*), the same with one
calculator annotation arithmetically corrupted per problem
(*corrupted*, n = 1301 corruptible), and the same with all `<<>>`
annotations stripped so only the free-text extractor works (*stripped* —
the regime real model outputs live in).

| pass | certified (coverage) | refuted | abstain | headline |
|---|---|---|---|---|
| clean | **95.2%** | 0.1% | 4.7% | certified↔gold agreement **100.0%** (0 disagreements) |
| corrupted | **0.0%** | 100.0% | 0.0% | catch rate **100.0%**, soundness failures **0** |
| stripped | **75.4%** | 0.1% | 24.6% | free-text extraction alone |

The single refutation in the clean and stripped passes — across all
1319 problems — is a **genuine error in the GSM8K test split itself**
(`$32 - $20 = $300`, problem intact in the raw data), which the harness
caught and this repo documents. Zero false refutations survive; the
build gate enforces that any refutation of a reference solution must be
on the manually-verified dataset-error list, or the build fails.

**What is *not* claimed:** any model's performance. No model ran here.
This calibrated the instrument. The model column is a **declared stub**,
printed as such in every bench run, until someone actually runs a model
through it — see below for exactly how.

## Quick start

```bash
pip install sympy
python pipeline.py                       # one worked verdict + report
python bench/run_gsm8k.py                # reproduce the calibration (250 sample)
python bench/run_gsm8k.py --data path/to/gsm8k_test.jsonl --n 1319   # full
python tests/run.py                      # the build gate
```

```python
from pipeline import PLVerifyPipeline
pipe = PLVerifyPipeline()

v = pipe("She sells 16 - 3 - 4 = 9 eggs. Then 9 * 2 = 18. #### 18")
v["status"], v["tier"]                   # ('CERTIFIED', 'STIPULATED')

v = pipe("She sells 16 - 3 - 4 = 9 eggs. Then 9 * 2 = 19. #### 19")
v["status"], v["reasons"]                # ('REFUTED', ['step recomputes
                                         #   false: 9*2 = 18, not 19'])
```

### Filling the model column (the intended deployment)

```python
answers  = [my_model(q) for q in gsm8k_questions]   # ANY model
verdicts = pipe(answers)
print(pipe.report(verdicts))            # coverage table + sealed chain
```

Then report the honest **pair** — coverage and accuracy-on-certified —
never one flattering number. The selective-answering policy is one
line: emit only certified answers, abstain otherwise. Every session
seals a hash-chained manifest (byte-compatible with the PL kernel's
`replay()`), so an evaluation report is a verifiable structure, not a
screenshot.

## What a certificate is, exactly

Extraction takes GSM8K-style `<<a=b>>` calculator annotations plus
conservative free-text equations — including chains (`2*4 + 3*6 = 8 +
18 = 26`, verified pairwise, one false link sinks it), fraction and
mixed-number claims (`= 3 1/2`), percents (`100 * 20% = 20`), unicode
dashes, currency and thousands separators. Every step is recomputed
under exact rational semantics (sympy); decimals verify at the precision
the author wrote.

The extractor is deliberately **precision-first**: anything that risks
being a fragment of a larger expression — implicit multiplication,
truncated space-grouped numbers, algebra variables, unit-ambiguous
percents — is *skipped*, never guessed at, because a false extraction
becomes a false refutation and soundness is the product. Every guard in
`plverify/extract.py` exists because a real GSM8K sentence defeated the
naive pattern; `docs/CALIBRATION.md` is the iteration log, kept because
the discipline says the instrument's own debugging history is part of
its documentation.

## Design commitments

- **Never a solver.** There is no path from question text to answer in
  this codebase, and there never will be — a verifier that quietly
  solves has erased the load history of who did the work.
- **Refutations are pure.** Skip on ambiguity; refute only on a
  recomputed counterexample. Zero tolerance in the gate.
- **The honest pair.** Coverage and accuracy-on-certified, always
  together; abstention priced, never hidden.
- **Non-claims ship in the verdict.** Every `Verdict` carries what a
  certificate does *not* mean.
- **Benchmark before claim.** The measured table above predates every
  performance sentence in this README; the model column stays a
  declared stub until run.

## Repository map

```
plverify/          core (tiers, seal/replay) · extract · verify
pipeline.py        the HF-facing wrapper (grader, not model)
bench/             run_gsm8k.py + vendored 250-sample (PROVENANCE.md)
tests/run.py       fixtures + live calibration invariants + honesty check
docs/              CALIBRATION.md (the iteration log), MODEL_CARD.md
.github/           CI runs the full gate on every push and PR
```

## Relation to the MathofLogic repos

The vocabulary (tiers, weakest link, self-cap, seals, non-claims) is
**/PL**'s; the model-proposes-harness-disposes pattern is **/rigor**'s
JIG; the training for reading instruments like this one is
**/PL-lessons**. PL-Verify is stdlib + sympy and stands alone.

## License

MIT. GSM8K sample data © OpenAI, MIT, provenance in
`bench/data/PROVENANCE.md`.
