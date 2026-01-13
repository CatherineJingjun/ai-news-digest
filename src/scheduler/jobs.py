from datetime import datetime

import structlog
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.collectors import RSSCollector, YouTubeCollector
from src.config import settings, sources
from src.digest import DigestGenerator, EmailSender
from src.processors import ContentSummarizer
from src.storage import init_db

logger = structlog.get_logger()


class DigestScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="US/Pacific")
        self.rss_collector = RSSCollector()
        self.youtube_collector = YouTubeCollector()
        self.summarizer = ContentSummarizer()
        self.digest_generator = DigestGenerator()
        self.email_sender = EmailSender()

    def collect_rss_job(self):
        logger.info("running_rss_collection")
        try:
            self.rss_collector.collect_all(sources.rss_feeds)
        except Exception as e:
            logger.error("rss_collection_failed", error=str(e))

    def collect_youtube_job(self):
        logger.info("running_youtube_collection")
        try:
            self.youtube_collector.collect_all(sources.youtube_channels)
        except Exception as e:
            logger.error("youtube_collection_failed", error=str(e))

    def process_content_job(self):
        logger.info("running_content_processing")
        try:
            self.summarizer.process_unprocessed(limit=50)
        except Exception as e:
            logger.error("content_processing_failed", error=str(e))

    def generate_digest_job(self):
        logger.info("running_digest_generation")
        try:
            self.digest_generator.create_and_save_digest()
        except Exception as e:
            logger.error("digest_generation_failed", error=str(e))

    def send_digest_job(self):
        logger.info("running_digest_send")
        try:
            self.email_sender.send_latest_digest()
        except Exception as e:
            logger.error("digest_send_failed", error=str(e))

    def setup_jobs(self):
        # RSS collection every 6 hours
        self.scheduler.add_job(
            self.collect_rss_job,
            CronTrigger(hour="*/6"),
            id="rss_collection",
            name="RSS Feed Collection",
            replace_existing=True,
        )

        # YouTube collection daily at midnight PT
        self.scheduler.add_job(
            self.collect_youtube_job,
            CronTrigger(hour=0, minute=0),
            id="youtube_collection",
            name="YouTube Channel Collection",
            replace_existing=True,
        )

        # Process content nightly at 11 PM PT
        self.scheduler.add_job(
            self.process_content_job,
            CronTrigger(hour=23, minute=0),
            id="content_processing",
            name="Content Processing",
            replace_existing=True,
        )

        # Generate digest at 6:30 AM PT
        self.scheduler.add_job(
            self.generate_digest_job,
            CronTrigger(hour=6, minute=30),
            id="digest_generation",
            name="Digest Generation",
            replace_existing=True,
        )

        # Send digest at 7:00 AM PT
        self.scheduler.add_job(
            self.send_digest_job,
            CronTrigger(hour=settings.digest_send_hour, minute=0),
            id="digest_send",
            name="Digest Email Send",
            replace_existing=True,
        )

        logger.info("scheduler_jobs_configured", job_count=5)

    def start(self):
        init_db()
        self.setup_jobs()
        self.scheduler.start()
        logger.info("scheduler_started")

    def stop(self):
        self.scheduler.shutdown()
        self.rss_collector.close()
        logger.info("scheduler_stopped")

    def run_now(self, job_name: str):
        job_map = {
            "rss": self.collect_rss_job,
            "youtube": self.collect_youtube_job,
            "process": self.process_content_job,
            "generate": self.generate_digest_job,
            "send": self.send_digest_job,
        }
        if job_name in job_map:
            job_map[job_name]()
        else:
            logger.error("unknown_job", job_name=job_name)

    def run_full_pipeline(self):
        logger.info("running_full_pipeline")
        self.collect_rss_job()
        self.collect_youtube_job()
        self.process_content_job()
        self.generate_digest_job()
        self.send_digest_job()
        logger.info("full_pipeline_complete")
