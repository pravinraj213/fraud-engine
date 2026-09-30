// Quote all values and neutralize spreadsheet formulas from user-provided fields.
export function csvCell(value) {
  let text = String(value ?? "");
  if (/^[\s]*[=+@-]/.test(text)) text = "'" + text;
  return '"' + text.replace(/"/g, '""') + '"';
}
export function transactionsCsv(items) {
  const fields = [
    "transaction_id",
    "account_id",
    "merchant",
    "amount",
    "currency",
    "location_label",
    "occurred_at",
    "total_score",
    "risk_level",
    "status",
    "rules_triggered",
  ];
  return [
    fields,
    ...items.map((t) =>
      fields.map((key) => (Array.isArray(t[key]) ? t[key].join("; ") : t[key])),
    ),
  ]
    .map((row) => row.map(csvCell).join(","))
    .join("\r\n");
}
export function exportTransactions(items) {
  const url = URL.createObjectURL(
    new Blob(["\uFEFF" + transactionsCsv(items)], {
      type: "text/csv;charset=utf-8;",
    }),
  );
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "suraksha-transactions.csv";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
