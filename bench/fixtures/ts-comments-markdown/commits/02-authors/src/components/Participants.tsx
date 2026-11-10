import moment from "moment";
import type { Comment } from "../types";

/** "12 people joined the discussion · last reply 3 hours ago" */
export function Participants({ comments }: { comments: Comment[] }) {
  const unique = comments.filter(
    (c, i) => comments.findIndex((x) => x.author.id === c.author.id) === i
  );
  const last = comments[comments.length - 1];
  return (
    <p className="participants">
      {unique.length} people joined the discussion
      {last && <> · last reply {moment(last.createdAt).fromNow()}</>}
    </p>
  );
}
