"""
API handlers for Investor Content OS
"""
import json
from datetime import datetime, timezone
from typing import Optional

import structlog

from src.storage import (
    Company,
    Content,
    ContentCompanyTag,
    ContentThemeTag,
    Lead,
    LeadAction,
    SessionLocal,
    Theme,
)

logger = structlog.get_logger()


# === Content API ===

def get_content_feed(limit: int = 50, offset: int = 0, content_type: Optional[str] = None):
    with SessionLocal() as session:
        query = session.query(Content).order_by(Content.publish_date.desc())
        if content_type and content_type != "all":
            query = query.filter(Content.content_type == content_type)
        items = query.offset(offset).limit(limit).all()
        
        result = []
        for item in items:
            # Get tags for this item
            theme_tags = session.query(ContentThemeTag).filter_by(content_id=item.id).all()
            company_tags = session.query(ContentCompanyTag).filter_by(content_id=item.id).all()
            
            theme_ids = [t.theme_id for t in theme_tags]
            company_ids = [c.company_id for c in company_tags]
            
            themes = session.query(Theme).filter(Theme.id.in_(theme_ids)).all() if theme_ids else []
            companies = session.query(Company).filter(Company.id.in_(company_ids)).all() if company_ids else []
            
            result.append({
                "id": item.id,
                "title": item.title,
                "url": item.source_url,
                "source": item.source_name,
                "type": item.content_type,
                "date": item.publish_date.strftime("%b %d, %Y"),
                "timestamp": item.publish_date.isoformat(),
                "summary": item.summary[:200] + "..." if item.summary and len(item.summary) > 200 else item.summary,
                "themes": [{"id": t.id, "name": t.name} for t in themes],
                "companies": [{"id": c.id, "name": c.name} for c in companies],
            })
        
        total = session.query(Content).count()
        return {"items": result, "total": total}


def get_content_item(content_id: int):
    with SessionLocal() as session:
        item = session.query(Content).filter_by(id=content_id).first()
        if not item:
            return None
        
        theme_tags = session.query(ContentThemeTag).filter_by(content_id=item.id).all()
        company_tags = session.query(ContentCompanyTag).filter_by(content_id=item.id).all()
        
        theme_ids = [t.theme_id for t in theme_tags]
        company_ids = [c.company_id for c in company_tags]
        
        themes = session.query(Theme).filter(Theme.id.in_(theme_ids)).all() if theme_ids else []
        companies = session.query(Company).filter(Company.id.in_(company_ids)).all() if company_ids else []
        
        return {
            "id": item.id,
            "title": item.title,
            "url": item.source_url,
            "source": item.source_name,
            "type": item.content_type,
            "date": item.publish_date.strftime("%b %d, %Y"),
            "summary": item.summary,
            "raw_content": item.raw_content[:2000] if item.raw_content else None,
            "themes": [{"id": t.id, "name": t.name} for t in themes],
            "companies": [{"id": c.id, "name": c.name} for c in companies],
        }


# === Theme API ===

def get_themes():
    with SessionLocal() as session:
        themes = session.query(Theme).order_by(Theme.name).all()
        result = []
        for t in themes:
            count = session.query(ContentThemeTag).filter_by(theme_id=t.id).count()
            result.append({
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "content_count": count,
            })
        return result


def get_theme(theme_id: int):
    with SessionLocal() as session:
        theme = session.query(Theme).filter_by(id=theme_id).first()
        if not theme:
            return None
        
        tags = session.query(ContentThemeTag).filter_by(theme_id=theme_id).all()
        content_ids = [t.content_id for t in tags]
        
        items = []
        if content_ids:
            contents = session.query(Content).filter(Content.id.in_(content_ids)).order_by(Content.publish_date.desc()).all()
            items = [{
                "id": c.id,
                "title": c.title,
                "url": c.source_url,
                "source": c.source_name,
                "type": c.content_type,
                "date": c.publish_date.strftime("%b %d, %Y"),
            } for c in contents]
        
        return {
            "id": theme.id,
            "name": theme.name,
            "description": theme.description,
            "content_count": len(items),
            "items": items,
        }


def create_theme(name: str, description: str = None):
    with SessionLocal() as session:
        existing = session.query(Theme).filter_by(name=name).first()
        if existing:
            return {"id": existing.id, "name": existing.name, "exists": True}
        
        theme = Theme(name=name, description=description)
        session.add(theme)
        session.commit()
        return {"id": theme.id, "name": theme.name, "exists": False}


def update_theme(theme_id: int, name: str = None, description: str = None):
    with SessionLocal() as session:
        theme = session.query(Theme).filter_by(id=theme_id).first()
        if not theme:
            return None
        if name:
            theme.name = name
        if description is not None:
            theme.description = description
        session.commit()
        return {"id": theme.id, "name": theme.name}


def delete_theme(theme_id: int):
    with SessionLocal() as session:
        session.query(ContentThemeTag).filter_by(theme_id=theme_id).delete()
        session.query(Theme).filter_by(id=theme_id).delete()
        session.commit()
        return True


# === Company API ===

def get_companies():
    with SessionLocal() as session:
        companies = session.query(Company).order_by(Company.name).all()
        result = []
        for c in companies:
            count = session.query(ContentCompanyTag).filter_by(company_id=c.id).count()
            lead_count = session.query(Lead).filter_by(company_id=c.id).count()
            result.append({
                "id": c.id,
                "name": c.name,
                "website": c.website,
                "status": c.status,
                "content_count": count,
                "lead_count": lead_count,
            })
        return result


def get_company(company_id: int):
    with SessionLocal() as session:
        company = session.query(Company).filter_by(id=company_id).first()
        if not company:
            return None
        
        tags = session.query(ContentCompanyTag).filter_by(company_id=company_id).all()
        content_ids = [t.content_id for t in tags]
        
        items = []
        if content_ids:
            contents = session.query(Content).filter(Content.id.in_(content_ids)).order_by(Content.publish_date.desc()).all()
            items = [{
                "id": c.id,
                "title": c.title,
                "url": c.source_url,
                "source": c.source_name,
                "type": c.content_type,
                "date": c.publish_date.strftime("%b %d, %Y"),
            } for c in contents]
        
        leads = session.query(Lead).filter_by(company_id=company_id).order_by(Lead.created_at.desc()).all()
        lead_list = [{
            "id": l.id,
            "stage": l.stage,
            "why_now": l.why_now,
            "created_at": l.created_at.strftime("%b %d, %Y"),
        } for l in leads]
        
        return {
            "id": company.id,
            "name": company.name,
            "website": company.website,
            "notes": company.notes,
            "status": company.status,
            "content_count": len(items),
            "items": items,
            "leads": lead_list,
        }


def create_company(name: str, website: str = None, status: str = "Watch"):
    with SessionLocal() as session:
        existing = session.query(Company).filter_by(name=name).first()
        if existing:
            return {"id": existing.id, "name": existing.name, "exists": True}
        
        company = Company(name=name, website=website, status=status)
        session.add(company)
        session.commit()
        return {"id": company.id, "name": company.name, "exists": False}


def update_company(company_id: int, name: str = None, website: str = None, notes: str = None, status: str = None):
    with SessionLocal() as session:
        company = session.query(Company).filter_by(id=company_id).first()
        if not company:
            return None
        if name:
            company.name = name
        if website is not None:
            company.website = website
        if notes is not None:
            company.notes = notes
        if status:
            company.status = status
        session.commit()
        return {"id": company.id, "name": company.name, "status": company.status}


def delete_company(company_id: int):
    with SessionLocal() as session:
        session.query(ContentCompanyTag).filter_by(company_id=company_id).delete()
        session.query(Lead).filter_by(company_id=company_id).delete()
        session.query(Company).filter_by(id=company_id).delete()
        session.commit()
        return True


# === Tagging API ===

def tag_content_theme(content_id: int, theme_id: int):
    with SessionLocal() as session:
        existing = session.query(ContentThemeTag).filter_by(content_id=content_id, theme_id=theme_id).first()
        if existing:
            return {"exists": True}
        
        tag = ContentThemeTag(content_id=content_id, theme_id=theme_id)
        session.add(tag)
        session.commit()
        return {"id": tag.id}


def untag_content_theme(content_id: int, theme_id: int):
    with SessionLocal() as session:
        session.query(ContentThemeTag).filter_by(content_id=content_id, theme_id=theme_id).delete()
        session.commit()
        return True


def tag_content_company(content_id: int, company_id: int):
    with SessionLocal() as session:
        existing = session.query(ContentCompanyTag).filter_by(content_id=content_id, company_id=company_id).first()
        if existing:
            return {"exists": True}
        
        tag = ContentCompanyTag(content_id=content_id, company_id=company_id)
        session.add(tag)
        session.commit()
        return {"id": tag.id}


def untag_content_company(content_id: int, company_id: int):
    with SessionLocal() as session:
        session.query(ContentCompanyTag).filter_by(content_id=content_id, company_id=company_id).delete()
        session.commit()
        return True


# === Lead API ===

def get_leads():
    with SessionLocal() as session:
        leads = session.query(Lead).order_by(Lead.updated_at.desc()).all()
        result = []
        for l in leads:
            company = session.query(Company).filter_by(id=l.company_id).first()
            content = session.query(Content).filter_by(id=l.created_from_content_id).first() if l.created_from_content_id else None
            
            result.append({
                "id": l.id,
                "company": {"id": company.id, "name": company.name} if company else None,
                "stage": l.stage,
                "why_now": l.why_now,
                "owner_note": l.owner_note,
                "source_content": {"id": content.id, "title": content.title} if content else None,
                "created_at": l.created_at.strftime("%b %d, %Y"),
                "updated_at": l.updated_at.strftime("%b %d, %Y"),
            })
        return result


def get_lead(lead_id: int):
    with SessionLocal() as session:
        lead = session.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return None
        
        company = session.query(Company).filter_by(id=lead.company_id).first()
        content = session.query(Content).filter_by(id=lead.created_from_content_id).first() if lead.created_from_content_id else None
        actions = session.query(LeadAction).filter_by(lead_id=lead_id).order_by(LeadAction.created_at.desc()).all()
        
        return {
            "id": lead.id,
            "company": {"id": company.id, "name": company.name, "website": company.website} if company else None,
            "stage": lead.stage,
            "why_now": lead.why_now,
            "owner_note": lead.owner_note,
            "source_content": {
                "id": content.id,
                "title": content.title,
                "url": content.source_url,
                "summary": content.summary,
            } if content else None,
            "actions": [{
                "id": a.id,
                "type": a.action_type,
                "content": a.content,
                "created_at": a.created_at.strftime("%b %d, %Y %H:%M"),
            } for a in actions],
            "created_at": lead.created_at.strftime("%b %d, %Y"),
            "updated_at": lead.updated_at.strftime("%b %d, %Y"),
        }


def create_lead(company_id: int, content_id: int = None, why_now: str = None):
    with SessionLocal() as session:
        lead = Lead(
            company_id=company_id,
            created_from_content_id=content_id,
            why_now=why_now,
            stage="New",
        )
        session.add(lead)
        session.commit()
        return {"id": lead.id}


def update_lead(lead_id: int, stage: str = None, why_now: str = None, owner_note: str = None):
    with SessionLocal() as session:
        lead = session.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return None
        if stage:
            lead.stage = stage
        if why_now is not None:
            lead.why_now = why_now
        if owner_note is not None:
            lead.owner_note = owner_note
        session.commit()
        return {"id": lead.id, "stage": lead.stage}


def delete_lead(lead_id: int):
    with SessionLocal() as session:
        session.query(LeadAction).filter_by(lead_id=lead_id).delete()
        session.query(Lead).filter_by(id=lead_id).delete()
        session.commit()
        return True


# === Lead Actions API ===

def create_lead_action(lead_id: int, action_type: str, content: str):
    with SessionLocal() as session:
        action = LeadAction(lead_id=lead_id, action_type=action_type, content=content)
        session.add(action)
        session.commit()
        return {"id": action.id}


def generate_questions(lead_id: int):
    """Generate diligence questions for a lead"""
    with SessionLocal() as session:
        lead = session.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return None
        
        company = session.query(Company).filter_by(id=lead.company_id).first()
        content = session.query(Content).filter_by(id=lead.created_from_content_id).first() if lead.created_from_content_id else None
        
        # Generate questions based on available info
        questions = [
            f"1. What is {company.name}'s current ARR and growth rate?",
            f"2. Who are the founders and what's their relevant background?",
            f"3. What's the competitive landscape and {company.name}'s differentiation?",
            f"4. What's the go-to-market strategy and current customer base?",
            f"5. What's the current funding status and runway?",
            f"6. What are the key technical risks or moats?",
            f"7. What's the team size and key hires needed?",
            f"8. What's the path to profitability or next milestone?",
        ]
        
        if content and content.summary:
            questions.append(f"9. Based on recent news: {content.title[:50]}... - what's the strategic implication?")
        
        if lead.why_now:
            questions.append(f"10. Follow up on 'why now': {lead.why_now[:100]}...")
        
        question_text = "\n".join(questions)
        
        action = LeadAction(lead_id=lead_id, action_type="Questions", content=question_text)
        session.add(action)
        session.commit()
        
        return {"id": action.id, "content": question_text}


def generate_outreach(lead_id: int, tone: str = "professional"):
    """Generate outreach draft for a lead"""
    with SessionLocal() as session:
        lead = session.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return None
        
        company = session.query(Company).filter_by(id=lead.company_id).first()
        content = session.query(Content).filter_by(id=lead.created_from_content_id).first() if lead.created_from_content_id else None
        
        # Generate outreach based on tone
        if tone == "warm":
            opener = f"Hi there! I came across {company.name} and was really impressed by what you're building."
        elif tone == "direct":
            opener = f"I'm reaching out because {company.name} caught my attention as a potential investment opportunity."
        else:
            opener = f"I hope this message finds you well. I wanted to reach out regarding {company.name}."
        
        hook = ""
        if content:
            hook = f"\n\nI recently saw the coverage in {content.source_name} about {content.title[:50]}... and it reinforced my interest in learning more."
        elif lead.why_now:
            hook = f"\n\n{lead.why_now}"
        
        outreach = f"""{opener}{hook}

I'm an investor focused on enterprise AI and would love to learn more about:
- Your vision for the company
- Current traction and roadmap
- How you're thinking about the next phase of growth

Would you have 20-30 minutes for a call in the coming weeks?

Best regards"""
        
        action = LeadAction(lead_id=lead_id, action_type="OutreachDraft", content=outreach)
        session.add(action)
        session.commit()
        
        return {"id": action.id, "content": outreach}


# === Search API ===

def search(query: str, limit: int = 20):
    if not query or len(query) < 2:
        return {"results": []}
    
    query_lower = f"%{query.lower()}%"
    results = []
    
    with SessionLocal() as session:
        # Search content
        contents = session.query(Content).filter(
            Content.title.ilike(query_lower)
        ).limit(limit).all()
        
        for c in contents:
            results.append({
                "type": "content",
                "id": c.id,
                "title": c.title,
                "subtitle": f"{c.source_name} - {c.publish_date.strftime('%b %d')}",
                "url": f"/content/{c.id}",
            })
        
        # Search themes
        themes = session.query(Theme).filter(
            Theme.name.ilike(query_lower)
        ).limit(10).all()
        
        for t in themes:
            results.append({
                "type": "theme",
                "id": t.id,
                "title": t.name,
                "subtitle": t.description or "Theme",
                "url": f"/themes/{t.id}",
            })
        
        # Search companies
        companies = session.query(Company).filter(
            Company.name.ilike(query_lower)
        ).limit(10).all()
        
        for c in companies:
            results.append({
                "type": "company",
                "id": c.id,
                "title": c.name,
                "subtitle": f"Status: {c.status}",
                "url": f"/companies/{c.id}",
            })
        
        # Search leads
        leads = session.query(Lead).filter(
            Lead.why_now.ilike(query_lower) | Lead.owner_note.ilike(query_lower)
        ).limit(10).all()
        
        for l in leads:
            company = session.query(Company).filter_by(id=l.company_id).first()
            results.append({
                "type": "lead",
                "id": l.id,
                "title": company.name if company else "Lead",
                "subtitle": f"Stage: {l.stage}",
                "url": f"/leads/{l.id}",
            })
    
    return {"results": results[:limit]}


# === Stats API ===

def get_stats():
    with SessionLocal() as session:
        content_count = session.query(Content).count()
        article_count = session.query(Content).filter(Content.content_type == "article").count()
        podcast_count = session.query(Content).filter(Content.content_type == "podcast").count()
        theme_count = session.query(Theme).count()
        company_count = session.query(Company).count()
        lead_count = session.query(Lead).count()
        tagged_count = session.query(ContentThemeTag).distinct(ContentThemeTag.content_id).count()
        
        return {
            "content": content_count,
            "articles": article_count,
            "podcasts": podcast_count,
            "themes": theme_count,
            "companies": company_count,
            "leads": lead_count,
            "tagged": tagged_count,
        }
