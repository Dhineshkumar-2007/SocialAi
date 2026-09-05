"""Scheduled background timeout scanner service (Step 10).
Triggers assignment_service.check_expired_assignments() at configured interval.
Can be run directly or via a scheduler loop.
"""
import time
import logging
from datetime import datetime
from services import assignment_service
from config import Config

logger = logging.getLogger("timeout_scanner")


INTERVAL_MINUTES = int(getattr(Config, 'TIMEOUT_SCANNER_INTERVAL_MINUTES', 30))
TIMEOUT_HOURS = getattr(Config, 'UNIVERSITY_RESPONSE_TIMEOUT_HOURS', 72)


def run_scan():
    """Single scan pass: expire stale assignments and re-route."""
    logger.info("[Timeout Scanner] Starting scan at %s", datetime.utcnow().isoformat())
    try:
        expired = assignment_service.check_expired_assignments()
        logger.info(
            "[Timeout Scanner] Expired %d assignment(s) after %dh timeout. IDs: %s",
            len(expired), TIMEOUT_HOURS, expired
        )
        return {"expired_count": len(expired), "expired_ids": expired, "timeout_hours": TIMEOUT_HOURS, "scanned_at": datetime.utcnow().isoformat()}
    except Exception as exc:
        logger.error("[Timeout Scanner] Scan failed: %s", exc)
        return {"error": str(exc), "scanned_at": datetime.utcnow().isoformat()}


def start_scheduler():
    """Continuous background loop — call from a background thread or cron job."""
    logger.info("Timeout scanner scheduler started (interval=%dm, timeout=%dh).", INTERVAL_MINUTES, TIMEOUT_HOURS)
    while True:
        result = run_scan()
        logger.info("Scan result: %s", result)
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    # Direct execution mode for manual/admin trigger
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(run_scan())
