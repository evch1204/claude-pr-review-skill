# Verifier brief

Use this when handing candidate findings to a fresh subagent (SKILL.md, Step 4). Fill in the placeholders. Pass the findings themselves, but not the reasoning that produced them. The point is a second opinion that isn't anchored on yours.

```
You are verifying candidate code-review findings for a change in the repository at <repo path>.
See the change with: <diff command, e.g. `git diff main...HEAD` or `gh pr diff 123`>.
The change is meant to: <one-sentence intent>.
Repo rules that apply: <quoted rules from CLAUDE.md/CONTRIBUTING/etc., or "none found">.

For each finding below, open the cited code (the full file, plus callers if relevant) and decide:
- CONFIRMED: the problem is real, introduced or touched by this change, and you can state a concrete
  scenario (input/state → wrong result). Give the file:line evidence.
- REFUTED: the code doesn't say that, it's handled elsewhere (cite where), it's pre-existing and untouched,
  or the scenario can't happen. Say why in one sentence.
- UNCERTAIN: you can't tell without information you don't have. Say what's missing.

Also say if the severity looks wrong: blocking means a realistic bug, crash, data loss, security hole, or broken
safety rule; otherwise it's should-fix or nit.

Do not add new findings unless you trip over a clearly blocking problem while checking. List those separately.
Do not modify any files.

Findings:
1. [severity] path:line — <claim> — Breaks when: <scenario>
2. ...

Reply as a numbered list matching the findings: VERDICT — evidence — (severity change, if any).
```
