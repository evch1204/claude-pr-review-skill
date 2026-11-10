import { renderMarkdown } from "../markdown";
import { sanitize } from "../sanitize";

/** Author bio on the profile card. Bios are user-written, so we sanitize. */
export function Bio({ text }: { text: string }) {
  return <div className="bio" dangerouslySetInnerHTML={{ __html: sanitize(renderMarkdown(text)) }} />;
}
