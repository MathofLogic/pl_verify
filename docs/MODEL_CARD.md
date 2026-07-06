---
license: mit
tags: [verification, math, evaluation, selective-prediction, gsm8k]
pipeline_tag: other
---

# PL-Verify — a verifier, not a model

**This repository contains no weights and answers no questions.** It is
a deterministic verification harness for math derivations: it recomputes
every checkable step of a proposed solution with exact rational
arithmetic and returns CERTIFIED / REFUTED / ABSTAIN with an evidence
tier, named reasons, and a sealed (hash-chained, replayable) manifest.

## Intended use

Attach to any model's math-benchmark outputs to produce honest
selective-prediction reports: **coverage** (how often the harness
certifies) and **accuracy-on-certified**, together, with abstention
priced. Also usable as a dataset linter (it found a real arithmetic
error in the GSM8K test split) and as a training-signal filter
(certified-only distillation data).

## Calibration (measured, full GSM8K test split, n=1319)

| pass | certified | refuted | abstain | note |
|---|---|---|---|---|
| clean reference solutions | 95.2% | 0.1% | 4.7% | gold agreement 100.0% |
| one corrupted step each (n=1301) | 0.0% | 100.0% | 0.0% | 0 soundness failures |
| annotations stripped (free text) | 75.4% | 0.1% | 24.6% | model-output regime |

The only clean-pass refutation is a verified error in the dataset
itself ($32 - $20 = $300). Reproduce with
`python bench/run_gsm8k.py --data <gsm8k test.jsonl> --n 1319`.

## Out-of-scope / limitations (the standing non-claims)

- It does NOT judge whether equations model the word problem — a
  CERTIFIED derivation can be a correct computation of the wrong thing.
- It does NOT parse algebra with variables, unit conversions, or
  geometry; such content is ABSTAIN territory, reported as such.
- It has evaluated NO model. Any model numbers you see elsewhere with
  this harness's name must come with the coverage/accuracy pair and a
  replayable manifest, or treat them as UNPAID.
- Certificates cap at STIPULATED by construction: extraction is the
  harness's own stipulated theta.

## Provenance

Part of the MathofLogic project (PL / rigor / PL-lessons / PL-Verify).
Seal format is byte-compatible with the PL kernel's replay().
