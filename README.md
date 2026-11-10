# pr-review: a PR review skill for Claude Code (and Codex)

`pr-review` is a skill that reviews pull requests the way a careful senior engineer does. It finds the problems that matter, proves each one with a concrete "breaks when" scenario, leaves out noise, and ends with a clear merge verdict.

It covers seven areas, mapped to industry guidance:

| Area | What it checks | Based on |
|---|---|---|
| Correctness | Edge cases, error paths, concurrency, regressions, blast radius of global code, silent wrong answers | Google eng-practices "Functionality" |
| Security | Injection, XSS, access control (IDOR), CSRF, secrets, crypto, SSRF, dependencies, AI/LLM risks | OWASP Top 10 (2025), OWASP LLM Top 10 |
| Testing | New behavior tested, tests would fail if code broke, edge and error cases, CI status | Google "Tests" |
| Readability | Names, single responsibility, DRY (reuse existing helpers), comments explain *why* | Google "Complexity / Naming / Comments" |
| Performance | Complexity at realistic scale, N+1 queries, unbounded memory | |
| Conventions | The repo's own CLAUDE.md / AGENTS.md / CONTRIBUTING rules, quoted | Google "Consistency" |
| PR quality | Focused scope, size (about 400 lines), description (what/why/tested), commit messages | SmartBear/Cisco study, Google "small CLs" |

Severity follows Conventional Comments' blocking/non-blocking idea: 🔴 blocking, 🟡 should fix, ⚪ nit (at most 3), and ❓ question.

## Install

```bash
git clone <this repo> && cd claude-pr-review-skill
./install.sh            # links the skill into ~/.claude/skills and ~/.codex/skills
./install.sh claude     # Claude Code only
./install.sh --uninstall
```

The install is a symlink, so a `git pull` here updates every installed copy. To review GitHub PRs you need the `gh` CLI logged in (`gh auth login`).

## Use

| Claude Code | Codex | Reviews |
|---|---|---|
| `/pr-review 123` | `$pr-review 123` | GitHub PR #123 in the current repo |
| `/pr-review <PR URL>` | `$pr-review <PR URL>` | Any PR |
| `/pr-review` | `$pr-review` | Your current branch vs. the default branch |
| "review my PR", "is this ready to merge?" | same | Picked up from the description |

**What a review looks like:** a verdict, then **at most two comments**. Findings are grouped by the change that fixes them, so the author gets one fix to make instead of eight separate chores:

```
**Verdict: ❌ Request changes**: <why, in one sentence>

### 1. 🔴 Make transfers safe: ownership, CSRF, amount validation, one locked transaction
- src/routes/transfers.js:23: fromId never checked against req.user → anyone can drain any account
- src/routes/transfers.js:21: negative amount reverses the transfer
- ...one line per finding...

**Fix:** <one combined fix>

### 2. 🟡 Add route tests and split out the unrelated changes
- ...

**Scorecard:** Correctness ❌ · Security ❌ · Testing ⚠️ · Readability ⚠️ · Performance ✅ · Conventions ❌ · PR quality ⚠️
```

Grouping never drops or downgrades a finding. Every 🔴 and 🟡 still gets its own line, and most nits are cut. A clean PR gets a verdict and the scorecard line, with no comments.

The skill is read-only. It never edits code, pushes, posts, or approves unless you ask. To post a review, ask it to, and it shows you the draft first.

**How many agents it uses:**

| PR size | Agents |
|---|---|
| Under about 400 changed lines | The main agent, plus 1 fresh verifier subagent that confirms or refutes each finding. The verifier is skipped for tiny PRs. |
| Over about 400 lines | 2–3 area reviewer subagents, plus 1 verifier. |

In Codex, helper agents need multi-agent mode turned on. Without it, the skill does the same passes itself.

## Repo layout

```
skills/pr-review/
  SKILL.md                    workflow, severity rules, report format
  references/checklist.md     deep checklist per area, language pitfalls, AI/LLM section, "not bugs" list
  references/verifier.md      brief for the verifier subagent
  references/area-reviewer.md brief for area reviewers on large PRs
  references/posting.md       posting to GitHub safely (draft first, one review, correct line numbers)
bench/                        the benchmark used to build and compare the skill (see below)
install.sh
```

## How it was tested

The skill was built test-first against other public review approaches. The full results are in `bench/workspace/*/comparison.md`.

**Reviewers compared** (each run on the same isolated git repo with the same prompt):

| Reviewer | What it is |
|---|---|
| `with_skill` | This skill |
| `anthropic_code_review` | Anthropic's official `code-review` plugin command |
| `spillwave` | [SpillwaveSolutions/pr-reviewer-skill](https://github.com/SpillwaveSolutions/pr-reviewer-skill) |
| `without_skill` | Plain Claude asked to review the PR |

**Test cases:**

| Case | Kind | What it tests |
|---|---|---|
| `py-order-search` | Seeded | SQL injection, hardcoded live key, off-by-one, crash paths, missing tests, plus two traps that look wrong but are fine |
| `ts-comments-markdown` | Seeded | Stored XSS, useEffect regression, O(n²) on large threads, an unneeded dependency, weak tests, plus a safe-HTML trap |
| `js-clean-rate-limiter` | Seeded | A correct, well-tested PR. A good review approves with few or no nits. |
| `node-transfer-messy-pr` | Seeded | IDOR, negative amounts, a race without a transaction, missing CSRF, an unclear helper, PR hygiene (title "updates", "wip" commits, unrelated reformat), plus traps |

Each review was graded blind against an answer key by a separate agent, which also checked every extra claim against the code. Labels were shuffled so the grader didn't know which reviewer wrote which review.

To rerun:

```bash
bench/prepare_runs.sh <runs_dir> with_skill without_skill   # build isolated repos
# run each reviewer on each repo (see bench/workspace/*/eval_metadata.json for prompts)
python3 bench/score.py bench/workspace/iteration-N <grading_dir>
```

## Results

### Round 1: all reviewers, 4 cases (skill v1)

| Reviewer | Checks passed | Seeded bugs found | Wrong claims | Correct verdict | Actionability (1–5) | Avg words | Avg tokens |
|---|---|---|---|---|---|---|---|
| **pr-review (v1)** | **100%** | 25/25 | **0** | **4/4** | **5.0** | 924 | 60k |
| Anthropic code-review | 81% | 19/25 | 0 | 3/4 | 3.8 | 408 | 47k |
| Spillwave pr-reviewer | 75% | 25/25 | 1 | 3/4 | 3.2 | 1,816 | 62k |
| Plain Claude | 75% | 25/25 | 1 | 3/4 | 4.2 | 995 | 44k |

- **The clean PR** separated the reviewers most. Spillwave and plain Claude both blocked a correct PR. pr-review approved it with three useful nits.
- **Anthropic's command** is precise but deliberately narrow. On the React case it skipped missing tests, performance, and the unneeded dependency (3 of 7 found).

### Rounds 2–3

| Change | Result |
|---|---|
| v2: large PRs are split across area reviewers up front. Added "blast radius" (code that runs on every page or request) and "silent wrong answers" checks, and an AI/LLM section (OWASP LLM Top 10). | No regressions on the 4 seeded cases (100%, 25/25, 0 wrong claims). |
| v3: a failure a normal user hits in normal use is at least 🟡. Unverifiable claims become ❓ questions. | Still approves the clean PR, with 3 nits and 0 wrong claims. |

### Round 4: two-comment format

| Check | Before (one item per finding) | After (at most 2 grouped comments) |
|---|---|---|
| Seeded bugs still reported (3 multi-bug cases) | 25/25 | 25/25, 0 wrong claims |
| Average length | about 1,090 words | about 730 words (−33%) |

To browse every review side by side, open `bench/workspace/iteration-1/review.html`.

## Known limits

- **Small benchmark:** 4 seeded cases with one run each, so treat the differences as directional, not statistically significant. Plain Claude also caught every seeded bug, so these cases mostly measure precision, verdicts, and report quality, not recall on real-world PRs. `bench/prepare_runs.sh` can also build cases from your own repos (list them in `bench/real_cases.tsv`).
- **CI checks:** can't be tested locally; the skill reads `gh pr checks` on real PRs.
- **Cost:** about 1.2–1.5× the tokens of a plain review, because of the verifier and, on large PRs, the area reviewers.
- **Codex:** the skill is written tool-neutrally and installs into Codex, but it has only been benchmarked on Claude.
