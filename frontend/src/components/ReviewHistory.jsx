import { dateTime } from "../utils/format.js";
import StatusBadge from "./StatusBadge.jsx";

export default function ReviewHistory({ reviews }) {
  if (reviews.length === 0) return null;
  return (
    <section className="panel">
      <h2>Review history</h2>
      <ol className="history">
        {reviews.map((r, i) => (
          <li key={`${r.created_at}-${i}`}>
            <div>
              <strong>{r.reviewer}</strong> marked <strong>{r.action.toLowerCase()}</strong>{" "}
              <StatusBadge status={r.from_status} /> → <StatusBadge status={r.to_status} />
            </div>
            <time className="muted">{dateTime(r.created_at)}</time>
            {r.note && <blockquote>{r.note}</blockquote>}
          </li>
        ))}
      </ol>
    </section>
  );
}
