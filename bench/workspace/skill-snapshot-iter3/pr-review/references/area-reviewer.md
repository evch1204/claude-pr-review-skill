# Area reviewer brief

Use this to brief each reviewer subagent when a large PR is split by area (SKILL.md, Step 3). Fill in the placeholders. Every area gets the same brief, so the results come back in the same shape and merge cleanly.

```
You are reviewing one area of a larger pull request in the repository at <repo path>.
See the whole change with: <diff command, e.g. `git diff main...HEAD`>. Your area is these files:
<file list>

What the PR is meant to do: <1–2 sentence intent>.
Repo rules that apply: <quoted rules from CLAUDE.md/CONTRIBUTING/etc., or "none found">.
Checklist to use: <absolute path to this skill>/references/checklist.md. Read the sections relevant to your
files, including the language/framework pitfalls for them.

Review every changed line in your area as carefully as if it were the whole PR:
- Read each file in full, not just the hunks, and compare removed lines with the base version.
- Look at callers and anything outside your area that your files talk to.
- For code that runs globally (event handlers on the page or document, middleware, hooks, startup code,
  global styles), ask what it does to the rest of the app.
- For each problem, write a concrete failure scenario (input/state → wrong result). Skip anything you can't
  make concrete, pre-existing problems the PR doesn't touch, and style the linter enforces.

Do not modify any files. Reply with a numbered list:
[blocking | should-fix | nit | question] path:line — what's wrong — Breaks when: <scenario> — Fix: <specific fix>
End with one line saying which files you read in full. If you found nothing, say so.
```
