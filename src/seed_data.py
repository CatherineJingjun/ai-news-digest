"""
Seed initial themes and companies for Investor Content OS
"""
from src.storage import SessionLocal, Theme, Company

INITIAL_THEMES = [
    ("AI Infrastructure", "Cloud, compute, MLOps, model serving"),
    ("Foundation Models", "LLMs, multimodal models, model training"),
    ("AI Agents", "Autonomous agents, agentic workflows, tool use"),
    ("Enterprise AI", "AI for business operations, productivity"),
    ("AI Security", "AI safety, security tools, red teaming"),
    ("Vertical AI", "Industry-specific AI applications"),
    ("Developer Tools", "Coding assistants, DevOps, testing"),
    ("Data Infrastructure", "Data pipelines, labeling, synthetic data"),
    ("Robotics & Physical AI", "Embodied AI, manipulation, autonomous systems"),
    ("Healthcare AI", "Drug discovery, diagnostics, clinical AI"),
    ("Fintech AI", "AI in finance, trading, risk"),
    ("AI Hardware", "Chips, accelerators, edge devices"),
    ("Computer Vision", "Image/video understanding, generation"),
    ("Speech & Audio", "Voice AI, transcription, generation"),
    ("AI Regulation", "Policy, compliance, governance"),
]

INITIAL_COMPANIES = [
    ("OpenAI", "https://openai.com", "Watch"),
    ("Anthropic", "https://anthropic.com", "Watch"),
    ("Mistral", "https://mistral.ai", "Watch"),
    ("Cohere", "https://cohere.com", "Watch"),
    ("Databricks", "https://databricks.com", "Watch"),
    ("Scale AI", "https://scale.com", "Watch"),
    ("Hugging Face", "https://huggingface.co", "Watch"),
    ("Anyscale", "https://anyscale.com", "Watch"),
    ("Modal", "https://modal.com", "Watch"),
    ("Weights & Biases", "https://wandb.ai", "Watch"),
    ("Pinecone", "https://pinecone.io", "Watch"),
    ("Weaviate", "https://weaviate.io", "Watch"),
    ("LangChain", "https://langchain.com", "Watch"),
    ("Cursor", "https://cursor.sh", "Watch"),
    ("Replit", "https://replit.com", "Watch"),
    ("Vercel", "https://vercel.com", "Watch"),
    ("Groq", "https://groq.com", "Watch"),
    ("Cerebras", "https://cerebras.net", "Watch"),
    ("Figure AI", "https://figure.ai", "Watch"),
    ("Covariant", "https://covariant.ai", "Watch"),
    ("Harvey", "https://harvey.ai", "Watch"),
    ("Glean", "https://glean.com", "Watch"),
    ("Writer", "https://writer.com", "Watch"),
    ("Jasper", "https://jasper.ai", "Watch"),
    ("Runway", "https://runwayml.com", "Watch"),
    ("ElevenLabs", "https://elevenlabs.io", "Watch"),
    ("Synthesia", "https://synthesia.io", "Watch"),
    ("Midjourney", "https://midjourney.com", "Watch"),
    ("Stability AI", "https://stability.ai", "Watch"),
    ("Inflection AI", "https://inflection.ai", "Watch"),
]


def seed_themes():
    with SessionLocal() as session:
        for name, description in INITIAL_THEMES:
            existing = session.query(Theme).filter_by(name=name).first()
            if not existing:
                theme = Theme(name=name, description=description)
                session.add(theme)
        session.commit()
        count = session.query(Theme).count()
        print(f"Seeded themes: {count} total")


def seed_companies():
    with SessionLocal() as session:
        for name, website, status in INITIAL_COMPANIES:
            existing = session.query(Company).filter_by(name=name).first()
            if not existing:
                company = Company(name=name, website=website, status=status)
                session.add(company)
        session.commit()
        count = session.query(Company).count()
        print(f"Seeded companies: {count} total")


def seed_all():
    seed_themes()
    seed_companies()


if __name__ == "__main__":
    seed_all()
