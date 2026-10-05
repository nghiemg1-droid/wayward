from datetime import timedelta

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Device, Ping, User, utcnow
from app.services.retention import prune_old_pings


def make_session():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_prune_deletes_only_old_pings():
    db = make_session()
    user = User(email="a@example.com", hashed_password="x")
    db.add(user)
    db.flush()
    device = Device(user_id=user.id, name="Phone")
    db.add(device)
    db.flush()
    now = utcnow()
    db.add_all(
        [
            Ping(device_id=device.id, lat=1, lng=1, recorded_at=now - timedelta(days=40)),
            Ping(device_id=device.id, lat=1, lng=1, recorded_at=now - timedelta(days=2)),
        ]
    )
    db.commit()

    assert prune_old_pings(db, days=30, now=now) == 1
    assert db.scalar(select(func.count()).select_from(Ping)) == 1
