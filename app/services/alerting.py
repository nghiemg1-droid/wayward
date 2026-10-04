from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Device, Ping
from app.services.alert_rules import Reading, should_alert
from app.services.geo import distance_m

RECENT_READINGS = 20


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC so they can be compared."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def check_for_alert(db: Session, device: Device, now: datetime) -> Alert | None:
    """Create and return an Alert if the device's recent pings call for one."""
    if device.home_lat is None or device.home_lng is None:
        return None

    pings = list(
        db.scalars(
            select(Ping)
            .where(Ping.device_id == device.id)
            .order_by(Ping.recorded_at.desc(), Ping.id.desc())
            .limit(RECENT_READINGS)
        )
    )
    readings = [
        Reading(
            lat=p.lat,
            lng=p.lng,
            accuracy_m=p.accuracy_m,
            recorded_at=_as_utc(p.recorded_at),
        )
        for p in pings
    ]
    last_alert = db.scalar(
        select(Alert)
        .where(Alert.device_id == device.id)
        .order_by(Alert.created_at.desc())
        .limit(1)
    )
    last_alert_at = _as_utc(last_alert.created_at) if last_alert else None

    if not should_alert(
        readings,
        home_lat=device.home_lat,
        home_lng=device.home_lng,
        radius_m=device.radius_m,
        now=_as_utc(now),
        last_alert_at=last_alert_at,
    ):
        return None

    latest = pings[0]
    alert = Alert(
        device_id=device.id,
        lat=latest.lat,
        lng=latest.lng,
        distance_m=distance_m(device.home_lat, device.home_lng, latest.lat, latest.lng),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def format_alert_message(device: Device, alert: Alert) -> str:
    km = alert.distance_m / 1000
    return (
        f"Wayward alert: '{device.name}' is {km:.1f} km from its home location "
        f"(last position {alert.lat:.5f}, {alert.lng:.5f})."
    )
