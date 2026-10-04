from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Device, Ping, User, utcnow
from app.routers.devices import get_owned_device
from app.schemas import PingCreate, PingOut

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


@router.post("/pings", response_model=PingOut, status_code=status.HTTP_201_CREATED)
def create_ping(
    data: PingCreate,
    device: Device = Depends(get_device_from_token),
    db: Session = Depends(get_db),
):
    now = utcnow()
    ping = Ping(device_id=device.id, recorded_at=now, **data.model_dump())
    device.last_seen = now
    db.add(ping)
    db.commit()
    db.refresh(ping)
    return ping


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
