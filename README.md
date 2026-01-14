# AI News Digest

Daily AI news aggregation and summarization system for enterprise AI investment.

## Setup

```bash
cp .env.example .env  # Add your API keys
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
python main.py init   # Initialize database
python main.py serve  # Start scheduler
```

## Commands

- `python main.py serve` - Run scheduler continuously
- `python main.py run` - Run full pipeline once
- `python main.py collect` - Collect content only
- `python main.py process` - Process content only
- `python main.py digest` - Generate and send digest
