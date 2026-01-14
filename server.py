#!/usr/bin/env python3
"""
Investor Content OS - Web Server
Run with: python3 server.py
Then open: http://localhost:8000
"""

import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from src import api
from src.storage import init_db


class ContentOSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.directory = str(Path(__file__).parent / "web")
        super().__init__(*args, directory=self.directory, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        
        # Serve app.html for root
        if path == "/" or path == "":
            self.path = "/app.html"
            return super().do_GET()
        
        # API Routes
        if path == "/api/feed":
            filter_type = query.get("filter", ["all"])[0]
            data = api.get_content_feed(limit=50, content_type=filter_type if filter_type != "all" else None)
            return self.json_response(data)
        
        if path.startswith("/api/content/") and not "/themes" in path and not "/companies" in path:
            content_id = int(path.split("/")[-1])
            data = api.get_content_item(content_id)
            return self.json_response(data or {"error": "Not found"})
        
        if path == "/api/themes":
            data = api.get_themes()
            return self.json_response(data)
        
        if path.startswith("/api/themes/") and path.count("/") == 3:
            theme_id = int(path.split("/")[-1])
            data = api.get_theme(theme_id)
            return self.json_response(data or {"error": "Not found"})
        
        if path == "/api/companies":
            data = api.get_companies()
            return self.json_response(data)
        
        if path.startswith("/api/companies/") and path.count("/") == 3:
            company_id = int(path.split("/")[-1])
            data = api.get_company(company_id)
            return self.json_response(data or {"error": "Not found"})
        
        if path == "/api/leads":
            data = api.get_leads()
            return self.json_response(data)
        
        if path.startswith("/api/leads/") and path.count("/") == 3:
            lead_id = int(path.split("/")[-1])
            data = api.get_lead(lead_id)
            return self.json_response(data or {"error": "Not found"})
        
        if path == "/api/search":
            q = query.get("q", [""])[0]
            data = api.search(q)
            return self.json_response(data)
        
        if path == "/api/stats":
            data = api.get_stats()
            return self.json_response(data)
        
        # Fallback to static files
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_length > 0:
            raw = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw)
            except:
                pass
        
        # Theme routes
        if path == "/api/themes":
            data = api.create_theme(body.get("name", ""), body.get("description"))
            return self.json_response(data)
        
        if path.startswith("/api/themes/") and path.count("/") == 3:
            theme_id = int(path.split("/")[-1])
            data = api.update_theme(theme_id, body.get("name"), body.get("description"))
            return self.json_response(data or {"error": "Not found"})
        
        # Company routes
        if path == "/api/companies":
            data = api.create_company(body.get("name", ""), body.get("website"), body.get("status", "Watch"))
            return self.json_response(data)
        
        if path.startswith("/api/companies/") and path.count("/") == 3:
            company_id = int(path.split("/")[-1])
            data = api.update_company(company_id, body.get("name"), body.get("website"), body.get("notes"), body.get("status"))
            return self.json_response(data or {"error": "Not found"})
        
        # Tagging routes
        if "/themes/" in path and "/content/" in path:
            parts = path.split("/")
            content_id = int(parts[3])
            theme_id = int(parts[5])
            data = api.tag_content_theme(content_id, theme_id)
            return self.json_response(data)
        
        if "/companies/" in path and "/content/" in path:
            parts = path.split("/")
            content_id = int(parts[3])
            company_id = int(parts[5])
            data = api.tag_content_company(content_id, company_id)
            return self.json_response(data)
        
        # Lead routes
        if path == "/api/leads":
            data = api.create_lead(body.get("company_id"), body.get("content_id"), body.get("why_now"))
            return self.json_response(data)
        
        if path.startswith("/api/leads/") and "/questions" in path:
            lead_id = int(path.split("/")[3])
            data = api.generate_questions(lead_id)
            return self.json_response(data or {"error": "Not found"})
        
        if path.startswith("/api/leads/") and "/outreach" in path:
            lead_id = int(path.split("/")[3])
            data = api.generate_outreach(lead_id, body.get("tone", "professional"))
            return self.json_response(data or {"error": "Not found"})
        
        if path.startswith("/api/leads/") and path.count("/") == 3:
            lead_id = int(path.split("/")[-1])
            data = api.update_lead(lead_id, body.get("stage"), body.get("why_now"), body.get("owner_note"))
            return self.json_response(data or {"error": "Not found"})
        
        return self.json_response({"error": "Unknown endpoint"})

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # Theme delete
        if path.startswith("/api/themes/") and path.count("/") == 3:
            theme_id = int(path.split("/")[-1])
            api.delete_theme(theme_id)
            return self.json_response({"success": True})
        
        # Company delete
        if path.startswith("/api/companies/") and path.count("/") == 3:
            company_id = int(path.split("/")[-1])
            api.delete_company(company_id)
            return self.json_response({"success": True})
        
        # Lead delete
        if path.startswith("/api/leads/") and path.count("/") == 3:
            lead_id = int(path.split("/")[-1])
            api.delete_lead(lead_id)
            return self.json_response({"success": True})
        
        # Untag content-theme
        if "/content/" in path and "/themes/" in path:
            parts = path.split("/")
            content_id = int(parts[3])
            theme_id = int(parts[5])
            api.untag_content_theme(content_id, theme_id)
            return self.json_response({"success": True})
        
        # Untag content-company
        if "/content/" in path and "/companies/" in path:
            parts = path.split("/")
            content_id = int(parts[3])
            company_id = int(parts[5])
            api.untag_content_company(content_id, company_id)
            return self.json_response({"success": True})
        
        return self.json_response({"error": "Unknown endpoint"})

    def json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        # Quieter logging
        if "/api/" in args[0]:
            print(f"  API: {args[0]}")


def run_server(port=8000):
    # Initialize database and seed data
    print("\n  Initializing database...")
    init_db()
    
    print("  Seeding themes and companies...")
    from src.seed_data import seed_all
    seed_all()
    
    server = HTTPServer(("localhost", port), ContentOSHandler)
    print(f"\n  ✓ Investor Content OS running at: http://localhost:{port}\n")
    print("  Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    run_server()
