const inrFormatter = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

/** Money arrives from the API as a string, e.g. "4999.00". */
export function money(amount, currency = "INR") {
  const value = Number(amount);
  if (currency === "INR") return inrFormatter.format(value);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(value);
}

export function dateTime(iso) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function timeOnly(iso) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const UNITS = [
  ["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60], ["second", 1],
];

export function timeAgo(iso) {
  const seconds = (new Date(iso).getTime() - Date.now()) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size || unit === "second") {
      return relative.format(Math.round(seconds / size), unit);
    }
  }
  return "";
}

export function ruleLabel(name) {
  return name.replace(/_/g, " ");
}

export function number(value, digits = 0) {
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits });
}
