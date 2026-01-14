import json
from datetime import datetime, timezone
from typing import Optional

import structlog

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    build = None
    HttpError = Exception

from src.config import settings
from src.storage import Content, ContentType, SessionLocal

logger = structlog.get_logger()


class YouTubeCollector:
    def __init__(self):
        self.youtube = None
        if build and settings.youtube_api_key:
            self.youtube = build("youtube", "v3", developerKey=settings.youtube_api_key)

    def get_channel_uploads(self, channel_id: str, max_results: int = 10) -> list[dict]:
        if not self.youtube:
            logger.warning("youtube_api_not_configured")
            return []

        try:
            channel_response = self.youtube.channels().list(
                part="contentDetails", id=channel_id
            ).execute()

            if not channel_response.get("items"):
                logger.error("channel_not_found", channel_id=channel_id)
                return []

            uploads_playlist_id = channel_response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]

            playlist_response = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results,
            ).execute()

            return playlist_response.get("items", [])

        except HttpError as e:
            logger.error("youtube_api_error", error=str(e), channel_id=channel_id)
            return []

    def get_video_details(self, video_id: str) -> Optional[dict]:
        if not self.youtube:
            return None

        try:
            response = self.youtube.videos().list(
                part="snippet,contentDetails,statistics", id=video_id
            ).execute()

            if response.get("items"):
                return response["items"][0]
            return None

        except HttpError as e:
            logger.error("video_details_error", error=str(e), video_id=video_id)
            return None

    def parse_duration(self, duration_str: str) -> int:
        import re
        pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
        match = pattern.match(duration_str)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def collect_from_channel(self, channel_name: str, channel_id: str) -> list[Content]:
        logger.info("collecting_youtube", channel_name=channel_name, channel_id=channel_id)
        collected = []

        videos = self.get_channel_uploads(channel_id)

        with SessionLocal() as session:
            for item in videos:
                snippet = item.get("snippet", {})
                video_id = item.get("contentDetails", {}).get("videoId")
                if not video_id:
                    continue

                source_url = f"https://www.youtube.com/watch?v={video_id}"

                existing = session.query(Content).filter_by(source_url=source_url).first()
                if existing:
                    continue

                video_details = self.get_video_details(video_id)
                duration_seconds = 0
                if video_details:
                    duration_str = video_details.get("contentDetails", {}).get("duration", "")
                    duration_seconds = self.parse_duration(duration_str)

                publish_date_str = snippet.get("publishedAt", "")
                if publish_date_str:
                    publish_date = datetime.fromisoformat(publish_date_str.replace("Z", "+00:00"))
                else:
                    publish_date = datetime.now(timezone.utc)

                content = Content(
                    source_name=channel_name,
                    source_url=source_url,
                    content_type=ContentType.VIDEO,
                    title=snippet.get("title", "Untitled"),
                    author=snippet.get("channelTitle"),
                    publish_date=publish_date,
                    raw_content=snippet.get("description", ""),
                    duration_seconds=duration_seconds,
                    entities=json.dumps({
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    }),
                    processed=False,
                )

                session.add(content)
                collected.append(content)
                logger.info("video_collected", title=content.title, channel=channel_name)

            session.commit()

        return collected

    def collect_all(self, channels: list[dict[str, str]]) -> list[Content]:
        all_collected = []
        for channel in channels:
            collected = self.collect_from_channel(channel["name"], channel["channel_id"])
            all_collected.extend(collected)
        logger.info("youtube_collection_complete", total_videos=len(all_collected))
        return all_collected
