# Calibration log — how the extractor earned its guards

Method: run the harness over GSM8K reference solutions (known-good),
treat every refutation as a bug in the instrument until proven a bug in
the data, fix, re-run. Soundness target: zero false refutations at
n=1319. Each round below is a sealed fact of this repo's history.

| round | clean refuted | root causes found | fix |
|---|---|---|---|
| 1 | 11/250 (4.4%) | percent signs ("100% - 70% = 30%"); fraction & mixed-number claims truncated ("= 1/20", "= 3 1/2"); one-sided percents ("100 * 20% = 20"); implicit multiplication tails ("(1/2) 278 + 11"); space-grouped thousands ("$409 500"); algebra variables mangled ("2x - 4") | N% -> (N/100) both sides; fraction/mixed claim patterns; x100-tolerant one-sided percents, else SKIP; truncation guards (preceding char, trailing digits, leading zeros, digit-attached x) |
| 2 | 5/250 (2.0%) | matches that are the TAIL of larger expressions (preceded by ')', digit, operator, unicode ¾) | preceding-non-space-char guard extended |
| 3 | 5/1319 (0.4%) | equation CHAINS ("2*4 + 3*6 = 8 + 18 = 26") falsely split; claims gluing across newlines | pairwise chain verification; same-line-only equation whitespace |
| 4 | 2/1319 | en-dash subtraction ("1 – 3/4 = 1/4"); '='-preceded tails of word-interrupted chains | unicode dashes normalised as '-'; '=' added to guard |
| 5 | **1/1319** | `$32 - $20 = $300` — confirmed present in the raw GSM8K test split: a genuine dataset annotation error | none. The instrument is doing its job. Encoded in the gate as the one permitted refutation. |

Standing rule the log demonstrates: when the verifier disagrees with
known-good data, the verifier is guilty until the raw data is checked —
and precisely once in 1319 problems, the data was.
