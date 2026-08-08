import os
import sys
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

import scout
import delivery
import auto_notifier
import threading

app = FastAPI(title="AgentScout — Hacker News AI Briefing Hub")

@app.on_event("startup")
def start_background_worker():
    """Starts background Hacker News notifier loop inside web process (100% Free deployment mode)"""
    def worker_loop():
        print("[Startup] Starting AgentScout background notifier thread...")
        auto_notifier.start_notifier()
    
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailRequest(BaseModel):
    email: str
    password: Optional[str] = None
    top_n: int = 5
    live: bool = True

@app.get("/api/brief")
def get_brief(live: bool = True, top_n: int = 5):
    try:
        data = scout.run_ambient_scout(live=live, top_n=top_n)
        return {"success": True, "brief": data}
    except Exception as e:
        data = scout.run_ambient_scout(live=False, top_n=top_n)
        return {"success": True, "brief": data, "warning": str(e)}

@app.post("/api/send-email")
def send_email(req: EmailRequest):
    try:
        os.environ["AGENTSCOUT_EMAIL_TO"] = req.email
        os.environ["AGENTSCOUT_EMAIL_FROM"] = req.email
        if req.password:
            os.environ["AGENTSCOUT_SMTP_PASSWORD"] = req.password

        brief = scout.run_ambient_scout(live=req.live, top_n=req.top_n)
        result = delivery.send_brief(brief)
        
        return {
            "success": result.get("sent", False),
            "result": result,
            "brief": brief
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Ensure proper MIME types registration for Windows compatibility
import mimetypes
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/html", ".html")

# Static web files directory
static_dir = os.path.join(os.path.dirname(__file__), "web")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/web", StaticFiles(directory=static_dir), name="web_dir")

@app.get("/index.css")
def get_css():
    css_path = os.path.join(static_dir, "index.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css", headers={"Cache-Control": "no-cache"})
    raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/app.js")
def get_js():
    js_path = os.path.join(static_dir, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript", headers={"Cache-Control": "no-cache"})
    raise HTTPException(status_code=404, detail="JS file not found")

@app.get("/index.html")
@app.get("/", response_class=HTMLResponse)
def root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html", headers={"Cache-Control": "no-cache"})
    return "<h1>AgentScout API Backend Running</h1>"

if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="root_static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8500))
    uvicorn.run("webapp:app", host="0.0.0.0", port=port)

