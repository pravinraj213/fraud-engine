from app.engine.base import HistoryProvider, Rule, RuleResult, TransactionData
from app.engine.geo_utils import haversine_km, place_label
from app.engine.registry import register_rule


@register_rule
class ImpossibleTravelRule(Rule):
    name = "impossible_travel"
    description = "Two transactions too far apart to travel between in the time available."
    default_params = {"max_speed_kmh": 900, "min_distance_km": 100}

    def evaluate(self, txn: TransactionData, history: HistoryProvider) -> RuleResult:
        prev = history.previous_transaction(txn.account_id, txn.occurred_at)
        if prev is None:
            return RuleResult(self.name, False)
        distance = haversine_km(prev.latitude, prev.longitude, txn.latitude, txn.longitude)
        if distance < float(self.params["min_distance_km"]):
            return RuleResult(self.name, False)

        max_speed = float(self.params["max_speed_kmh"])
        hours = (txn.occurred_at - prev.occurred_at).total_seconds() / 3600
        simultaneous = hours <= 0
        speed = None if simultaneous else distance / hours  # None means infinite
        if speed is not None and speed <= max_speed:
            return RuleResult(self.name, False)

        score = 90 if speed is None or speed > 2 * max_speed else 70
        minutes = max(hours * 60, 0)
        route = (f"{place_label(prev.location_label, prev.latitude, prev.longitude)} → "
                 f"{place_label(txn.location_label, txn.latitude, txn.longitude)}")
        speed_text = "same moment" if speed is None else f"{speed:,.0f} km/h"
        return RuleResult(
            self.name, True, score,
            f"{route}: {distance:,.0f} km in {minutes:,.0f} min ({speed_text}, max {max_speed:,.0f})",
            {"previous_transaction_id": prev.id,
             "previous_location": place_label(prev.location_label, prev.latitude, prev.longitude),
             "distance_km": round(distance, 1), "minutes_between": round(minutes, 1),
             "speed_kmh": round(speed, 1) if speed is not None else None,
             "simultaneous": simultaneous},
        )
