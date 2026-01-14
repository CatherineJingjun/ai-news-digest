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


# === Investor Content OS Models ===

class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    website: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Watch")  # Watch, Diligence, Pass, Invest
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContentThemeTag(Base):
    __tablename__ = "content_theme_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column()
    theme_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_content_theme_content", "content_id"),
        Index("ix_content_theme_theme", "theme_id"),
    )


class ContentCompanyTag(Base):
    __tablename__ = "content_company_tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_id: Mapped[int] = mapped_column()
    company_id: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_content_company_content", "content_id"),
        Index("ix_content_company_company", "company_id"),
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column()
    created_from_content_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    why_now: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="New")  # New, Contacted, Meeting, Diligence, Done
    owner_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_leads_company", "company_id"),
        Index("ix_leads_stage", "stage"),
    )


class LeadAction(Base):
    __tablename__ = "lead_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column()
    action_type: Mapped[str] = mapped_column(String(50))  # Questions, OutreachDraft, MemoSkeleton
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_lead_actions_lead", "lead_id"),)
