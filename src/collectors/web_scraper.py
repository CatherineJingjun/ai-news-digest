from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from src.storage import Content, ContentType, SessionLocal

logger = structlog.get_logger()


class WebScraper:
    def __init__(self, auth_cookies: Optional[dict] = None):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.client = httpx.Client(timeout=30.0, follow_redirects=True, headers=headers)
        if auth_cookies:
            self.client.cookies.update(auth_cookies)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_page(self, url: str) -> str:
        response = self.client.get(url)
        response.raise_for_status()
        return response.text

    def extract_article_content(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = ""
        if soup.title:
            title = soup.title.string or ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", title)

        author = ""
        author_meta = soup.find("meta", {"name": "author"})
        if author_meta:
            author = author_meta.get("content", "")
        author_tag = soup.find(class_=lambda x: x and "author" in x.lower() if x else False)
        if author_tag and not author:
            author = author_tag.get_text(strip=True)

        publish_date = None
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            try:
                publish_date = datetime.fromisoformat(
                    time_tag["datetime"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        article = soup.find("article")
        if article:
            content = article.get_text(separator="\n", strip=True)
        else:
            main = soup.find("main") or soup.find(class_="content") or soup.find(id="content")
            if main:
                content = main.get_text(separator="\n", strip=True)
            else:
                paragraphs = soup.find_all("p")
                content = "\n".join(p.get_text(strip=True) for p in paragraphs)

        return {
            "title": title,
            "author": author,
            "publish_date": publish_date or datetime.now(timezone.utc),
            "content": content[:50000],  # Limit content size
        }

    def scrape_article(self, url: str, source_name: str) -> Optional[Content]:
        logger.info("scraping_article", url=url, source=source_name)

        with SessionLocal() as session:
            existing = session.query(Content).filter_by(source_url=url).first()
            if existing:
                logger.info("article_exists", url=url)
                return None

        try:
            html = self.fetch_page(url)
            extracted = self.extract_article_content(html, url)

            content = Content(
                source_name=source_name,
                source_url=url,
                content_type=ContentType.ARTICLE,
                title=extracted["title"],
                author=extracted["author"],
                publish_date=extracted["publish_date"],
                raw_content=extracted["content"],
                processed=False,
            )

            with SessionLocal() as session:
                session.add(content)
                session.commit()
                session.refresh(content)

            logger.info("article_scraped", title=content.title, url=url)
            return content

        except Exception as e:
            logger.error("scrape_failed", url=url, error=str(e))
            return None

    def scrape_articles(self, urls: list[tuple[str, str]]) -> list[Content]:
        collected = []
        for url, source_name in urls:
            content = self.scrape_article(url, source_name)
            if content:
                collected.append(content)
        return collected

    def close(self):
        self.client.close()
