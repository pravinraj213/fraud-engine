from app.engine.geo_utils import haversine_km
from app.engine.rules.impossible_travel import ImpossibleTravelRule
from tests.fakes import InMemoryHistoryProvider, make_txn

RULE = ImpossibleTravelRule()


def after(prev_city: str, minutes_before: float, city: str, **kw):
    prev = make_txn(prev_city, minutes=-minutes_before)
    return RULE.evaluate(make_txn(city, **kw), InMemoryHistoryProvider([prev])), prev


def test_no_previous_transaction() -> None:
    assert not RULE.evaluate(make_txn(), InMemoryHistoryProvider()).triggered


def test_under_min_distance_not_triggered() -> None:
    prev = make_txn(minutes=-1, latitude=13.15, longitude=80.30)  # ~8 km away
    assert not RULE.evaluate(make_txn(), InMemoryHistoryProvider([prev])).triggered


def test_chennai_to_bengaluru_in_six_hours_not_triggered() -> None:
    result, _ = after("Chennai, IN", 360, "Bengaluru, IN")
    assert not result.triggered


def test_chennai_to_london_in_45_minutes_scores_90() -> None:
    result, prev = after("Chennai, IN", 45, "London, GB")
    assert result.triggered and result.score == 90
    assert result.reason.startswith("Chennai, IN → London, GB: ")
    assert "in 45 min" in result.reason and "max 900" in result.reason
    assert result.details["previous_transaction_id"] == prev.id
    assert result.details["simultaneous"] is False


def test_same_timestamp_500_km_scores_90_simultaneous() -> None:
    prev = make_txn(latitude=13.0827, longitude=80.2707)
    txn = make_txn(latitude=17.3850, longitude=78.4867, location_label=None)  # Hyderabad, ~520 km
    result = RULE.evaluate(txn, InMemoryHistoryProvider([prev]))
    assert result.triggered and result.score == 90
    assert result.details["simultaneous"] is True and result.details["speed_kmh"] is None
    assert "(17.39, 78.49)" in result.reason  # coordinates when no label


def test_speed_between_900_and_1800_scores_70() -> None:
    result, _ = after("Chennai, IN", 90, "Delhi, IN")  # ~1,760 km in 90 min
    assert result.triggered and result.score == 70
    assert 900 < result.details["speed_kmh"] <= 1800


def test_haversine_chennai_london_within_one_percent() -> None:
    assert abs(haversine_km(13.0827, 80.2707, 51.5072, -0.1276) - 8200) / 8200 < 0.01


def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(13.0827, 80.2707, 13.0827, 80.2707) == 0
