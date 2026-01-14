import json
from typing import Optional

import structlog

try:
    import anthropic
except ImportError:
    anthropic = None

from src.config import settings
from src.storage import Category, Content, ContentType, SessionLocal

logger = structlog.get_logger()

ARTICLE_PROMPT = """Analyze this article about enterprise AI/tech and provide:

1. SUMMARY: A 3-5 sentence executive summary focused on what matters for enterprise AI investment.

2. ENTITIES: Extract key entities in JSON format:
   - companies: List of company names mentioned
   - people: List of people mentioned with their roles if known
   - funding: Any funding details (amount, stage, investors)
   - technologies: Key technologies or products mentioned

3. CATEGORIES: Classify into one or more categories:
   - funding: Funding announcements
   - product_launch: New product or feature launches
   - m_and_a: Mergers, acquisitions, partnerships
   - regulatory: Policy or regulatory developments
   - talent: Executive hires, departures, team changes
   - technical: Technical breakthroughs, research
   - trend: Emerging market or technology trends

4. INVESTMENT_SIGNALS: Rate investment relevance (1-10) and explain why this matters for enterprise AI investors.

Article Title: {title}
Source: {source}

Content:
{content}

Respond in JSON format:
{{
  "summary": "...",
  "entities": {{"companies": [], "people": [], "funding": {{}}, "technologies": []}},
  "categories": [],
  "investment_signals": {{"relevance_score": 0, "rationale": "..."}}
}}"""

PODCAST_PROMPT = """Analyze this podcast transcript about enterprise AI/tech and provide:

1. SUMMARY: 5-7 bullet points covering the key discussion topics, with guest context.

2. KEY_TIMESTAMPS: Important moments in the conversation (use segment timestamps if available).

3. ENTITIES: Extract in JSON format:
   - companies: Companies discussed
   - people: People mentioned (especially guest details)
   - investors: Investors or VCs mentioned
   - trends: Market trends discussed

4. CATEGORIES: Classify the main themes (funding, product_launch, m_and_a, regulatory, talent, technical, trend)

5. INVESTMENT_SIGNALS: Rate relevance (1-10) for enterprise AI investment and explain key takeaways.

Podcast Title: {title}
Source: {source}
Duration: {duration} minutes

Transcript:
{content}

Respond in JSON format:
{{
  "summary": ["bullet1", "bullet2", ...],
  "key_timestamps": [{{"time": "MM:SS", "topic": "..."}}],
  "entities": {{"companies": [], "people": [], "investors": [], "trends": []}},
  "categories": [],
  "investment_signals": {{"relevance_score": 0, "rationale": "..."}}
}}"""

VIDEO_PROMPT = """Analyze this video transcript about enterprise AI/tech and provide:

1. SUMMARY: 5-7 bullet points with key insights.

2. CONTENT_TYPE: Classify as "interview", "tutorial", "analysis", or "other".

3. KEY_TIMESTAMPS: Important moments worth linking to.

4. ENTITIES: Extract companies, people, technologies discussed.

5. INVESTMENT_SIGNALS: Rate relevance (1-10) for enterprise AI investment.

Video Title: {title}
Source: {source}
Duration: {duration} minutes

Transcript:
{content}

Respond in JSON format:
{{
  "summary": ["bullet1", "bullet2", ...],
  "content_type": "...",
  "key_timestamps": [{{"time": "MM:SS", "topic": "..."}}],
  "entities": {{"companies": [], "people": [], "technologies": []}},
  "categories": [],
  "investment_signals": {{"relevance_score": 0, "rationale": "..."}}
}}"""


class ContentSummarizer:
    def __init__(self):
        self.client = None
        if anthropic and settings.anthropic_api_key:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def _get_prompt(self, content: Content) -> str:
        text = content.transcript or content.raw_content or ""
        text = text[:30000]  # Limit for context window

        duration_mins = (content.duration_seconds or 0) // 60

        if content.content_type == ContentType.ARTICLE:
            return ARTICLE_PROMPT.format(
                title=content.title,
                source=content.source_name,
                content=text,
            )
        elif content.content_type == ContentType.PODCAST:
            return PODCAST_PROMPT.format(
                title=content.title,
                source=content.source_name,
                duration=duration_mins,
                content=text,
            )
        else:  # VIDEO
            return VIDEO_PROMPT.format(
                title=content.title,
                source=content.source_name,
                duration=duration_mins,
                content=text,
            )

    def summarize(self, content: Content) -> Optional[dict]:
        if not self.client:
            logger.error("anthropic_not_configured")
            return None

        prompt = self._get_prompt(content)

        try:
            response = self.client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.max_summary_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            result_text = response.content[0].text

            # Parse JSON from response
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    logger.error("json_parse_failed", response=result_text[:500])
                    return None

            return result

        except Exception as e:
            logger.error("summarization_failed", content_id=content.id, error=str(e))
            return None

    def process_content(self, content: Content) -> bool:
        logger.info("processing_content", content_id=content.id, title=content.title)

        result = self.summarize(content)
        if not result:
            return False

        with SessionLocal() as session:
            db_content = session.query(Content).filter_by(id=content.id).first()
            if not db_content:
                return False

            # Handle summary (can be string or list)
            summary = result.get("summary", "")
            if isinstance(summary, list):
                summary = "\n".join(f"• {item}" for item in summary)
            db_content.summary = summary

            # Extract categories (store as JSON string)
            categories = result.get("categories", [])
            db_content.categories = json.dumps(categories)

            # Store entities (as JSON string)
            existing_entities = json.loads(db_content.entities) if db_content.entities else {}
            existing_entities.update(result.get("entities", {}))
            if result.get("key_timestamps"):
                existing_entities["key_timestamps"] = result["key_timestamps"]
            if result.get("content_type"):
                existing_entities["video_type"] = result["content_type"]
            db_content.entities = json.dumps(existing_entities)

            # Store investment signals (as JSON string)
            db_content.investment_signals = json.dumps(result.get("investment_signals", {}))

            db_content.processed = True
            session.commit()

        logger.info("content_processed", content_id=content.id)
        return True

    def process_unprocessed(self, limit: int = 50) -> int:
        with SessionLocal() as session:
            unprocessed = (
                session.query(Content)
                .filter_by(processed=False)
                .order_by(Content.publish_date.desc())
                .limit(limit)
                .all()
            )

        processed_count = 0
        for content in unprocessed:
            if self.process_content(content):
                processed_count += 1

        logger.info("batch_processing_complete", processed=processed_count, total=len(unprocessed))
        return processed_count
