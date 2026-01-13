#!/usr/bin/env python3
"""
AI News Digest - Main entry point

Usage:
    python main.py serve          # Start the scheduler (runs continuously)
    python main.py run            # Run the full pipeline once
    python main.py collect        # Run content collection only
    python main.py process        # Run content processing only
    python main.py digest         # Generate and send digest
    python main.py init           # Initialize database and seed data
"""

import sys
import time

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


def init_database():
    from src.storage import init_db
    from src.conferences import seed_conferences

    logger.info("initializing_database")
    init_db()
    seed_conferences()
    logger.info("database_initialized")


def run_collection():
    from src.collectors import RSSCollector, YouTubeCollector
    from src.config import sources

    rss = RSSCollector()
    youtube = YouTubeCollector()

    try:
        rss.collect_all(sources.rss_feeds)
        youtube.collect_all(sources.youtube_channels)
    finally:
        rss.close()


def run_processing():
    from src.processors import ContentSummarizer

    summarizer = ContentSummarizer()
    summarizer.process_unprocessed(limit=50)


def run_digest():
    from src.digest import DigestGenerator, EmailSender

    generator = DigestGenerator()
    sender = EmailSender()

    digest = generator.create_and_save_digest()
    if digest:
        sender.send_digest(digest)


def serve():
    from src.scheduler import DigestScheduler

    scheduler = DigestScheduler()

    try:
        scheduler.start()
        logger.info("scheduler_running", message="Press Ctrl+C to stop")
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("shutting_down")
        scheduler.stop()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    commands = {
        "init": init_database,
        "serve": serve,
        "run": lambda: (run_collection(), run_processing(), run_digest()),
        "collect": run_collection,
        "process": run_processing,
        "digest": run_digest,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    commands[command]()


if __name__ == "__main__":
    main()
