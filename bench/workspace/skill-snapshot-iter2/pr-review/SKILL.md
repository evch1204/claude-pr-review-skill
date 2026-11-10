---
name: pr-review
description: Review a pull request, branch, or set of code changes the way a careful senior engineer would — correctness bugs, security (OWASP), tests, readability, performance, repo conventions, and PR hygiene — with every finding verified against the code and a clear merge verdict. Use this whenever the user asks to review a PR / pull request / merge request / branch / diff / commit range / "my changes", pastes a GitHub PR number or URL, or asks things like "is this ready to merge?", "can you look over my PR", "check this before I open a PR", even if they never say the word "review". Works with GitHub PRs (via the gh CLI) and with local branches or uncommitted changes.
---

# PR Review

Your job is to give the author the review a strong senior engineer would: find the problems that matter, prove each one, leave out noise, and end with a clear verdict. The bar comes from Google's code review standard: approve once the change improves the overall health of the code, even if it isn't perfect. Block only on real problems.

Two failure modes ruin a review, and you're steering between them:
- **Missing a real bug.** This usually happens when you only skim the diff hunks and never look at callers, removed lines, or the repo's rules.
- **Burying the author in noise.** False positives, speculative "might be an issue", and long lists of nits teach people to ignore reviews. A short review with three proven findings beats a long one with fifteen maybes.

## Ground rules

- **Read-only.** Don't edit files, commit, push, post comments, or approve unless the user asks. If they want the review posted, show the draft first (see `references/posting.md`).
- **Review the change, not the whole codebase.** Problems in untouched code are out of scope. The exception is when the PR newly depends on them or makes them worse; mention those briefly as FYI.
- **The repo's own rules beat generic best practice.** If CLAUDE.md, AGENTS.md, CONTRIBUTING, the README, or the linter config decides something, follow it and quote it. Don't impose outside preferences the repo hasn't adopted.
- **Every finding needs a concrete failure scenario:** "when X, Y happens". If you can't write one, it's a question or nothing.

## Step 1: Find the change and its context

Work out what's being reviewed:

| User gives | Collect with |
|---|---|
| PR number or URL | `gh pr view <n> --json number,title,body,author,baseRefName,headRefName,headRefOid,isDraft,additions,deletions,files,commits,reviews,comments` · `gh pr diff <n>` · `gh pr checks <n>` |
| A branch, or "my branch" | Base = the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`, else `main`/`master`). Then `git diff <base>...HEAD`, `git log --format='%h %s%n%b' <base>..HEAD` |
| "My changes" with nothing committed | `git diff HEAD` plus untracked files from `git status --short` |
| A commit or range | `git show <sha>` / `git diff <a>..<b>` |

Reading PR files without disturbing the user's working tree:
- If the PR branch isn't checked out, run `git fetch origin pull/<n>/head:pr-<n>` and read with `git show pr-<n>:<path>`.
- Don't switch branches or stash on the user's behalf.

If there's no PR description (local branch), ask yourself whether the commit messages explain the change. If the user mentioned what the change is for, that's the intent.

Then gather what you'll judge against:
1. **Intent.** Use the PR title, description, linked issues (`gh issue view <n>` for `#123` references), and commit messages.
2. **Repo rules.** Read CLAUDE.md and AGENTS.md (the root one and any in changed directories), CONTRIBUTING*, the PR template, convention sections of the README, and linter/formatter configs. Note the rules relevant to this diff.
3. **Size.** Count changed lines, excluding lockfiles, generated, vendored, and snapshot files. Over about 400 lines, plan to split the review (start of Step 3). One reviewer reading 1,000 lines gives the last files much less attention than the first, and bugs hide in the files read last.

## Step 2: Understand before judging

Before looking for problems, write one or two sentences for yourself about what the change is trying to do and how. If you can't, the PR's description and structure are a finding in themselves. Ask about intent instead of guessing it.

Then read with real context, because most serious bugs live at the boundaries the diff doesn't show:
- **Read each changed file in full**, not just the hunks.
- **Look at the removed lines.** A deleted guard, dependency, `await`, or validation is a common source of regressions. Compare old behavior to new for each hunk.
- **Find the callers** of every changed function or signature (grep for the name), and check that their assumptions still hold.
- **Check what the code promises against what it does.** Look at docstrings, comments, README, API docs, and the PR description. A mismatch is often the bug.
- **Look for existing helpers** that the new code duplicates or should have used. A sibling file often shows the house pattern, such as an ownership check, a sanitizer, or a transaction helper.

## Step 3: Review across the seven areas

**Large PRs (over about 400 changed lines): split first.** If you can start subagents (for example Claude Code's Agent tool or Codex multi-agent mode):
- Group the changed files into 2–3 areas that each make sense alone, such as backend tools, API and wiring, and frontend. Keep tests with the code they test.
- Start one reviewer subagent per area, all at once, using the brief in `references/area-reviewer.md`.
- While they work, review the cross-cutting parts yourself: how the areas connect (API contracts, data passed between frontend and backend, config and hooks) and the PR as a whole.

Without subagents, review area by area yourself and give each area its own full pass. Either way, every area, including the frontend and config, gets real attention. Don't leave it to whatever's left at the end.

Go through these in order of impact. Spend most of your effort on 1 and 2. For deeper prompts per area, plus language-specific pitfalls and a list of things that are *not* bugs, read `references/checklist.md`. It's worth reading on any PR touching security, concurrency, or an unfamiliar language.

1. **Correctness.** Does it do what the intent says? Check:
   - edge cases: empty/null/None, zero and negative, boundaries and off-by-one, duplicates, huge inputs, Unicode, time zones;
   - error paths: swallowed exceptions, missing awaits, wrong status codes, partial failure;
   - concurrency: check-then-act, multi-step writes without a transaction or lock, shared mutable state, async races and stale results;
   - regressions against the base version;
   - **blast radius:** code that runs everywhere can break features the PR never touches. That includes page- or document-level event handlers, middleware, app-wide hooks, startup code, global CSS, and monkey-patches. Ask what it does to everything else;
   - **silent wrong answers:** invalid input that produces an empty or default result instead of an error, when someone downstream (a person, a UI, or an AI model) will take "nothing found" as the truth.
2. **Security.** Trace untrusted input from where it enters to where it's used. Look for:
   - injection (SQL, shell, template, path);
   - XSS through raw-HTML sinks;
   - missing authorization on object access (IDOR);
   - authentication and session problems, including CSRF on cookie-authenticated state changes;
   - secrets in code or logs, crypto misuse, SSRF, unsafe deserialization;
   - new dependencies: are they needed, already covered by an existing dependency, and maintained?
   - for features built on an AI model: prompt injection through data the model reads, model output rendered as HTML or markdown, tools with more power than needed, and model-supplied tool arguments. See the AI section of the checklist.
3. **Testing.** Is the new behavior tested? Would those tests fail if the code broke? Are the error and edge cases covered? If the repo has a cheap, local, existing test, lint, or typecheck command, run it; installing packages or hitting the network needs the user's OK. Report what you ran and the result, and include CI status for GitHub PRs.
4. **Readability and maintainability.** Look for:
   - names that don't say what things are;
   - functions doing several jobs, and boolean flag parameters;
   - duplicated logic;
   - comments that explain *what* instead of *why*;
   - dead code;
   - over-engineering for hypothetical futures.
5. **Performance.** Look for work that's too slow at the sizes this code will really see: O(n²) on large collections, N+1 queries, work repeated per render or loop, unbounded memory or caches, missing pagination. Use stated or realistic scale; don't micro-optimize.
6. **Style and conventions.** Check consistency with the repo's documented rules and the surrounding code. Skip anything a formatter or linter enforces in CI.
7. **PR quality.** Is the PR one focused change, with no unrelated refactors or reformatting? Is it a reasonable size? Does the title and description explain what, why, and how it was tested? Are the commit messages meaningful? Were docs, migrations, and changelog updated when behavior changed? Are breaking changes called out?

## Step 4: Verify every finding

This is where review quality is won. Whoever drafts a finding is biased toward keeping it, so check each candidate deliberately:

1. **Re-open the exact lines** in the PR's version and confirm the code says what you think.
2. **Write the failure scenario:** the concrete input or state, then the wrong result. If you can't, drop it or turn it into a question.
3. **Look for handling elsewhere**, such as caller validation, middleware, a framework guarantee, a DB constraint, or a type system. Many "missing checks" exist one layer up.
4. **Confirm the PR introduced or touched it.** Pre-existing problems are out of scope, except as a brief FYI.
5. **Assign severity** using the scale below.

**Use a fresh verifier when you can.** If your environment lets you start a subagent (for example, Claude Code's Agent tool or Codex multi-agent mode), give one fresh agent the candidate list along with the repo path and the diff command. Leave out your reasoning so it isn't anchored by it. Ask it to confirm or refute each finding with file:line evidence, using the brief in `references/verifier.md`. Drop what it refutes, and look again at anything it marks uncertain.

If you can't start a subagent, do a separate second pass yourself where you argue that each finding is wrong.

For a quick review, or a PR under about 50 changed lines with no findings above nit, skip the verifier.

**Large PRs:** merge the area reviewers' findings with your own, and de-duplicate them. When the same file:line has the same issue, keep it once at the higher severity. Then verify the merged list as above. In the report, say that the PR is large and suggest how it could have been split.

### Severity

- **🔴 Blocking:** must fix before merge. Use this for incorrect behavior on realistic input, crashes, data loss or corruption, a security vulnerability, or breaking a documented repo rule that exists for safety (auth, money, data integrity).
- **🟡 Should fix:** a real problem with lower impact or likelihood. Examples: missing tests for new logic, error handling gaps, a performance problem at realistic scale, maintainability problems likely to cause bugs, or PR hygiene the repo requires. The author should fix it or push back with a reason.
- **⚪ Nit:** optional polish. Keep at most 3, the most useful ones, and drop the rest.
- **❓ Question:** use this when you genuinely can't tell the intent. Ask it as a question, not an accusation.

### Verdict

- **❌ Request changes:** any 🔴, or 🟡 items significant enough to need another look.
- **✅ Approve with comments:** no 🔴, and any 🟡 items are small enough for the author to fix without re-review.
- **✅ Approve:** nothing above nit.

## Step 5: Write the report

Keep it skimmable. The author should know within ten seconds whether they can merge and what to fix first. Leave out empty sections, and don't narrate the diff back to them.

```markdown
## PR Review: <PR title or branch name>

**Verdict: ❌ Request changes**: <one sentence on the main reason>

<1–2 sentences on what the PR does, which shows you understood it>

### 🔴 Blocking
1. **<Short title>**: `path/to/file.py:42`
   <What's wrong, 1–2 sentences.>
   **Breaks when:** <concrete input/state → wrong result>
   **Fix:** <specific change; include a short snippet only if it fixes it fully>

### 🟡 Should fix
1. ...same shape...

### ⚪ Nits
- `path:line`: <one line>

### ❓ Questions
- <question>

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | <≤10 words> |
| Security | ✅ | |
| Testing | ⚠️ | |
| Readability | ✅ | |
| Performance | ✅ | |
| Conventions | ✅ | |
| PR quality | ⚠️ | |

**Checked:** <tests/lint you ran and results, CI status, or "not run: why"> · **Not reviewed:** <generated/lock files you skipped, if any>
**Good:** <one specific thing done well, if there is one; skip generic praise>
```

Scorecard symbols:
- ✅ means no issues;
- ⚠️ means only 🟡 or nits;
- ❌ means at least one 🔴;
- "n/a" means the area doesn't apply.

Number the findings so the author can reply "fixed 1, pushing back on 3". For a clean PR the whole report is the verdict, summary, scorecard, and "Good" line, and that's a successful review, not a lazy one.

If the user asked for a quick look, report only 🔴 and 🟡 findings and skip the scorecard.

## Step 6: Post to GitHub (only when asked)

Read `references/posting.md`. In short:
1. Show the draft and confirm.
2. Post one review with `gh pr review` (or the reviews API for inline comments), using the head commit SHA and real file line numbers.
3. Never approve on the user's behalf unless they explicitly say so.
