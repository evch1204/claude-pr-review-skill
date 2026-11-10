# Benchmark comparison

Recall is weighted by severity (blocker 3, major 2, minor 1). FP = findings the blind grader checked against the code and judged wrong.

## Overall

| Reviewer | Pass rate | Weighted recall | Bugs found | False positives | Decoys flagged | Verdict correct | Actionability (1-5) | Avg words | Avg tokens | Avg time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 100% | 25/25 | 0 | 0 | 4/4 | 5.0 | 927 | 66620 | 128 |

## js-clean-rate-limiter

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 0/0 | n/a | 0 | 0 | ✅ | 3 | 452 | 58169 | 73.8 |

## node-transfer-messy-pr

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 11/11 | 100% | 0 | 0 | ✅ | 0 | 1193 | 68731 | 126.2 |

## py-order-search

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 2 | 1088 | 69963 | 104.1 |

## ts-comments-markdown

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 1 | 974 | 69617 | 208.9 |
