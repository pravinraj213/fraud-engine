/**
 * Browser version of simulator/generate_transactions.py: the same scenarios, posted to the API.
 * Each run tags its account IDs (e.g. ACC-2001-K7Q) so re-runs start from a clean history.
 */
import { api } from "../api/client.js";

export const CITIES = {
  "Chennai, IN": [13.0827, 80.2707],
  "Mumbai, IN": [19.076, 72.8777],
  "Delhi, IN": [28.6139, 77.209],
  "Bengaluru, IN": [12.9716, 77.5946],
  "Kolkata, IN": [22.5726, 88.3639],
  "London, GB": [51.5072, -0.1276],
  "Dubai, AE": [25.2048, 55.2708],
  "Singapore, SG": [1.3521, 103.8198],
};
const HOME_CITIES = ["Chennai, IN", "Mumbai, IN", "Delhi, IN", "Bengaluru, IN", "Kolkata, IN"];
export const MERCHANTS = [
  "Big Bazaar", "Croma Electronics", "Swiggy", "Zomato", "Reliance Fresh", "Apollo Pharmacy",
  "Indian Oil", "Amazon India", "Myntra", "Cafe Coffee Day", "BookMyShow", "Tanishq",
];
// The first purchases cover the account's whole normal range, so later ordinary purchases
// never look like z-score outliers against a history that happens to be too uniform.
const SPREAD = [1.0, 0.6, 1.4, 0.8, 1.2];

export const SCENARIOS = [
  {
    id: "baseline",
    title: "Normal customers",
    description: "10 accounts, each with 20 ordinary purchases over the past 30 days in their home city.",
    expect: "All CLEAN",
    highAlerts: 0,
    requests: 200,
  },
  {
    id: "velocity",
    title: "Card being drained",
    description: "10 normal purchases, then 8 purchases within 6 minutes.",
    expect: "HIGH (70)",
    highAlerts: 1,
    requests: 18,
  },
  {
    id: "amount",
    title: "Unusually large amount",
    description: "INR 60,000 after normal spending, plus a brand-new account spending INR 1,50,000.",
    expect: "HIGH (80) and MEDIUM (50)",
    highAlerts: 1,
    requests: 12,
  },
  {
    id: "travel",
    title: "Impossible travel",
    description: "A purchase in Chennai, then one in London 45 minutes later.",
    expect: "HIGH (90)",
    highAlerts: 1,
    requests: 12,
  },
  {
    id: "combo",
    title: "Burst + big purchase",
    description: "7 purchases in 5 minutes, the last one INR 20,000.",
    expect: "HIGH (100, capped)",
    highAlerts: 1,
    requests: 17,
  },
];

function seededRandom(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function runTag() {
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  return Array.from({ length: 3 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
}

const MINUTE = 60_000;

class Runner {
  constructor({ seed, onProgress }) {
    this.rand = seededRandom(seed);
    this.now = Date.now();
    this.tag = runTag();
    this.onProgress = onProgress;
    this.sent = 0;
    this.homes = {};
    this.bases = {};
    this.counts = {};
    this.checks = [];
  }

  pick(list) {
    return list[Math.floor(this.rand() * list.length)];
  }

  account(base) {
    return `${base}-${this.tag}`;
  }

  async send(account, amount, city, at, merchant) {
    const [latitude, longitude] = CITIES[city];
    const detail = await api.createTransaction({
      account_id: account,
      amount: amount.toFixed(2),
      currency: "INR",
      merchant: merchant ?? this.pick(MERCHANTS),
      latitude,
      longitude,
      location_label: city,
      occurred_at: new Date(at).toISOString(),
    });
    this.sent += 1;
    this.onProgress?.(this.sent);
    return detail;
  }

  normalAmount(account) {
    this.bases[account] ??= 400 + this.rand() * 1600;
    this.counts[account] = (this.counts[account] ?? 0) + 1;
    const n = this.counts[account];
    const factor = n <= SPREAD.length ? SPREAD[n - 1] : 0.6 + this.rand() * 0.8;
    return Math.round(this.bases[account] * factor * 100) / 100;
  }

  async baseline(account, count, days = 30, home) {
    this.homes[account] = home ?? this.homes[account] ?? this.pick(HOME_CITIES);
    const start = this.now - days * 1440 * MINUTE;
    const step = ((days - 1) * 1440 * MINUTE) / count;
    const results = [];
    for (let i = 0; i < count; i++) {
      results.push(await this.send(account, this.normalAmount(account), this.homes[account], start + step * i));
    }
    return results;
  }

  record(scenario, account, description, expected, detail) {
    this.checks.push({
      scenario,
      account,
      description,
      expected,
      actual: detail.assessment.risk_level,
      score: detail.assessment.total_score,
      rules: detail.rule_hits.map((h) => h.rule_name),
      transactionId: detail.transaction.id,
    });
  }

  async baselineScenario() {
    for (let n = 1001; n <= 1010; n++) {
      const account = this.account(`ACC-${n}`);
      const results = await this.baseline(account, 20);
      const worst = results.reduce((a, b) => (b.assessment.total_score > a.assessment.total_score ? b : a));
      this.record("baseline", account, "20 normal purchases over 30 days", "NONE", worst);
    }
  }

  async velocityScenario() {
    const account = this.account("ACC-2001");
    await this.baseline(account, 10);
    const start = this.now - 6 * MINUTE;
    let last;
    for (let i = 0; i < 8; i++) {
      last = await this.send(account, this.normalAmount(account), this.homes[account], start + i * 45_000);
    }
    this.record("velocity", account, "8 purchases in 6 minutes", "HIGH", last);
  }

  async amountScenario() {
    const regular = this.account("ACC-3001");
    await this.baseline(regular, 10);
    const big = await this.send(regular, 60000, this.homes[regular], this.now, "Tanishq");
    this.record("amount", regular, "INR 60,000 after normal spending", "HIGH", big);
    const fresh = this.account("ACC-3002");
    const first = await this.send(fresh, 150000, "Mumbai, IN", this.now, "Croma Electronics");
    this.record("amount", fresh, "Brand-new account, INR 1,50,000", "MEDIUM", first);
  }

  async travelScenario() {
    const account = this.account("ACC-4001");
    await this.baseline(account, 10, 30, "Chennai, IN");
    await this.send(account, this.normalAmount(account), "Chennai, IN", this.now - 45 * MINUTE);
    const london = await this.send(account, this.normalAmount(account), "London, GB", this.now, "Harrods");
    this.record("travel", account, "Chennai, then London 45 min later", "HIGH", london);
  }

  async comboScenario() {
    const account = this.account("ACC-5001");
    await this.baseline(account, 10);
    const start = this.now - 5 * MINUTE;
    for (let i = 0; i < 6; i++) {
      await this.send(account, this.normalAmount(account), this.homes[account], start + i * 40_000);
    }
    const last = await this.send(account, 20000, this.homes[account], this.now, "Croma Electronics");
    this.record("combo", account, "7 purchases in 5 min, last INR 20,000", "HIGH", last);
  }
}

/** Runs the chosen scenarios in order and returns one check per expected verdict. */
export async function runScenarios(ids, { seed = 42, onProgress } = {}) {
  const runner = new Runner({ seed, onProgress });
  for (const id of ids) {
    await runner[`${id}Scenario`]();
  }
  return { tag: runner.tag, checks: runner.checks };
}
