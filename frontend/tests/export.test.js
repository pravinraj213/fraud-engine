import assert from "node:assert/strict";
import { csvCell, transactionsCsv } from "../src/utils/export.js";
assert.equal(csvCell("=SUM(A1)"), '"\'=SUM(A1)"');
assert.equal(csvCell("  +1"), '"\'  +1"');
assert.equal(csvCell('a"b'), '"a""b"');
assert.equal(csvCell(null), '""');
const csv = transactionsCsv([
  {
    merchant: "Example, Inc.",
    amount: "1200.00",
    rules_triggered: ["velocity", "unusual_amount"],
  },
]);
assert.ok(csv.includes('"Example, Inc."'));
assert.ok(csv.includes('"1200.00"'));
assert.ok(csv.includes('"velocity; unusual_amount"'));
assert.equal(csv.split("\r\n").length, 2);
console.log("8 CSV export assertions passed.");
