from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Alert, Device, Ping, User, utcnow
from app.routers.devices import get_owned_device
from app.schemas import AlertOut, PingCreate, PingOut
from app.services.alerting import check_for_alert, format_alert_message
from app.services.notifier import send_alert_message
from app.services.retention import maybe_prune_old_pings

router = APIRouter(tags=["pings"])


def get_device_from_token(
    x_device_token: str = Header(),
    db: Session = Depends(get_db),
) -> Device:
    device = db.scalar(select(Device).where(Device.device_token == x_device_token))
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token"
        )
    return device


def record_ping(
    db: Session,
    background_tasks: BackgroundTasks,
    device: Device,
    lat: float,
    lng: float,
    accuracy_m: float | None,
    recorded_at: datetime | None = None,
) -> Ping:
    """Store a position, update last_seen and raise an alert if the rules say so."""
    now = utcnow()
    maybe_prune_old_pings(db, now)
    ping = Ping(
        device_id=device.id,
        lat=lat,
        lng=lng,
        accuracy_m=accuracy_m,
        recorded_at=recorded_at or now,
    )
    device.last_seen = now
    db.add(ping)
    db.commit()
    db.refresh(ping)

    alert = check_for_alert(db, device, now)
    if alert is not None:
        # The message is built now, while the database session is still open;
        # sending it happens in the background so the device gets a fast response.
        background_tasks.add_task(send_alert_message, format_alert_message(device, alert))
    return ping


@router.post("/pings", response_model=PingOut, status_code=status.HTTP_201_CREATED)
def create_ping(
    data: PingCreate,
    background_tasks: BackgroundTasks,
    device: Device = Depends(get_device_from_token),
    db: Session = Depends(get_db),
):
    return record_ping(db, background_tasks, device, data.lat, data.lng, data.accuracy_m)


def parse_timestamp(value: str | None) -> datetime | None:
    """Read the time a phone says a position was taken (Unix seconds, or milliseconds).

    Phone apps may queue positions while offline and send them later, so the time
    they report is more accurate than the time we receive them. Values that make no
    sense (unreadable, in the future, or older than a week) are ignored.
    """
    if not value:
        return None
    try:
        seconds = float(value)
        if seconds > 1e11:  # milliseconds
            seconds /= 1000
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None
    now = utcnow()
    if moment > now + timedelta(minutes=5) or moment < now - timedelta(days=7):
        return None
    return moment


@router.get("/osmand")
def report_from_tracking_app(
    background_tasks: BackgroundTasks,
    device_token: str = Query(alias="id", min_length=1),
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    accuracy: float | None = Query(default=None, ge=0),
    timestamp: str | None = None,
    db: Session = Depends(get_db),
):
    """Receive positions from tracking apps such as Traccar Client (OsmAnd-style GET).

    These apps run in the background on a phone and cannot send custom headers, so the
    device token travels in the `id` query parameter (it can show up in server logs).
    """
    device = db.scalar(select(Device).where(Device.device_token == device_token))
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")
    record_ping(db, background_tasks, device, lat, lon, accuracy, parse_timestamp(timestamp))
    return Response(content="OK", media_type="text/plain")


@router.get("/devices/{device_id}/pings", response_model=list[PingOut])
def list_pings(
    device_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = get_owned_device(device_id, current_user, db)
    query = (
        select(Ping)
        .where(Ping.device_id == device.id)
        .order_by(Ping.recorded_at.desc(), Ping.id.desc())
        .limit(limit)
    )
    return list(db.scalars(query))


@router.get("/devices/{device_id}/alerts", response_model=list[AlertOut])
def list_alerts(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = get_owned_device(device_id, current_user, db)
    query = (
        select(Alert)
        .where(Alert.device_id == device.id)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(limit)
    )
    return list(db.scalars(query))
