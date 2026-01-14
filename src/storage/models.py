from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ContentType(str, Enum):
    ARTICLE = "article"
    PODCAST = "podcast"
    VIDEO = "video"


class Category(str, Enum):
    FUNDING = "funding"
    PRODUCT_LAUNCH = "product_launch"
    MA = "m_and_a"
    REGULATORY = "regulatory"
    TALENT = "talent"
    TECHNICAL = "technical"
    TREND = "trend"


class Content(Base):
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(String(2048), unique=True)
    content_type: Mapped[ContentType] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    publish_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    entities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    investment_signals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    duration_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    processed: Mapped[bool] = mapped_column(default=False)
    included_in_digest: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_content_publish_date", "publish_date"),
        Index("ix_content_content_type", "content_type"),
        Index("ix_content_processed", "processed"),
    )


class Conference(Base):
    __tablename__ = "conferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    registration_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    quarter: Mapped[str] = mapped_column(String(10))  # e.g., "Q1 2025"
    highlights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_conferences_start_date", "start_date"),)


class Digest(Base):
    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), unique=True)
    content_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    top_signal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    html_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    focus_areas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    stage_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    geography: Mapped[str] = mapped_column(String(50), default="US")
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
