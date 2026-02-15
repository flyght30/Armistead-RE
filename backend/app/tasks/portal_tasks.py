"""Celery tasks for Phase 3: Party Portal — access log cleanup."""
import logging
from datetime import datetime, timedelta

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/ttc")
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)
    return Session()


@celery_app.task(name="app.tasks.portal_tasks.cleanup_access_logs")
def cleanup_access_logs():
    """Daily: delete portal access logs older than 180 days."""
    from app.models.portal import PortalAccessLog
    from sqlalchemy import delete

    session = _get_sync_session()
    try:
        cutoff = datetime.utcnow() - timedelta(days=180)
        stmt = delete(PortalAccessLog).where(PortalAccessLog.accessed_at < cutoff)
        result = session.execute(stmt)
        session.commit()
        logger.info(f"Cleaned up {result.rowcount} old portal access logs")
    except Exception as e:
        session.rollback()
        logger.error(f"Error cleaning up portal access logs: {e}")
        raise
    finally:
        session.close()
