import hashlib
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from src.storage import Content, ContentType, SessionLocal

logger = structlog.get_logger()


class RSSCollector:
    def __init__(self):
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        response = self.client.get(url)
        response.raise_for_status()
        return feedparser.parse(response.text)

    def determine_content_type(self, entry: dict, feed_title: str) -> ContentType:
        feed_lower = feed_title.lower()
        if "podcast" in feed_lower or "20vc" in feed_lower or "a16z" in feed_lower:
            return ContentType.PODCAST
        if entry.get("enclosures") or entry.get("links"):
            for link in entry.get("links", []):
                if link.get("type", "").startswith("audio/"):
                    return ContentType.PODCAST
        return ContentType.ARTICLE

    def parse_publish_date(self, entry: dict) -> datetime:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc)

    def extract_content(self, entry: dict) -> Optional[str]:
        if hasattr(entry, "content") and entry.content:
            return entry.content[0].get("value", "")
        if hasattr(entry, "summary"):
            return entry.summary
        if hasattr(entry, "description"):
            return entry.description
        return None

    def get_audio_url(self, entry: dict) -> Optional[str]:
        for enclosure in entry.get("enclosures", []):
            if enclosure.get("type", "").startswith("audio/"):
                return enclosure.get("href")
        for link in entry.get("links", []):
            if link.get("type", "").startswith("audio/"):
                return link.get("href")
        return None

    def collect_from_feed(self, feed_name: str, feed_url: str) -> list[Content]:
        logger.info("collecting_feed", feed_name=feed_name, url=feed_url)
        collected = []

        try:
            feed = self.fetch_feed(feed_url)
        except Exception as e:
            logger.error("feed_fetch_failed", feed_name=feed_name, error=str(e))
            return collected

        with SessionLocal() as session:
            for entry in feed.entries:
                source_url = entry.get("link", "")
                if not source_url:
                    continue

                existing = session.query(Content).filter_by(source_url=source_url).first()
                if existing:
                    continue

                content_type = self.determine_content_type(entry, feed.feed.get("title", feed_name))
                publish_date = self.parse_publish_date(entry)
                raw_content = self.extract_content(entry)

                content = Content(
                    source_name=feed_name,
                    source_url=source_url,
                    content_type=content_type,
                    title=entry.get("title", "Untitled"),
                    author=entry.get("author"),
                    publish_date=publish_date,
                    raw_content=raw_content,
                    processed=False,
                )

                if content_type == ContentType.PODCAST:
                    audio_url = self.get_audio_url(entry)
                    if audio_url:
                        content.entities = {"audio_url": audio_url}

                session.add(content)
                collected.append(content)
                logger.info(
                    "content_collected",
                    title=content.title,
                    content_type=content_type,
                    source=feed_name,
                )

            session.commit()

        return collected

    def collect_all(self, feeds: list[dict[str, str]]) -> list[Content]:
        all_collected = []
        for feed in feeds:
            collected = self.collect_from_feed(feed["name"], feed["url"])
            all_collected.extend(collected)
        logger.info("collection_complete", total_items=len(all_collected))
        return all_collected

    def close(self):
        self.client.close()
