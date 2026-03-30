import os
import json
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .models import MarketplaceRequest
from .pipeline import run_pipeline

load_dotenv()

# Rate limiting: 3 requests per IP per day
from typing import Dict, List
rate_limit_store: Dict[str, List[float]] = defaultdict(list)
DAILY_LIMIT = 3


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    day_ago = now - 86400
    # Clean old entries
    rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > day_ago]
    if len(rate_limit_store[ip]) >= DAILY_LIMIT:
        return False
    rate_limit_store[ip].append(now)
    return True


app = FastAPI(title="Marketplace Intelligence Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "marketplace-intelligence-agent"}


@app.post("/analyze")
async def analyze(request: Request, body: MarketplaceRequest):
    client_ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Daily limit reached (3 analyses per day). This is a free demo — thanks for trying it!"
            },
        )

    session_id = str(uuid.uuid4())

    async def event_stream():
        async for event in run_pipeline(
            company=body.company_name,
            marketplace_type=body.marketplace_type,
            focus_area=body.focus_area,
        ):
            payload = json.dumps({"session_id": session_id, **event})
            yield f"data: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    with open(index_path) as f:
        return HTMLResponse(content=f.read())
