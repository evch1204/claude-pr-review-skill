# Posting a review to GitHub

Only post when the user asks. Posting is public and notifies people.

## 1. Draft first

1. Show the user exactly what will be posted.
2. Confirm the review event: `COMMENT`, `REQUEST_CHANGES`, or `APPROVE`. Never use `APPROVE` unless the user said to approve.
3. In the posted version, drop the scorecard and anything aimed at the user rather than the author (such as "Not reviewed: …") unless they want it kept.

Write for the author:
- Describe the code, not the person. Write "this query is built from…", not "you built…".
- Explain why each point matters.
- Use Conventional Comments prefixes if the team uses them: `issue (blocking):`, `suggestion:`, `nitpick (non-blocking):`, `question:`, `praise:`.
- Don't tag people (`@name`) unless the user asks.

## 2. Summary-only review

Use one call, so the summary and the verdict land together:

```bash
gh pr review <n> --comment --body-file review.md          # or --request-changes / --approve
```

## 3. Review with inline comments

Post at most two inline comments, the same two from the report.
- Anchor each one on its most important line.
- List the other affected `path:line` locations in that comment's body. Don't open a separate comment per location, because a pile of comments reads like a pile of chores.
- Use the reviews API, so the summary and both comments post as one review:

```bash
HEAD_SHA=$(gh pr view <n> --json headRefOid -q .headRefOid)
gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input review.json
```

`review.json`:

```json
{
  "commit_id": "<HEAD_SHA>",
  "event": "REQUEST_CHANGES",
  "body": "Summary + verdict here",
  "comments": [
    { "path": "app/orders.py", "line": 14, "side": "RIGHT", "body": "issue (blocking): ..." },
    { "path": "app/orders.py", "start_line": 20, "line": 23, "side": "RIGHT", "body": "..." }
  ]
}
```

Getting the fields right:
- **`line`** is the line number in the file at the head commit, not a position in the diff. The line must be inside a diff hunk, or GitHub returns 422.
- **`commit_id`**: use `headRefOid`. Don't take the last item of a paginated commits list.
- **Suggestions:** a `suggestion` block inside the body creates a one-click fix:

  ````
  ```suggestion
  replacement lines
  ```
  ````

  Only use one when the replacement fully fixes the issue. For larger fixes (more than about 6 lines), describe the change instead.
- **Escaping:** write the JSON with a file-writing tool rather than shell `echo`, to avoid quoting bugs.

## 4. After posting

Give the user the review URL. That's the `html_url` in the API response, or `gh pr view <n> --web`.
