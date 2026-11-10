## Code review

**PR:** Add TokenBucket rate limiter (`feat/token-bucket` -> `main`, 2 commits: a4c6089, 2d8c0ed)

No issues found. Checked for bugs and CLAUDE.md compliance.

---

**Scope checked**
- `src/token-bucket.js` (new): constructor validation, continuous refill capped at `capacity`, all-or-nothing `tryRemove(n)`, and the backwards-clock guard (keeps the high-water mark, so a later forward jump can't grant unearned tokens).
- `src/index.js`: new `TokenBucket` export resolves to the new module.
- `test/token-bucket.test.js`: 5 new cases; `node --test test/` passes locally (8/8, including the 3 existing retry tests).
- `README.md`: API notes match the implementation.
- CLAUDE.md: none in the repository, so there were no compliance rules to check.

**Process notes**
- I adapted the procedure to a local branch: I skipped the eligibility check and posted nothing (no `--comment`).
- The parallel reviewer subagents couldn't start because the session's concurrent-subagent limit was reached. I did the bug and logic pass myself on the full diff instead.
