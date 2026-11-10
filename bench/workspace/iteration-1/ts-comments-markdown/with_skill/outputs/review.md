## PR Review: Markdown in comments + participant count

**Verdict: ❌ Request changes.** Comment bodies now go into `dangerouslySetInnerHTML` without being sanitized, so any commenter can run script in every reader's browser. The comment fetch effect also quietly lost its `postId` dependency.

The PR adds a small regex-based `renderMarkdown()` that is used for comments and bios, plus a `Participants` component that counts distinct commenters and shows the time of the last reply.

### 🔴 Blocking

1. **Stored XSS in comments**: `src/components/CommentList.tsx:19`
   `renderMarkdown()` does no HTML escaping, and its output goes straight into `dangerouslySetInnerHTML`. `sanitize()` is skipped here, even though `Bio.tsx:6` in this same PR uses it, and `src/sanitize.ts:3` says sanitizing must happen "before it is ever passed to dangerouslySetInnerHTML".
   **Breaks when:** someone posts a comment whose body is `<img src=x onerror=alert(1)>`. It renders unchanged (I ran the renderer on it) and the script runs for everyone who opens the thread. The link syntax opens two more holes. `[x](javascript:alert(1))` produces a `javascript:` href. `[x](" onmouseover="…)` breaks out of the `href` attribute.
   **Fix:** sanitize the comment output the same way `Bio` does:
   ```tsx
   <div dangerouslySetInnerHTML={{ __html: sanitize(renderMarkdown(c.body)) }} />
   ```
   It would be better still to HTML-escape `src` at the top of `renderMarkdown()` before applying the markdown regexes, so the renderer can't produce unsafe output for any caller (see 3).

2. **Effect dropped `postId` dependency and cancellation**: `src/components/CommentList.tsx:10-12`
   `main` had `[postId]` and a `cancelled` flag. This PR changes it to `fetchComments(postId).then(setComments)` with `[]`. The change has nothing to do with markdown and the PR doesn't mention it. The lint config only enables `rules-of-hooks`, so lint won't catch it.
   **Breaks when:** a parent keeps `<CommentList>` mounted and changes `postId`, for example in-app navigation between posts. No new fetch happens, and the previous post's comments stay on screen under the new post.
   **Fix:** revert this block to the `main` version, with the `cancelled` flag and `[postId]`. If you only restore the dependency without the flag, an out-of-order response race comes back.

### 🟡 Should fix

3. **Renderer mangles code spans and swallows literal HTML**: `src/markdown.ts:7-9`
   Italic is applied before code, so markdown is processed inside backticks. There's also no escaping. Before this PR, `<p>{c.body}</p>` showed angle-bracket text as typed.
   **Breaks when:** a comment says `` `ls *.ts` and `rm *.js` ``. It renders as `<code>ls <em>.ts</code> and <code>rm </em>.js</code>`, which is mis-nested and wrong. A comment like "use the `<b>` tag" or "wrap it in <div>" now loses that text, because it's parsed as HTML.
   **Fix:** escape `& < > " '` first. Then pull code spans out into placeholders before running bold, italic and link, and put them back at the end. Alternatively, use a small maintained markdown library plus the existing `sanitize()`.

4. **The participants line isn't rendered anywhere**: `src/components/Participants.tsx`
   Nothing imports `Participants`. `CommentList` owns the `comments` state but doesn't render it, so the "participants line above the thread" from the description never shows up.
   **Fix:** render `<Participants comments={comments} />` above the `<ul>` in `CommentList`.

5. **O(n²) dedupe on threads of several thousand comments**: `src/components/Participants.tsx:6-8`
   `filter` combined with `findIndex` scans the whole array once per comment.
   **Breaks when:** a popular thread has about 5,000 comments from mostly different authors. That costs roughly 100–200 ms of work on every render of this component (I measured it with node).
   **Fix:** `const count = new Set(comments.map((c) => c.author.id)).size;` and wrap it in `useMemo` if the parent re-renders often.

6. **New `moment` dependency duplicates `date-fns`**: `package.json`, `src/components/Participants.tsx:1,13`
   `date-fns` is already a dependency, and `src/format.ts` already exports `relativeTime()`. `moment` is in maintenance mode and adds a large chunk to the bundle. It also words times differently: the participants line would say "3 hours ago" while each comment says "about 3 hours ago".
   **Fix:** use `relativeTime(last.createdAt)` and drop `moment` from `package.json`.

7. **Tests cover only the happy path for bold**: `src/__tests__/markdown.test.ts`
   The renderer is security-sensitive, but no test covers italic, code, links, nesting, HTML escaping or `javascript:` links. None of the bugs in 1 or 3 would make the current test fail.
   **Fix:** add cases for `<img onerror>`, `[x](javascript:…)`, `` `a*b*c` ``, and literal `<tag>` text, plus a quick test for `Participants` (distinct count, empty list).

### ⚪ Nits
- `src/components/CommentList.tsx:16-17`: `key={c.id}` was changed to `key={i}` with no stated reason. Revert it along with item 2. Stable ids are already available.
- `src/components/Participants.tsx:12`: one commenter reads "1 people joined the discussion". Handle the singular.
- `src/markdown.ts:2`: the doc comment says "for comment bodies", but bios use it too. Also state that the output is unsafe until it goes through `sanitize()`.

### ❓ Questions
- `src/components/Participants.tsx:9`: "last reply" takes the last element of the array. Does the comments API guarantee oldest-first order? If not, take the max `createdAt` instead.

### Scorecard
| Area | | Note |
|---|---|---|
| Correctness | ❌ | Effect lost `postId` dep; code spans mangled |
| Security | ❌ | Unsanitized markdown HTML in comments (stored XSS) |
| Testing | ⚠️ | One bold-only test; no hostile-input cases |
| Readability | ✅ | |
| Performance | ⚠️ | O(n²) participant dedupe at thousands of comments |
| Conventions | ⚠️ | `moment` duplicates `date-fns`/`relativeTime` |
| PR quality | ⚠️ | Unrelated, unmentioned effect/key changes; feature not wired up |

**Checked:** I could not run the tests, lint or typecheck because `node_modules` isn't installed and installing was out of scope. I did run the PR's `renderMarkdown` regexes and the participant dedupe in node against hostile and large inputs, and the results above come from those runs. Each finding was also checked separately by a second reviewer. There's no CI, since this is a local branch with no remote.
**Good:** `Bio` correctly runs the markdown output through the existing `sanitize()` helper, and the comment path needs the same treatment.
