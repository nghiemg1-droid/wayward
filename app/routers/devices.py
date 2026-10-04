from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Device, User
from app.schemas import DeviceCreate, DeviceCreated, DeviceOut

router = APIRouter(prefix="/devices", tags=["devices"])


def get_owned_device(device_id: int, user: User, db: Session) -> Device:
    device = db.scalar(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.post("", response_model=DeviceCreated, status_code=status.HTTP_201_CREATED)
def create_device(
    data: DeviceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    name = data.name.strip()
    duplicate = db.scalar(
        select(Device).where(
            Device.user_id == current_user.id,
            func.lower(Device.name) == name.lower(),
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a device with this name",
        )
    data.name = name

    device = Device(user_id=current_user.id, **data.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("", response_model=list[DeviceOut])
def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Device).where(Device.user_id == current_user.id).order_by(Device.id)
    return list(db.scalars(query))


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_owned_device(device_id, current_user, db)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = get_owned_device(device_id, current_user, db)
    db.delete(device)
    db.commit()