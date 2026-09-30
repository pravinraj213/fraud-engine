import { useEffect, useState } from "react";

export default function ReviewerName({ value, onChange }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);

  const save = () => onChange(draft.trim().slice(0, 64));

  return (
    <label className={`reviewer ${value ? "" : "reviewer-missing"}`}>
      <span>Reviewer</span>
      <input
        value={draft}
        maxLength={64}
        placeholder="Your name"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
      />
    </label>
  );
}
