export default function StatusBadge({ status }) {
  return <span className={`badge status-${status.toLowerCase()}`}>{status}</span>;
}
