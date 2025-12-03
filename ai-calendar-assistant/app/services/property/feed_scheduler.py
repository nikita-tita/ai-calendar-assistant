"""Feed update scheduler for Property Bot."""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import structlog

from app.services.property.feed_loader import feed_loader

logger = structlog.get_logger()


class FeedScheduler:
    """Scheduler for automatic feed updates."""

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.update_count = 0
        self.last_result = None

    async def update_feed_task(self):
        """Task to update feed."""
        logger.info("feed_update_scheduled_start", update_number=self.update_count + 1)

        try:
            result = await feed_loader.update_feed()
            self.last_result = result
            self.update_count += 1

            if result["status"] == "success":
                logger.info("feed_update_scheduled_complete",
                           update_number=self.update_count,
                           total=result.get("total", 0),
                           created=result.get("created", 0),
                           updated=result.get("updated", 0),
                           duration=result.get("duration_seconds", 0))
            else:
                logger.error("feed_update_scheduled_failed",
                            update_number=self.update_count,
                            error=result.get("error"))

        except Exception as e:
            logger.error("feed_update_scheduled_error",
                        error=str(e),
                        exc_info=True)
            self.last_result = {
                "status": "error",
                "error": str(e),
                "update_number": self.update_count
            }

    def start(self):
        """Start scheduler."""
        if self.is_running:
            logger.warning("feed_scheduler_already_running")
            return

        # Schedule every 6 hours
        # Run at 00:00, 06:00, 12:00, 18:00 UTC
        self.scheduler.add_job(
            self.update_feed_task,
            trigger=CronTrigger(hour='0,6,12,18', minute=0),
            id="feed_update_cron",
            name="Update property feed (cron)",
            replace_existing=True,
            misfire_grace_time=3600  # Allow 1 hour grace period
        )

        # Also schedule every 6 hours as fallback
        self.scheduler.add_job(
            self.update_feed_task,
            trigger=IntervalTrigger(hours=6, start_date=None),
            id="feed_update_interval",
            name="Update property feed (interval)",
            replace_existing=True
        )

        # Run immediately on startup (after 30 second delay)
        async def delayed_first_update():
            await asyncio.sleep(30)
            await self.update_feed_task()

        self.scheduler.add_job(
            delayed_first_update,
            id="feed_update_immediate",
            name="Immediate feed update (startup)"
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("feed_scheduler_started",
                   interval_hours=6,
                   cron_schedule="0,6,12,18:00")

    def stop(self):
        """Stop scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("feed_scheduler_stopped", total_updates=self.update_count)

    def get_status(self):
        """Get scheduler status."""
        if not self.is_running:
            return {
                "running": False,
                "total_updates": self.update_count,
                "last_result": self.last_result
            }

        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = None
            if job.next_run_time:
                next_run = job.next_run_time.isoformat()

            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run
            })

        return {
            "running": True,
            "total_updates": self.update_count,
            "jobs": jobs,
            "last_result": self.last_result
        }

    def trigger_manual_update(self):
        """Trigger manual feed update immediately."""
        if not self.is_running:
            logger.error("feed_scheduler_not_running")
            return False

        logger.info("feed_update_manual_trigger")

        # Add one-time job
        self.scheduler.add_job(
            self.update_feed_task,
            id=f"feed_update_manual_{self.update_count}",
            name="Manual feed update"
        )

        return True


# Global instance
feed_scheduler = FeedScheduler()
