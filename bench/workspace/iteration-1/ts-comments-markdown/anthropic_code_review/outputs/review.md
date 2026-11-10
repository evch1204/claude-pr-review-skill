## Code review

**Markdown in comments + participant count** (`feat/markdown-comments` → `main`, head `a25962d`)

Found 2 issues:

1. **Stored XSS in comment bodies.** `CommentList` puts `renderMarkdown(c.body)` straight into `dangerouslySetInnerHTML` without calling `sanitize()`. `renderMarkdown` doesn't escape HTML. It only runs regex replacements, so any raw HTML in a comment reaches the DOM unchanged. A comment like `<img src=x onerror=alert(document.cookie)>` runs script for everyone who views the thread. So does a link like `[click](javascript:alert(1))`, or a URL with a `"` in it that breaks out of the `href` attribute. `Bio.tsx` in this same PR does it correctly with `sanitize(renderMarkdown(text))`, and `src/sanitize.ts` says it must be used "before it is ever passed to dangerouslySetInnerHTML". (bug / security)

   `src/components/CommentList.tsx` L18-L20

   Fix: `<div dangerouslySetInnerHTML={{ __html: sanitize(renderMarkdown(c.body)) }} />` and import `sanitize` from `"../sanitize"`.

2. **The comment list no longer reloads when `postId` changes.** The effect's dependency array went from `[postId]` to `[]`, so comments are fetched only on first mount. When the same `CommentList` instance gets a new `postId` (for example, moving from one post to the next), it keeps showing the previous post's comments. The `cancelled` guard was also removed, so a slow response can still call `setComments` after unmount. The repo's ESLint config only enables `react-hooks/rules-of-hooks`, not `exhaustive-deps`, so lint won't catch this. This is a regression from the code on `main`. (bug)

   `src/components/CommentList.tsx` L10-L12

   Fix: restore the previous effect, which uses `[postId]` as its dependency and keeps the `cancelled` flag in its cleanup.
