import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.storage import Category, Content, ContentType, Digest, SessionLocal, Conference

logger = structlog.get_logger()


def _parse_json(value: Optional[str], default=None):
    """Parse JSON string, return default if None or invalid."""
    if not value:
        return default if default is not None else {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}


class DigestGenerator:
    def __init__(self):
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def get_recent_content(self, hours: int = 24) -> list[Content]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        with SessionLocal() as session:
            content = (
                session.query(Content)
                .filter(Content.publish_date >= cutoff)
                .filter(Content.processed == True)
                .order_by(Content.publish_date.desc())
                .all()
            )
            # Detach from session
            session.expunge_all()
            return content

    def get_top_signal(self, content_list: list[Content]) -> Optional[Content]:
        scored = []
        for item in content_list:
            signals = _parse_json(item.investment_signals)
            score = signals.get("relevance_score", 0)
            if score >= 7:  # Only consider high-relevance items
                scored.append((score, item))
        
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]
        return None

    def categorize_content(self, content_list: list[Content]) -> dict:
        categorized = {
            "investment_signals": [],
            "market_intelligence": [],
            "technical": [],
            "deep_dives": [],
        }

        investment_categories = {Category.FUNDING, Category.PRODUCT_LAUNCH, Category.MA}
        market_categories = {Category.TREND, Category.REGULATORY, Category.TALENT}
        technical_categories = {Category.TECHNICAL}

        for item in content_list:
            categories = set(_parse_json(item.categories, []))
            signals = _parse_json(item.investment_signals)
            relevance = signals.get("relevance_score", 0)

            if categories & investment_categories or relevance >= 8:
                categorized["investment_signals"].append(item)
            elif categories & market_categories:
                categorized["market_intelligence"].append(item)
            elif categories & technical_categories:
                categorized["technical"].append(item)

            # Deep dives: longer content with high relevance
            if item.content_type in [ContentType.PODCAST, ContentType.VIDEO] and relevance >= 6:
                categorized["deep_dives"].append(item)

        # Limit sections
        categorized["investment_signals"] = categorized["investment_signals"][:10]
        categorized["market_intelligence"] = categorized["market_intelligence"][:8]
        categorized["technical"] = categorized["technical"][:5]
        categorized["deep_dives"] = categorized["deep_dives"][:3]

        return categorized

    def get_upcoming_conferences(self) -> list[Conference]:
        now = datetime.now(timezone.utc)
        quarter_end = now + timedelta(days=90)
        
        with SessionLocal() as session:
            conferences = (
                session.query(Conference)
                .filter(Conference.start_date >= now)
                .filter(Conference.start_date <= quarter_end)
                .order_by(Conference.start_date)
                .limit(5)
                .all()
            )
            session.expunge_all()
            return conferences

    def format_duration(self, seconds: Optional[int]) -> str:
        if not seconds:
            return ""
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}m"

    def generate_digest(self, date: Optional[datetime] = None) -> dict:
        if date is None:
            date = datetime.now(timezone.utc)

        content_list = self.get_recent_content(hours=24)
        
        article_count = sum(1 for c in content_list if c.content_type == ContentType.ARTICLE)
        podcast_count = sum(1 for c in content_list if c.content_type == ContentType.PODCAST)
        video_count = sum(1 for c in content_list if c.content_type == ContentType.VIDEO)

        top_signal = self.get_top_signal(content_list)
        categorized = self.categorize_content(content_list)
        conferences = self.get_upcoming_conferences()

        return {
            "date": date,
            "counts": {
                "articles": article_count,
                "podcasts": podcast_count,
                "videos": video_count,
                "total": len(content_list),
            },
            "top_signal": top_signal,
            "sections": categorized,
            "conferences": conferences,
        }

    def render_html(self, digest_data: dict) -> str:
        template = self.env.get_template("digest_email.html")
        return template.render(
            digest=digest_data,
            format_duration=self.format_duration,
        )

    def create_and_save_digest(self) -> Optional[Digest]:
        digest_data = self.generate_digest()
        html_content = self.render_html(digest_data)

        content_ids = [str(c.id) for section in digest_data["sections"].values() for c in section]

        with SessionLocal() as session:
            digest = Digest(
                date=digest_data["date"],
                content_ids=json.dumps(content_ids),
                top_signal=(
                    json.dumps({
                        "id": digest_data["top_signal"].id,
                        "title": digest_data["top_signal"].title,
                        "summary": digest_data["top_signal"].summary,
                    })
                    if digest_data["top_signal"]
                    else None
                ),
                html_content=html_content,
                sent=False,
            )
            session.add(digest)
            session.commit()
            session.refresh(digest)

            # Mark content as included
            for content_id in content_ids:
                content = session.query(Content).filter_by(id=int(content_id)).first()
                if content:
                    content.included_in_digest = True
            session.commit()

            logger.info("digest_created", digest_id=digest.id, items=len(content_ids))
            return digest
