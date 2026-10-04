from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services.geo import distance_m

MAX_ACCURACY_M = 100.0
MIN_OUTSIDE_READINGS = 3
COOLDOWN = timedelta(minutes=30)


@dataclass(frozen=True)
class Reading:
    lat: float
    lng: float
    accuracy_m: float | None
    recorded_at: datetime


def should_alert(
    readings: list[Reading],
    *,
    home_lat: float | None,
    home_lng: float | None,
    radius_m: float,
    now: datetime,
    last_alert_at: datetime | None = None,
    min_outside: int = MIN_OUTSIDE_READINGS,
    max_accuracy_m: float = MAX_ACCURACY_M,
    cooldown: timedelta = COOLDOWN,
) -> bool:
    """Decide whether a device that left its home area should trigger an alert.

    `readings` must be ordered newest first. An alert fires only when:
    - the device has a home location,
    - the `min_outside` most recent accurate readings are all outside the radius,
    - and no alert was sent within the cooldown period.
    """
    if home_lat is None or home_lng is None:
        return False

    # Ignore readings with poor GPS accuracy (unknown accuracy is accepted)
    usable = [r for r in readings if r.accuracy_m is None or r.accuracy_m <= max_accuracy_m]

    recent = usable[:min_outside]
    if len(recent) < min_outside:
        return False

    if not all(distance_m(home_lat, home_lng, r.lat, r.lng) > radius_m for r in recent):
        return False

    if last_alert_at is not None and now - last_alert_at < cooldown:
        return False

    return True
