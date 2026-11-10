# Review: Markdown in comments + participant count (`feat/markdown-comments` → `main`)

**Verdict: don't merge yet.** There's a stored XSS in comments, and a regression in `CommentList` that shows the wrong post's comments. Both need fixing first. The participant line also has a performance problem at the thread sizes in the description, and it isn't rendered anywhere yet.

I read the full diff and ran `renderMarkdown` against some hostile inputs in Node. I couldn't run jest, tsc or eslint because `node_modules` isn't installed and I wasn't allowed to install packages.

---

## Blocking

### 1. Stored XSS: comment HTML is never sanitized
`src/components/CommentList.tsx`
```tsx
<div dangerouslySetInnerHTML={{ __html: renderMarkdown(c.body) }} />
```
`renderMarkdown` doesn't escape anything, so whatever HTML a commenter writes reaches the DOM unchanged. `Bio.tsx` correctly wraps it in `sanitize(...)`, but `CommentList` doesn't. Comments are user-written just like bios, and many more people see them. Here is what the renderer actually outputs:

| Input | Output |
|---|---|
| `<img src=x onerror=alert(1)>` | `<img src=x onerror=alert(1)>` (runs for every viewer of the thread) |
| `[x](" onmouseover="alert(1))` | `<a href="" onmouseover="alert(1" …>` (breaks out of the attribute) |
| `[x](javascript:alert(1))` | `<a href="javascript:alert(1" …>` |

**Fix:** in `CommentList`, use `sanitize(renderMarkdown(c.body))`. A better fix is to make `renderMarkdown` safe on its own, so the next caller can't forget:
- HTML-escape `& < > " '` in the source **before** applying the markdown regexes.
- Allow only `http:`, `https:` and `mailto:` in link hrefs.
- Still run the output through DOMPurify, either inside `renderMarkdown` or through one shared `<Markdown>` component that both `Bio` and `CommentList` use.

### 2. `CommentList` effect regression: stale comments, and a race when switching posts
```tsx
useEffect(() => {
  fetchComments(postId).then(setComments);
}, []);
```
On `main`, the effect depended on `[postId]` and had a `cancelled` guard. This PR removes both, and nothing in the PR needs that change:
- With `[]`, changing `postId` (for example, going from one post to the next in an SPA) **never refetches**. The new post shows the old post's comments.
- Without the cancellation guard, a slow response for an earlier post can overwrite a newer one, or call `setState` after unmount.

Lint won't catch this, because `.eslintrc.json` only enables `rules-of-hooks` and not `exhaustive-deps`. Please restore the original effect. Consider turning on `react-hooks/exhaustive-deps` too.

---

## Should fix

### 3. `key={i}` replaces `key={c.id}`
This is also an unrelated regression. Comments have stable ids. Index keys make React reuse the wrong `<li>` when comments are inserted, deleted or reordered, for example when a new comment is prepended or one is removed by moderation. Put back `key={c.id}`.

### 4. `Participants` is O(n²), and the description says threads reach several thousand comments
```ts
comments.filter((c, i) => comments.findIndex((x) => x.author.id === c.author.id) === i)
```
At 5,000 comments that's up to about 12.5M comparisons, and it runs on every render. Use a Set:
```ts
const count = new Set(comments.map((c) => c.author.id)).size;
```
`useMemo` on `comments` would also help, since the count only changes when the comments do.

### 5. `Participants` isn't rendered anywhere
Nothing imports it (`git grep Participants` only finds its own file). So the "participants line above the thread" isn't actually there. It also needs the `comments` array, which currently lives in `CommentList`'s local state. Either render `<Participants comments={comments} />` inside `CommentList`, or move the fetch up a level.

### 6. New `moment` dependency, even though `date-fns` already covers this
`src/format.ts` already exports `relativeTime()` using `date-fns`'s `formatDistanceToNow`, and `CommentList` uses it. `moment` is in maintenance mode, isn't tree-shakeable, and adds roughly 70 KB min+gz to a widget bundle just for `fromNow()`. Use `relativeTime(last.createdAt)` and drop `moment` from `package.json`. That also keeps the wording the same as the timestamps on each comment.

---

## Minor / nits

- **Markdown inside code spans.** Bold and italic run before code, so `` `a*b*c` `` renders as `<code>a<em>b</em>c</code>`. HTML in code is also inserted raw: `` `<div>` `` produces a real `<div>`. Handle code spans first and escape their contents. Escaping as in #1 fixes the second part.
- **Links with `)` in the URL get cut short** (e.g. Wikipedia URLs), and the leftover `)` shows up as text. It's acceptable for "basic" markdown, but worth knowing.
- **Link `rel`.** These are user-submitted links, so `rel="nofollow ugc noopener"` is the usual choice. `noopener` alone does nothing without `target="_blank"`.
- **"last reply" assumes the API returns comments oldest-first.** If it doesn't, the time shown will be wrong. Taking the max `createdAt` is safer.
- **"1 people joined the discussion".** Add a singular form.
- **The test barely covers anything.** It only checks bold. Given #1, the most important tests are the security ones: raw HTML is escaped, `javascript:` hrefs are rejected, and quotes in hrefs can't break out of the attribute. Add italic, code, link, nested and code-span cases too. Nothing tests `Participants` or the `CommentList` change, and a test that rerenders with a new `postId` would have caught #2.

---

## Summary of requested changes
1. Sanitize comment HTML, and make `renderMarkdown` escape input and allow-list link protocols.
2. Restore the `[postId]` dependency and the cancellation guard in `CommentList`.
3. Restore `key={c.id}`.
4. Count participants with a `Set`, and actually render `<Participants>`.
5. Replace `moment` with the existing `relativeTime` helper and remove the dependency.
6. Add XSS and edge-case tests for the renderer.
