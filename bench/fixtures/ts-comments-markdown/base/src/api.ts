import type { Comment } from "./types";

export async function fetchComments(postId: string): Promise<Comment[]> {
  const res = await fetch(`/api/posts/${encodeURIComponent(postId)}/comments`);
  if (!res.ok) throw new Error(`fetchComments failed: ${res.status}`);
  return res.json();
}
