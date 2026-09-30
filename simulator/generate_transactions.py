"""Send normal and fraudulent traffic to the running API and check every verdict.

    python simulator/generate_transactions.py --scenario all --base-url http://localhost:8000 --seed 42

Prints a pass/fail table and exits 1 if any actual risk level differs from the expected one.
Running it twice adds more history; delete backend/fraud.db and restart the API for a clean demo.
"""
import argparse
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

CITIES: dict[str, tuple[float, float]] = {
    "Chennai, IN": (13.0827, 80.2707), "Mumbai, IN": (19.0760, 72.8777), "Delhi, IN": (28.6139, 77.2090),
    "Bengaluru, IN": (12.9716, 77.5946), "Kolkata, IN": (22.5726, 88.3639), "London, GB": (51.5072, -0.1276),
    "Dubai, AE": (25.2048, 55.2708), "Singapore, SG": (1.3521, 103.8198),
}
HOME_CITIES = ["Chennai, IN", "Mumbai, IN", "Delhi, IN", "Bengaluru, IN", "Kolkata, IN"]
MERCHANTS = ["Big Bazaar", "Croma Electronics", "Swiggy", "Zomato", "Reliance Fresh", "Apollo Pharmacy",
             "Indian Oil", "Amazon India", "Myntra", "Cafe Coffee Day", "BookMyShow", "Tanishq"]


@dataclass
class Check:
    scenario: str
    account: str
    description: str
    expected: str
    actual: str
    score: int
    rules: list[str]

    @property
    def passed(self) -> bool:
        return self.expected == self.actual


class Simulator:
    def __init__(self, base_url: str, rng: random.Random) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=10)
        self.rng = rng
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.homes: dict[str, str] = {}
        self.bases: dict[str, float] = {}
        self.counts: dict[str, int] = {}
        self.checks: list[Check] = []

    def send(self, account: str, amount: float, city: str, at: datetime, merchant: str | None = None) -> dict:
        lat, lon = CITIES[city]
        body = {"account_id": account, "amount": str(Decimal(str(amount)).quantize(Decimal("0.01"))),
                "currency": "INR", "merchant": merchant or self.rng.choice(MERCHANTS),
                "latitude": lat, "longitude": lon, "location_label": city, "occurred_at": at.isoformat()}
        response = self.http.post("/api/transactions", json=body)
        response.raise_for_status()
        return response.json()

    # The first purchases cover the account's whole normal range, so a later ordinary purchase
    # never looks like a z-score outlier against a history that happens to be too uniform.
    SPREAD = (1.0, 0.6, 1.4, 0.8, 1.2)

    def normal_amount(self, account: str) -> float:
        """A typical purchase: within ±40% of the account's own base amount (INR 400-2,000)."""
        base = self.bases.setdefault(account, self.rng.uniform(400, 2000))
        seen = self.counts[account] = self.counts.get(account, 0) + 1
        factor = self.SPREAD[seen - 1] if seen <= len(self.SPREAD) else self.rng.uniform(0.6, 1.4)
        return round(base * factor, 2)

    def baseline(self, account: str, count: int, days: int = 30) -> list[dict]:
        """`count` normal purchases spread over the past `days`, ending a day ago, in the home city."""
        home = self.homes.setdefault(account, self.rng.choice(HOME_CITIES))
        step = timedelta(days=days - 1) / count
        start = self.now - timedelta(days=days)
        return [self.send(account, self.normal_amount(account), home, start + step * i) for i in range(count)]

    def record(self, scenario: str, account: str, description: str, expected: str, detail: dict) -> None:
        a = detail["assessment"]
        self.checks.append(Check(scenario, account, description, expected, a["risk_level"], a["total_score"],
                                 [h["rule_name"] for h in detail["rule_hits"]]))

    # --- scenarios -------------------------------------------------------------------------

    def scenario_baseline(self) -> None:
        for n in range(1001, 1011):
            account = f"ACC-{n}"
            results = self.baseline(account, 20)
            worst = max(results, key=lambda d: d["assessment"]["total_score"])
            self.record("baseline", account, "20 normal purchases over 30 days", "NONE", worst)

    def scenario_velocity(self) -> None:
        account = "ACC-2001"
        self.baseline(account, 10)
        home = self.homes[account]
        start = self.now - timedelta(minutes=6)
        last = {}
        for i in range(8):
            last = self.send(account, self.normal_amount(account), home, start + timedelta(seconds=45 * i))
        self.record("velocity", account, "8 purchases in 6 minutes", "HIGH", last)

    def scenario_amount(self) -> None:
        self.baseline("ACC-3001", 10)
        big = self.send("ACC-3001", 60_000, self.homes["ACC-3001"], self.now, "Tanishq")
        self.record("amount", "ACC-3001", "INR 60,000 after normal spending", "HIGH", big)
        new = self.send("ACC-3002", 150_000, "Mumbai, IN", self.now, "Croma Electronics")
        self.record("amount", "ACC-3002", "Brand-new account, INR 150,000", "MEDIUM", new)

    def scenario_travel(self) -> None:
        account = "ACC-4001"
        self.homes[account] = "Chennai, IN"
        self.baseline(account, 10)
        self.send(account, self.normal_amount(account), "Chennai, IN", self.now - timedelta(minutes=45))
        london = self.send(account, self.normal_amount(account), "London, GB", self.now, "Harrods")
        self.record("travel", account, "Chennai, then London 45 min later", "HIGH", london)

    def scenario_combo(self) -> None:
        account = "ACC-5001"
        self.baseline(account, 10)
        home = self.homes[account]
        start = self.now - timedelta(minutes=5)
        for i in range(6):
            self.send(account, self.normal_amount(account), home, start + timedelta(seconds=40 * i))
        last = self.send(account, 20_000, home, self.now, "Croma Electronics")
        self.record("combo", account, "7 purchases in 5 min, last INR 20,000", "HIGH", last)

    SCENARIOS = ("baseline", "velocity", "amount", "travel", "combo")

    def run(self, names: list[str]) -> bool:
        for name in names:
            getattr(self, f"scenario_{name}")()
        self.print_table()
        return all(c.passed for c in self.checks)

    def print_table(self) -> None:
        print(f"\n{'Scenario':<9} {'Account':<9} {'Expected':<8} {'Actual':<8} {'Score':>5}  {'Result':<6} Rules / description")
        print("-" * 100)
        for c in self.checks:
            mark = "PASS" if c.passed else "FAIL"
            rules = ", ".join(c.rules) or "-"
            print(f"{c.scenario:<9} {c.account:<9} {c.expected:<8} {c.actual:<8} {c.score:>5}  {mark:<6} {rules} / {c.description}")
        failed = sum(not c.passed for c in self.checks)
        print("-" * 100)
        print(f"{len(self.checks) - failed}/{len(self.checks)} checks passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=[*Simulator.SCENARIOS, "all"], default="all")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    sim = Simulator(args.base_url, random.Random(args.seed))
    names = list(Simulator.SCENARIOS) if args.scenario == "all" else [args.scenario]
    try:
        ok = sim.run(names)
    except httpx.HTTPError as exc:
        print(f"API request failed: {exc}. Is the backend running at {args.base_url}?", file=sys.stderr)
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
