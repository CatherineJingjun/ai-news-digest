import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from src.digest.generator import DigestGenerator
from src.storage import Content, ContentType, Category


class TestDigestGenerator:
    def test_format_duration_minutes(self):
        generator = DigestGenerator()
        
        assert generator.format_duration(300) == "5 min"
        assert generator.format_duration(1800) == "30 min"
        assert generator.format_duration(0) == ""
        assert generator.format_duration(None) == ""
        
    def test_format_duration_hours(self):
        generator = DigestGenerator()
        
        assert generator.format_duration(3600) == "1h 0m"
        assert generator.format_duration(5400) == "1h 30m"
        assert generator.format_duration(7200) == "2h 0m"

    def test_get_top_signal(self):
        generator = DigestGenerator()
        
        content1 = Mock()
        content1.investment_signals = {"relevance_score": 5}
        
        content2 = Mock()
        content2.investment_signals = {"relevance_score": 9}
        
        content3 = Mock()
        content3.investment_signals = {"relevance_score": 7}
        
        result = generator.get_top_signal([content1, content2, content3])
        assert result == content2

    def test_get_top_signal_no_high_relevance(self):
        generator = DigestGenerator()
        
        content1 = Mock()
        content1.investment_signals = {"relevance_score": 3}
        
        content2 = Mock()
        content2.investment_signals = {"relevance_score": 5}
        
        result = generator.get_top_signal([content1, content2])
        assert result is None

    def test_categorize_content(self):
        generator = DigestGenerator()
        
        funding_content = Mock()
        funding_content.categories = ["funding"]
        funding_content.investment_signals = {"relevance_score": 6}
        funding_content.content_type = ContentType.ARTICLE
        
        trend_content = Mock()
        trend_content.categories = ["trend"]
        trend_content.investment_signals = {"relevance_score": 5}
        trend_content.content_type = ContentType.ARTICLE
        
        technical_content = Mock()
        technical_content.categories = ["technical"]
        technical_content.investment_signals = {"relevance_score": 4}
        technical_content.content_type = ContentType.ARTICLE
        
        podcast_content = Mock()
        podcast_content.categories = ["trend"]
        podcast_content.investment_signals = {"relevance_score": 8}
        podcast_content.content_type = ContentType.PODCAST
        
        content_list = [funding_content, trend_content, technical_content, podcast_content]
        result = generator.categorize_content(content_list)
        
        assert funding_content in result["investment_signals"]
        assert trend_content in result["market_intelligence"]
        assert technical_content in result["technical"]
        assert podcast_content in result["deep_dives"]
