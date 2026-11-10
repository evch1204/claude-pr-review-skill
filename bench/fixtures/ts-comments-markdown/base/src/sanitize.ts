import DOMPurify from "dompurify";

/** Sanitize untrusted HTML before it is ever passed to dangerouslySetInnerHTML. */
export function sanitize(html: string): string {
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
}
