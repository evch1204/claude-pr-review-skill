# Benchmark comparison

Recall is weighted by severity (blocker 3, major 2, minor 1). FP = findings the blind grader checked against the code and judged wrong.

## Overall

| Reviewer | Pass rate | Weighted recall | Bugs found | False positives | Decoys flagged | Verdict correct | Actionability (1-5) | Avg words | Avg tokens | Avg time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 100% | 25/25 | 0 | 0 | 4/4 | 5.0 | 924 | 60107 | 220 |
| anthropic_code_review | 81% | 84% | 19/25 | 0 | 0 | 3/4 | 3.8 | 408 | 47400 | 145 |
| spillwave | 75% | 100% | 25/25 | 1 | 0 | 3/4 | 3.2 | 1816 | 62183 | 194 |
| without_skill | 75% | 100% | 25/25 | 1 | 0 | 3/4 | 4.2 | 995 | 43655 | 147 |

## js-clean-rate-limiter

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 0/0 | n/a | 0 | 0 | ✅ | 3 | 430 | 50778 | 128.1 |
| anthropic_code_review | 100% | 0/0 | n/a | 0 | 0 | ✅ | 0 | 152 | 44663 | 116.1 |
| spillwave | 0% | 0/0 | n/a | 1 | 0 | ❌ | 8 | 1250 | 61111 | 190.1 |
| without_skill | 0% | 0/0 | n/a | 1 | 0 | ❌ | 4 | 752 | 42752 | 130.5 |

## node-transfer-messy-pr

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 11/11 | 100% | 0 | 0 | ✅ | 0 | 1170 | 64673 | 237.6 |
| anthropic_code_review | 94% | 10/11 | 95% | 0 | 0 | ✅ | 3 | 719 | 50466 | 166.2 |
| spillwave | 100% | 11/11 | 100% | 0 | 0 | ✅ | 6 | 2338 | 63565 | 190.8 |
| without_skill | 100% | 11/11 | 100% | 0 | 0 | ✅ | 0 | 1206 | 43872 | 130.8 |

## py-order-search

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 3 | 1139 | 62450 | 276.5 |
| anthropic_code_review | 83% | 6/7 | 93% | 0 | 0 | ✅ | 4 | 522 | 48458 | 156.1 |
| spillwave | 100% | 7/7 | 100% | 0 | 0 | ✅ | 9 | 2007 | 63114 | 219.2 |
| without_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 5 | 1140 | 45538 | 190.7 |

## ts-comments-markdown

| Reviewer | Pass rate | Found | Weighted recall | FP | Decoys | Verdict ok | Nits | Words | Tokens | Time (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| with_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 4 | 958 | 62526 | 237.2 |
| anthropic_code_review | 45% | 3/7 | 64% | 0 | 0 | ❌ | 0 | 241 | 46015 | 142.4 |
| spillwave | 100% | 7/7 | 100% | 0 | 0 | ✅ | 12 | 1669 | 60943 | 177.2 |
| without_skill | 100% | 7/7 | 100% | 0 | 0 | ✅ | 6 | 883 | 42457 | 134.7 |
