import { useEffect, useState } from "react";
import { fetchComments } from "../api";
import { relativeTime } from "../format";
import type { Comment } from "../types";

export function CommentList({ postId }: { postId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchComments(postId).then((c) => {
      if (!cancelled) setComments(c);
    });
    return () => {
      cancelled = true;
    };
  }, [postId]);

  return (
    <ul>
      {comments.map((c) => (
        <li key={c.id}>
          <strong>{c.author.name}</strong> <time>{relativeTime(c.createdAt)}</time>
          <p>{c.body}</p>
        </li>
      ))}
    </ul>
  );
}
