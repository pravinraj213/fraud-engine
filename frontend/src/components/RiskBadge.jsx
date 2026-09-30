export default function RiskBadge({ level, score }) {
  return (
    <span className={`badge risk-${level.toLowerCase()}`}>
      {level}
      {score !== undefined && <strong>{score}</strong>}
    </span>
  );
}
