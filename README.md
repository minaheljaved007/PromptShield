# PromptShield

A security gateway that sits between an app and an LLM API. It scans every
incoming prompt in real time for injection attempts, jailbreaks, and
sensitive-data extraction *before* the prompt reaches the model. Each
request gets a risk score — safe ones pass through, suspicious ones get
sanitized, malicious ones get blocked outright. A live dashboard shows
blocked attacks, risk levels, and attack categories as they happen.

Built for the AI Infra Summit Hackathon.

## Project structure

```
promptshield/
├── backend/
│   ├── patterns.py       # attack pattern library (the detection "brain")
│   ├── llm_client.py     # Groq API wrapper (the protected LLM)
│   ├── gateway.py        # decision logic: block / sanitize / allow
│   ├── main.py           # FastAPI server exposing it all as an API
│   ├── requirements.txt
│   └── .env.example      # copy to .env and add your real Groq key
└── frontend/
    └── dashboard.py      # Gradio dashboard for the live demo
```

## Setup (do this once)

### 1. Get a free Groq API key
Go to **console.groq.com**, sign up (free, no card), go to API Keys,
create one, copy it.

### 2. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Add your API key
```bash
cp .env.example .env
```
Then open `.env` and replace `paste_your_actual_groq_key_here` with your
real key.

## Running it (two terminals, every time)

**Terminal 1 — start the backend:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```
Leave this running. You should see `Uvicorn running on http://127.0.0.1:8000`.

**Terminal 2 — start the dashboard:**
```bash
cd frontend
python dashboard.py
```
This will print a local URL (usually `http://127.0.0.1:7860`) — open it in
your browser. That's your demo screen.

## How to demo it

1. Use the "Quick demo prompts" dropdown — it has pre-loaded safe, suspicious,
   and malicious examples so you're not typing live under pressure.
2. Show a safe prompt first (gets ALLOWED, real LLM answer comes back).
3. Show a jailbreak prompt (gets BLOCKED, LLM is never called).
4. Point at the live stats panel and category chart updating in real time.
5. Explain the three-tier decision: ALLOWED / SANITIZED / BLOCKED, and that
   this is rule-based (fast, free, fully explainable) rather than needing
   a separate ML model — which is itself a legitimate infra trade-off to
   mention if judges ask "why not use an ML classifier?"

## How the pieces fit together

```
User prompt
    │
    ▼
[patterns.py] → scans against 5 attack categories, returns risk score 0-100
    │
    ▼
[gateway.py]  → score < 30  → ALLOWED    → forwarded untouched to Groq
              → score 30-59 → SANITIZED  → cleaned, then forwarded to Groq
              → score ≥ 60  → BLOCKED    → never reaches Groq at all
    │
    ▼
[llm_client.py] → calls Groq API, returns answer + latency + token counts
    │
    ▼
[main.py]     → exposes all of this as a FastAPI HTTP API (/analyze, /stats, /log)
    │
    ▼
[dashboard.py] → Gradio UI that calls the API and renders verdict + live stats
```

## Extending it (if you have time left)

- **More attack patterns**: add entries to the lists in `patterns.py` —
  each is just a regex string, no code changes needed elsewhere.
- **Adjustable thresholds**: the 30/60 score cutoffs live in `patterns.py`
  (`is_safe`, `is_suspicious`, `is_malicious`) — easy to tune live if a demo
  prompt doesn't score the way you expect.
- **Export the log**: `/log` endpoint already returns recent requests as
  JSON — could add a CSV download button to the dashboard.
