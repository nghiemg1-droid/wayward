from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    home_lat: float | None = Field(default=None, ge=-90, le=90)
    home_lng: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=500, ge=50, le=50000)


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    home_lat: float | None
    home_lng: float | None
    radius_m: int
    last_seen: datetime | None


class DeviceCreated(DeviceOut):
    device_token: str

class PingCreate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0)


class PingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lat: float
    lng: float
    accuracy_m: float | None
    recorded_at: datetime
