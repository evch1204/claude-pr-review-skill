/**
 * Minimal markdown -> HTML for comment bodies.
 * Supports **bold**, *italic*, `code` and [links](url).
 */
export function renderMarkdown(src: string): string {
  return src
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>")
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" rel="noopener">$1</a>')
    .replace(/\n/g, "<br/>");
}
