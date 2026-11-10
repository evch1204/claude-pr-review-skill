import { useEffect, useState } from "react";
import { fetchComments } from "../api";
import { relativeTime } from "../format";
import { renderMarkdown } from "../markdown";
import type { Comment } from "../types";

export function CommentList({ postId }: { postId: string }) {
  const [comments, setComments] = useState<Comment[]>([]);

  useEffect(() => {
    fetchComments(postId).then(setComments);
  }, []);

  return (
    <ul>
      {comments.map((c, i) => (
        <li key={i}>
          <strong>{c.author.name}</strong> <time>{relativeTime(c.createdAt)}</time>
          <div dangerouslySetInnerHTML={{ __html: renderMarkdown(c.body) }} />
        </li>
      ))}
    </ul>
  );
}
