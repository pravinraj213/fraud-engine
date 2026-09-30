export default function Pagination({ offset, limit, total, onChange }) {
  if (!total) return <span className="muted small">0 transactions</span>;
  return (
    <nav className="pagination" aria-label="Pages">
      <span>
        {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </span>
      <button
        aria-label="Previous page"
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - limit))}
      >
        ←
      </button>
      <button
        aria-label="Next page"
        disabled={offset + limit >= total}
        onClick={() => onChange(offset + limit)}
      >
        →
      </button>
    </nav>
  );
}
