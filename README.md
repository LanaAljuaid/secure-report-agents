# secure-report-agents

Multi-agent report generation pipeline with a security gate. LangGraph orchestration, FastAPI backend, Streamlit client.

```
Security → Research → Summarize → Write → Review
   │
   └─ blocked → END (no downstream calls, no LLM/API spend)
```

## Stack

| Layer | Tech |
|---|---|
| Orchestration | LangGraph (`StateGraph`) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Search | Tavily |
| API | FastAPI + Uvicorn |
| Client | Streamlit |
| Runtime | Docker (backend) |

## Structure

```
.
├── security.py              # regex-based prompt-injection guard
├── agent_report.py          # agents + graph definition, CLI entrypoint
├── api.py                   # FastAPI wrapper around report_manager
├── streamlit_app.py         # HTTP client, no agent logic
├── Dockerfile
├── requirements.txt          # backend
├── requirements-streamlit.txt
└── .env                      # not committed
```

## Env

```
GROQ_API_KEY=
TAVILY_API_KEY=
```

## Run

```bash
# backend
pip install -r requirements.txt
uvicorn api:app --reload          # :8000

# or containerized
docker build -t report-agent .
docker run --env-file .env -p 8000:8000 -v ${PWD}/output:/app/output report-agent

# client
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py    # :8501

# headless
python agent_report.py
```

## API

`POST /generate-report`

```json
// request
{ "topic": "string" }

// response
{
  "topic": "string",
  "security_status": "approved" | "blocked",
  "blocked_reason": "string | null",
  "research_notes": "string",
  "summary": "string",
  "draft_report": "string",
  "final_report": "string",
  "log": ["string"]
}
```

`GET /health` → `{"status": "ok"}`

## Security agent

Regex match against known injection/jailbreak phrasing (case-insensitive), checked before `research_agent` runs. Blocked state short-circuits the graph via conditional edge — `security_status`, `blocked_reason`, `final_report` set, no other node executes.

Pattern matching only — bypassable via novel phrasing, typos, other languages. Not a substitute for output-side filtering or a hardened system prompt.

## Notes

- `.env` git-ignored; rotate any key that's touched a chat log or public repo.
- `streamlit_app.py` not baked into the Docker image — client runs separately from the API container.
