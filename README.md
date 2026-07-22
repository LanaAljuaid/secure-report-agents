# Secure AI Report Agents
 
A multi-agent AI system that turns a topic into a fully researched, written,
and edited report — protected by a Security Agent that screens every
request for prompt-injection attempts before it reaches any other agent.
 
The project has three layers:
- **Agent pipeline** (LangGraph) — does the actual work
- **API** (FastAPI) — exposes the pipeline over HTTP
- **Frontend** (Streamlit) — a UI that talks to the API
## How it works
 
```
User types a topic in Streamlit
        │
        ▼
Streamlit sends a POST request to the FastAPI backend
        │
        ▼
FastAPI runs the LangGraph pipeline:
 
   Security Agent  →  screens the topic for prompt-injection attempts
        │
        ├── blocked  →  pipeline stops, returns a blocked status
        │
        └── approved
                │
                ▼
        Research Agent   → searches the web (Tavily)
                │
                ▼
        Summarization Agent → condenses the research
                │
                ▼
        Writing Agent    → drafts a structured report
                │
                ▼
        Review Agent     → polishes it into the final report
        │
        ▼
FastAPI returns the result as JSON
        │
        ▼
Streamlit displays it (green = approved, red = blocked)
```
 
## Project files
 
| File | Purpose |
|---|---|
| `security.py` | Pattern-matching guard against prompt-injection / jailbreak attempts |
| `agent_report.py` | The five agents + the LangGraph pipeline (`report_manager`). Also runnable standalone as a CLI script. |
| `api.py` | FastAPI backend. Imports the pipeline from `agent_report.py` and exposes it as `POST /generate-report` |
| `streamlit_app.py` | Web UI. Pure frontend — sends HTTP requests to the API, contains no agent logic |
| `Dockerfile` / `.dockerignore` | Packages the backend (API) into a container |
| `requirements.txt` | Backend dependencies |
| `requirements-streamlit.txt` | Frontend-only dependencies |
| `.env` (not committed) | Your API keys |
 
## Requirements
 
- Python 3.11+ (or Docker Desktop, if running the backend in a container)
- A free [Groq API key](https://console.groq.com/keys)
- A free [Tavily API key](https://app.tavily.com)
## Setup
 
1. Clone this repository.
2. Create a `.env` file in the project root (plain text — use Notepad or
   VS Code, **not Word**):
```
   GROQ_API_KEY=your-groq-key-here
   TAVILY_API_KEY=your-tavily-key-here
```
   `.env` is git-ignored on purpose — never commit real API keys.
 
## Running it
 
### Option A — Run the backend locally, no Docker
 
```bash
pip install -r requirements.txt
# set your keys as environment variables in this terminal session, e.g.
# PowerShell: $env:GROQ_API_KEY="..."; $env:TAVILY_API_KEY="..."
uvicorn api:app --reload
```
 
The API is now live at `http://127.0.0.1:8000`. Visit
`http://127.0.0.1:8000/docs` for an interactive test page.
 
### Option B — Run the backend in Docker
 
```bash
docker build -t report-agent .
docker run --env-file .env -p 8000:8000 -v ${PWD}/output:/app/output report-agent
```
 
### Then start the frontend (either option above)
 
```bash
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```
 
Opens automatically at `http://localhost:8501`. Make sure the "FastAPI
backend URL" in the sidebar matches wherever the API is running
(`http://localhost:8000` by default).
 
### Or skip the UI and call the API directly
 
```bash
curl -X POST http://localhost:8000/generate-report \
  -H "Content-Type: application/json" \
  -d '{"topic": "The future of quantum computing"}'
```
 
### Or run just the pipeline from the terminal (no API, no UI)
 
```bash
python agent_report.py
```
 
## Security Agent
 
The Security Agent runs first in every pipeline execution and blocks
requests containing patterns like:
- "ignore previous instructions"
- "reveal system prompt"
- "jailbreak"
- "bypass security"
- "pretend to be" / "act as"
Blocked requests never reach the Research Agent — no web search or LLM
call is made, so no API credits are spent on flagged input. The API
response and Streamlit UI both reflect this with a `blocked` status
instead of a generated report.
 
**Note:** this is pattern-based detection, a reasonable first layer of
defense but not a complete security solution — it can be bypassed by
novel phrasing, typos, or other languages. A production system should
pair this with output-side checks and a hardened system prompt.
