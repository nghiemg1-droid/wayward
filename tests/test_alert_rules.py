from datetime import datetime, timedelta, timezone

from app.services.alert_rules import Reading, should_alert

HOME = (37.7749, -122.4194)
NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
FAR = 0.05  # about 5.5 km north of home
NEAR = 0.001  # about 110 m from home


def reading(offset, minutes_ago, accuracy=10.0):
    return Reading(
        lat=HOME[0] + offset,
        lng=HOME[1],
        accuracy_m=accuracy,
        recorded_at=NOW - timedelta(minutes=minutes_ago),
    )


def check(readings, **kwargs):
    return should_alert(
        readings,
        home_lat=HOME[0],
        home_lng=HOME[1],
        radius_m=500,
        now=NOW,
        **kwargs,
    )


def test_no_home_location_never_alerts():
    readings = [reading(FAR, 1), reading(FAR, 2), reading(FAR, 3)]
    result = should_alert(readings, home_lat=None, home_lng=None, radius_m=500, now=NOW)
    assert result is False


def test_readings_inside_the_radius_do_not_alert():
    assert check([reading(NEAR, 1), reading(NEAR, 2), reading(NEAR, 3)]) is False


def test_too_few_readings_do_not_alert():
    assert check([reading(FAR, 1), reading(FAR, 2)]) is False


def test_three_consecutive_readings_outside_trigger_an_alert():
    assert check([reading(FAR, 1), reading(FAR, 2), reading(FAR, 3)]) is True


def test_single_gps_glitch_does_not_alert():
    assert check([reading(FAR, 1), reading(NEAR, 2), reading(NEAR, 3)]) is False


def test_returning_home_stops_the_alert():
    readings = [reading(NEAR, 1), reading(FAR, 2), reading(FAR, 3), reading(FAR, 4)]
    assert check(readings) is False


def test_low_accuracy_readings_are_ignored():
    noisy = [
        reading(FAR, 1, accuracy=500),
        reading(FAR, 2, accuracy=500),
        reading(FAR, 3, accuracy=500),
    ]
    assert check(noisy) is False


def test_noisy_reading_between_good_ones_is_skipped():
    readings = [
        reading(FAR, 1),
        reading(NEAR, 2, accuracy=500),
        reading(FAR, 3),
        reading(FAR, 4),
    ]
    assert check(readings) is True


def test_cooldown_blocks_repeat_alerts():
    readings = [reading(FAR, 1), reading(FAR, 2), reading(FAR, 3)]
    assert check(readings, last_alert_at=NOW - timedelta(minutes=10)) is False
    assert check(readings, last_alert_at=NOW - timedelta(minutes=31)) is True
