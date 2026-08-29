"""
main.py
FastAPI entry point. Exposes PromptShield as an actual HTTP API --
this is what makes it a gateway rather than just a script. Any app
could point requests here instead of calling the LLM directly.

Run with: uvicorn main:app --reload --port 8000
"""

from dotenv import load_dotenv
load_dotenv()  # reads backend/.env so GROQ_API_KEY is available

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.gateway import process_request, get_stats, REQUEST_LOG
app = FastAPI(title="PromptShield API")

# Allow the Gradio dashboard (different port/process) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PromptRequest(BaseModel):
    prompt: str


@app.get("/")
def root():
    return {"status": "PromptShield gateway is running"}


@app.post("/analyze")
def analyze(req: PromptRequest):
    """
    Main endpoint: takes a prompt, runs it through the gateway,
    returns the full decision record (action, risk score, response, etc).
    """
    return process_request(req.prompt)


@app.get("/stats")
def stats():
    """Summary stats for the dashboard."""
    return get_stats()


@app.get("/log")
def log(limit: int = 20):
    """Most recent requests, newest first -- for the live feed on the dashboard."""
    return list(reversed(REQUEST_LOG[-limit:]))
