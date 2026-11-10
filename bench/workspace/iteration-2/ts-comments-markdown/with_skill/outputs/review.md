## PR Review: Markdown in comments + participant count

**Verdict: ❌ Request changes**: comment bodies are rendered as raw HTML without sanitizing (stored XSS), and the comment-fetch effect lost its `postId` dependency and cancellation, so it can show the wrong post's comments.

The PR adds a small regex markdown renderer (`src/markdown.ts`), uses it for comment bodies and a new `Bio` component, and adds a `Participants` component that counts unique authors and shows when the last reply was posted.

### 🔴 Blocking
1. **Stored XSS: comment HTML is not sanitized**: `src/components/CommentList.tsx:19`
   `renderMarkdown` doesn't escape its input, and `CommentList` puts its output straight into `dangerouslySetInnerHTML`. `Bio.tsx` wraps the same call in `sanitize()`, and `src/sanitize.ts` says it exists for exactly this ("Sanitize untrusted HTML before it is ever passed to dangerouslySetInnerHTML"). The comment path skips it.
   **Breaks when:** someone posts the comment `<img src=x onerror=alert(document.cookie)>`. It passes through unchanged, and the script runs in the browser of everyone who opens the thread. `[x](javascript:alert(1))` and `[x](" onmouseover="alert(1))` also produce a live `javascript:` link and an injected event attribute (I ran the renderer on both to check).
   **Fix:** use the existing helper here, the same way `Bio` does:
   ```tsx
   <div dangerouslySetInnerHTML={{ __html: sanitize(renderMarkdown(c.body)) }} />
   ```
   Better still, HTML-escape `src` at the start of `renderMarkdown` (before any replacements) so the renderer is safe no matter who calls it. Keep `sanitize()` as well, because DOMPurify is what removes `javascript:` hrefs.

2. **Fetch effect regressed: stale and mismatched comments**: `src/components/CommentList.tsx:11-12`
   The old effect re-ran on `[postId]` and ignored stale responses through a `cancelled` flag. The new one is `fetchComments(postId).then(setComments)` with `[]`. Nothing in the PR description explains this change, and it isn't needed for markdown.
   **Breaks when:** the same `CommentList` instance gets a new `postId` (for example, client-side navigation from post A to post B). It never refetches, so post B shows post A's comments. If it is remounted quickly or unmounts mid-request, the response still calls `setComments` on a stale or unmounted component. The lint config only enables `rules-of-hooks`, not `exhaustive-deps`, so `npm run lint` won't catch this.
   **Fix:** restore the original effect body and `[postId]` dependency array from `main`.

### 🟡 Should fix
3. **The participants line is never shown**: `src/components/Participants.tsx`, `src/components/CommentList.tsx`
   The description and commit a25962d ("Show participant count above comment thread") both say a participants line appears above the thread, but nothing renders `<Participants>`. It also can't be added from outside as things stand: `CommentList` keeps `comments` in local state, so no parent has the list to pass in.
   **Breaks when:** this merges and someone opens a thread. No participants line appears.
   **Fix:** render `<Participants comments={comments} />` at the top of `CommentList`, or move the fetched comments up into a parent that renders both. If the wiring is meant to land in a separate PR, say so in the description.

4. **O(n²) participant count on large threads**: `src/components/Participants.tsx:6-8`
   `filter` + `findIndex` scans the array for every comment. That's O(n·k) for k distinct authors, which approaches O(n²) when most commenters are different people. The PR description says threads "can have several thousand comments".
   **Breaks when:** a thread has 5,000 comments from mostly distinct authors. That's on the order of 12.5M comparisons on every render of this component.
   **Fix:** `const count = new Set(comments.map((c) => c.author.id)).size;` (the component only uses `.length`).

5. **New `moment` dependency duplicates `date-fns`**: `package.json`, `src/components/Participants.tsx:1,13`
   The repo already formats relative times with `relativeTime()` in `src/format.ts` (date-fns). `moment` is in maintenance mode and adds a large chunk to the bundle for one `fromNow()` call. The two libraries also word the output slightly differently, so the thread header and the comment rows would disagree.
   **Fix:** drop `moment` and use `relativeTime(last.createdAt)`.

6. **Markdown is applied inside code spans**: `src/markdown.ts:7-9`
   The italic replacement runs before the code-span replacement, so asterisks inside backticks get rewritten.
   **Breaks when:** a comment contains `` `2*3*4` ``. It renders as `<code>2<em>3</em>4</code>` instead of the literal `2*3*4`. Commenters sharing code or math will hit this regularly.
   **Fix:** extract code spans first (swap them for placeholders, or split on backticks) and only apply the other rules outside them.

7. **Tests cover only the happy path**: `src/__tests__/markdown.test.ts`
   One test checks `**hi**`. Nothing covers italic, code, links, or newlines, and nothing covers hostile input. A test asserting that `<script>` / `<img onerror>` comes out escaped or stripped would have caught #1. `Participants` and the `CommentList` changes have no tests.
   **Fix:** add cases for each syntax, an escaping test, the code-span case from #6, and a `Participants` test with duplicate authors.

### ⚪ Nits
- `src/components/CommentList.tsx:16-17`: the list key changed from `c.id` to the array index for no stated reason. The rows have no state, so nothing renders wrong today, but React redoes the DOM and innerHTML for every row after an inserted comment. Go back to `key={c.id}`.

### ❓ Questions
- `Participants` treats `comments[comments.length - 1]` as the latest reply. Does the API guarantee oldest-first order?

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | Effect lost `postId` dep/cancel; participants not rendered |
| Security | ❌ | Unsanitized comment HTML → stored XSS |
| Testing | ⚠️ | One happy-path test; no escaping test |
| Readability | ✅ | |
| Performance | ⚠️ | O(n²) unique-author count on large threads |
| Conventions | ⚠️ | `moment` duplicates existing date-fns helper |
| PR quality | ⚠️ | Unmentioned effect/key changes; participants line not wired |

**Checked:** not run. There's no `node_modules` or lockfile in the repo, and installing packages was out of scope, so `npm test` / `lint` / `typecheck` weren't run. I ran `renderMarkdown` on its own in Node to confirm the XSS and code-span outputs above. · **Not reviewed:** nothing skipped (6 files, about 47 changed lines).
**Good:** `Bio` correctly runs `sanitize(renderMarkdown(...))` through the repo's existing DOMPurify helper. That's the pattern the comment path should follow.
