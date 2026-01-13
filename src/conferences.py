from datetime import datetime, timezone
from typing import Optional

import structlog

from src.storage import Conference, SessionLocal

logger = structlog.get_logger()

# Default major AI/tech conferences
DEFAULT_CONFERENCES = [
    # Q1
    {
        "name": "CES",
        "start_date": "2025-01-07",
        "end_date": "2025-01-10",
        "location": "Las Vegas, NV",
        "website": "https://www.ces.tech/",
        "quarter": "Q1 2025",
    },
    {
        "name": "SXSW",
        "start_date": "2025-03-07",
        "end_date": "2025-03-15",
        "location": "Austin, TX",
        "website": "https://www.sxsw.com/",
        "quarter": "Q1 2025",
    },
    # Q2
    {
        "name": "Google I/O",
        "start_date": "2025-05-14",
        "end_date": "2025-05-15",
        "location": "Mountain View, CA",
        "website": "https://io.google/",
        "quarter": "Q2 2025",
    },
    {
        "name": "Microsoft Build",
        "start_date": "2025-05-19",
        "end_date": "2025-05-21",
        "location": "Seattle, WA",
        "website": "https://build.microsoft.com/",
        "quarter": "Q2 2025",
    },
    # Q3
    {
        "name": "Dreamforce",
        "start_date": "2025-09-16",
        "end_date": "2025-09-18",
        "location": "San Francisco, CA",
        "website": "https://www.salesforce.com/dreamforce/",
        "quarter": "Q3 2025",
    },
    {
        "name": "TechCrunch Disrupt",
        "start_date": "2025-09-29",
        "end_date": "2025-10-01",
        "location": "San Francisco, CA",
        "website": "https://techcrunch.com/events/disrupt/",
        "quarter": "Q3 2025",
    },
    # Q4
    {
        "name": "AWS re:Invent",
        "start_date": "2025-12-01",
        "end_date": "2025-12-05",
        "location": "Las Vegas, NV",
        "website": "https://reinvent.awsevents.com/",
        "quarter": "Q4 2025",
    },
    {
        "name": "NeurIPS",
        "start_date": "2025-12-08",
        "end_date": "2025-12-14",
        "location": "Vancouver, BC",
        "website": "https://neurips.cc/",
        "quarter": "Q4 2025",
    },
]


def seed_conferences():
    with SessionLocal() as session:
        for conf_data in DEFAULT_CONFERENCES:
            existing = (
                session.query(Conference)
                .filter_by(name=conf_data["name"], quarter=conf_data["quarter"])
                .first()
            )
            if existing:
                continue

            conference = Conference(
                name=conf_data["name"],
                start_date=datetime.strptime(conf_data["start_date"], "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                ),
                end_date=(
                    datetime.strptime(conf_data["end_date"], "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                    if conf_data.get("end_date")
                    else None
                ),
                location=conf_data.get("location"),
                website=conf_data.get("website"),
                quarter=conf_data["quarter"],
            )
            session.add(conference)

        session.commit()
        logger.info("conferences_seeded")


def add_conference(
    name: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    location: Optional[str] = None,
    website: Optional[str] = None,
    registration_deadline: Optional[datetime] = None,
) -> Conference:
    quarter_num = (start_date.month - 1) // 3 + 1
    quarter = f"Q{quarter_num} {start_date.year}"

    with SessionLocal() as session:
        conference = Conference(
            name=name,
            start_date=start_date,
            end_date=end_date,
            location=location,
            website=website,
            registration_deadline=registration_deadline,
            quarter=quarter,
        )
        session.add(conference)
        session.commit()
        session.refresh(conference)
        logger.info("conference_added", name=name, quarter=quarter)
        return conference


def get_upcoming_conferences(days: int = 90) -> list[Conference]:
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    with SessionLocal() as session:
        conferences = (
            session.query(Conference)
            .filter(Conference.start_date >= now)
            .filter(Conference.start_date <= cutoff)
            .order_by(Conference.start_date)
            .all()
        )
        session.expunge_all()
        return conferences


def get_current_quarter_conferences() -> list[Conference]:
    now = datetime.now(timezone.utc)
    quarter_num = (now.month - 1) // 3 + 1
    quarter = f"Q{quarter_num} {now.year}"

    with SessionLocal() as session:
        conferences = (
            session.query(Conference)
            .filter_by(quarter=quarter)
            .order_by(Conference.start_date)
            .all()
        )
        session.expunge_all()
        return conferences
