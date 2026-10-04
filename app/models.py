import secrets
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    devices: Mapped[list["Device"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    device_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=lambda: secrets.token_urlsafe(32)
    )
    home_lat: Mapped[float | None] = mapped_column(default=None)
    home_lng: Mapped[float | None] = mapped_column(default=None)
    radius_m: Mapped[int] = mapped_column(default=500)
    last_seen: Mapped[datetime | None] = mapped_column(default=None)

    owner: Mapped["User"] = relationship(back_populates="devices")
    pings: Mapped[list["Ping"]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class Ping(Base):
    __tablename__ = "pings"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    lat: Mapped[float] = mapped_column()
    lng: Mapped[float] = mapped_column()
    accuracy_m: Mapped[float | None] = mapped_column(default=None)
    recorded_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    device: Mapped["Device"] = relationship(back_populates="pings")
