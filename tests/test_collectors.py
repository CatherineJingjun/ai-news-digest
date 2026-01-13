import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.collectors.rss_collector import RSSCollector
from src.storage import ContentType


class TestRSSCollector:
    def test_determine_content_type_podcast(self):
        collector = RSSCollector()
        
        # Test podcast detection by feed name
        assert collector.determine_content_type({}, "a16z Podcast") == ContentType.PODCAST
        assert collector.determine_content_type({}, "20VC Show") == ContentType.PODCAST
        
        # Test article detection
        assert collector.determine_content_type({}, "TechCrunch") == ContentType.ARTICLE
        
        collector.close()

    def test_determine_content_type_by_enclosure(self):
        collector = RSSCollector()
        
        entry_with_audio = {
            "links": [{"type": "audio/mpeg", "href": "http://example.com/audio.mp3"}]
        }
        assert collector.determine_content_type(entry_with_audio, "Some Feed") == ContentType.PODCAST
        
        collector.close()

    def test_parse_publish_date_with_published(self):
        collector = RSSCollector()
        
        entry = MagicMock()
        entry.published_parsed = (2025, 1, 15, 10, 30, 0, 0, 0, 0)
        
        result = collector.parse_publish_date(entry)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        
        collector.close()

    def test_parse_publish_date_fallback(self):
        collector = RSSCollector()
        
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        
        result = collector.parse_publish_date(entry)
        assert result.tzinfo == timezone.utc
        
        collector.close()

    def test_extract_content_from_content_field(self):
        collector = RSSCollector()
        
        entry = MagicMock()
        entry.content = [{"value": "This is the content"}]
        
        result = collector.extract_content(entry)
        assert result == "This is the content"
        
        collector.close()

    def test_extract_content_from_summary(self):
        collector = RSSCollector()
        
        entry = MagicMock()
        entry.content = None
        entry.summary = "This is the summary"
        
        # Need to handle hasattr properly
        del entry.content
        
        result = collector.extract_content(entry)
        assert result == "This is the summary"
        
        collector.close()

    def test_get_audio_url(self):
        collector = RSSCollector()
        
        entry = {
            "enclosures": [
                {"type": "audio/mpeg", "href": "http://example.com/episode.mp3"}
            ]
        }
        
        result = collector.get_audio_url(entry)
        assert result == "http://example.com/episode.mp3"
        
        collector.close()


class TestYouTubeCollector:
    def test_parse_duration_hours_minutes_seconds(self):
        from src.collectors.youtube_collector import YouTubeCollector
        
        collector = YouTubeCollector()
        
        assert collector.parse_duration("PT1H30M45S") == 5445
        assert collector.parse_duration("PT45M30S") == 2730
        assert collector.parse_duration("PT10M") == 600
        assert collector.parse_duration("PT30S") == 30
        assert collector.parse_duration("PT2H") == 7200
        
    def test_parse_duration_invalid(self):
        from src.collectors.youtube_collector import YouTubeCollector
        
        collector = YouTubeCollector()
        
        assert collector.parse_duration("invalid") == 0
        assert collector.parse_duration("") == 0
