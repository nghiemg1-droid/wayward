import logging
from datetime import datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ping, utcnow

logger = logging.getLogger(__name__)

CHECK_EVERY = timedelta(hours=6)
_last_check: datetime | None = None


def prune_old_pings(db: Session, days: int, now: datetime | None = None) -> int:
    """Delete positions older than `days` days and return how many were removed."""
    now = now or utcnow()
    result = db.execute(delete(Ping).where(Ping.recorded_at < now - timedelta(days=days)))
    db.commit()
    return result.rowcount


def maybe_prune_old_pings(db: Session, now: datetime) -> None:
    """Prune at most once every CHECK_EVERY. A failure is logged and never breaks a ping."""
    global _last_check
    if settings.ping_retention_days <= 0:
        return
    if _last_check is not None and now - _last_check < CHECK_EVERY:
        return
    _last_check = now
    try:
        removed = prune_old_pings(db, settings.ping_retention_days, now)
        if removed:
            logger.info("Removed %s old positions", removed)
    except Exception:
        db.rollback()
        logger.exception("Could not remove old positions")
