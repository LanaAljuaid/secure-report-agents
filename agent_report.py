"""
AI Agents for Report Generation
--------------------------------
Multi-agent pipeline: Research -> Summarize -> Write -> Review,
coordinated by a LangGraph "Report Manager".

Runs as a plain script (built to run inside Docker). The topic can be set
via the TOPIC environment variable, or it'll fall back to the default below.
"""

import os
from typing import TypedDict, List

from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END

from security import check_input_safety

from dotenv import load_dotenv

load_dotenv()
# ---------------------------------------------------------------------------
# 1. API keys (must be set as environment variables -- see .env.example)
# ---------------------------------------------------------------------------
def require_key(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Missing {name}. Set it as an environment variable "
            f"(see .env.example) before running this script."
        )
    return value


require_key("GROQ_API_KEY")
require_key("TAVILY_API_KEY")
print("API keys loaded successfully.")


# ---------------------------------------------------------------------------
# 2. Shared setup
# ---------------------------------------------------------------------------
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
search_tool = TavilySearch(max_results=5)


# ---------------------------------------------------------------------------
# 3. Shared state
# ---------------------------------------------------------------------------
class ReportState(TypedDict):
    topic: str                 # the subject of the report (input)
    research_notes: str        # output of the Research Agent
    summary: str                # output of the Summarization Agent
    draft_report: str           # output of the Writing Agent
    final_report: str           # output of the Review Agent
    log: List[str]              # a running log of what each agent did
    security_status: str        # "approved" or "blocked" (set by the Security Agent)
    blocked_reason: str | None  # why the request was blocked, if it was


# ---------------------------------------------------------------------------
# 4. Security Agent (runs first, before any other agent)
# ---------------------------------------------------------------------------
def security_agent(state: ReportState) -> ReportState:
    topic = state["topic"]
    print(f"[Security Agent] Screening input: {topic!r} ...")

    is_safe, reason = check_input_safety(topic)

    if is_safe:
        state["security_status"] = "approved"
        state["blocked_reason"] = None
        state["log"].append("Security Agent: input approved, no suspicious patterns found.")
    else:
        state["security_status"] = "blocked"
        state["blocked_reason"] = reason
        state["final_report"] = "[BLOCKED] Security policy violation detected."
        state["log"].append(f"Security Agent: input BLOCKED ({reason}).")

    return state


def route_after_security(state: ReportState) -> str:
    """Conditional-edge router: decide where to go after the Security Agent."""
    if state["security_status"] == "approved":
        return "research"
    return END


# ---------------------------------------------------------------------------
# 5. Research Agent
# ---------------------------------------------------------------------------
def research_agent(state: ReportState) -> ReportState:
    topic = state["topic"]
    print(f"[Research Agent] Searching the web for: {topic!r} ...")

    search_results = search_tool.invoke({"query": topic})

    raw_chunks = []
    for r in search_results.get("results", []):
        raw_chunks.append(f"Source: {r.get('title')} ({r.get('url')})\n{r.get('content')}")
    raw_text = "\n\n".join(raw_chunks) if raw_chunks else "No search results found."

    prompt = f"""You are a Research Agent. Using the raw web search results below,
produce detailed, well-organized research notes on the topic: "{topic}".

Requirements:
- Organize notes under clear subheadings.
- Include key facts, figures, and any dates or names mentioned.
- Note the source for important claims where possible.
- Do not fabricate information that isn't supported by the search results.

Raw search results:
{raw_text}
"""

    response = llm.invoke(prompt)
    state["research_notes"] = response.content
    state["log"].append("Research Agent: collected and organized research notes.")
    return state


# ---------------------------------------------------------------------------
# 6. Summarization Agent
# ---------------------------------------------------------------------------
def summarization_agent(state: ReportState) -> ReportState:
    print("[Summarization Agent] Condensing research notes ...")

    prompt = f"""You are a Summarization Agent. Condense the research notes below
into a short summary (roughly 150-250 words) that captures only the most
important points. Use bullet points where helpful.

Research notes:
{state['research_notes']}
"""

    response = llm.invoke(prompt)
    state["summary"] = response.content
    state["log"].append("Summarization Agent: produced a short summary of the research.")
    return state


# ---------------------------------------------------------------------------
# 7. Writing Agent
# ---------------------------------------------------------------------------
def writing_agent(state: ReportState) -> ReportState:
    print("[Writing Agent] Drafting the report ...")

    prompt = f"""You are a Writing Agent. Using the summary below, write a
professional report on the topic: "{state['topic']}".

Structure the report with:
1. Title
2. Introduction
3. Key Findings (use subheadings or bullet points)
4. Conclusion

Write in clear, professional prose suitable for a business or academic audience.

Summary to base the report on:
{state['summary']}
"""

    response = llm.invoke(prompt)
    state["draft_report"] = response.content
    state["log"].append("Writing Agent: generated the draft report.")
    return state


# ---------------------------------------------------------------------------
# 8. Review Agent
# ---------------------------------------------------------------------------
def review_agent(state: ReportState) -> ReportState:
    print("[Review Agent] Reviewing and polishing the draft ...")

    prompt = f"""You are a Review Agent (an experienced editor). Review the draft
report below for clarity, structure, tone, and grammar. Then produce a final,
polished version of the full report (not just a list of comments -- the
complete improved report text).

Draft report:
{state['draft_report']}
"""

    response = llm.invoke(prompt)
    state["final_report"] = response.content
    state["log"].append("Review Agent: reviewed the draft and produced the final polished report.")
    return state


# ---------------------------------------------------------------------------
# 9. Report Manager Agent -- build the graph
#    Pipeline: Security -> Research -> Summarize -> Write -> Review -> END
#    If the Security Agent blocks the input, the graph goes straight to END.
# ---------------------------------------------------------------------------
workflow = StateGraph(ReportState)

workflow.add_node("security", security_agent)
workflow.add_node("research", research_agent)
workflow.add_node("summarize", summarization_agent)
workflow.add_node("write", writing_agent)
workflow.add_node("review", review_agent)

workflow.add_edge(START, "security")
workflow.add_conditional_edges(
    "security",
    route_after_security,
    {"research": "research", END: END},
)
workflow.add_edge("research", "summarize")
workflow.add_edge("summarize", "write")
workflow.add_edge("write", "review")
workflow.add_edge("review", END)

report_manager = workflow.compile()
print("Report Manager graph compiled. Pipeline: security -> research -> summarize -> write -> review")


# ---------------------------------------------------------------------------
# 9. Run the pipeline
# ---------------------------------------------------------------------------
def main():
    topic = os.environ.get(
        "TOPIC",
        "The impact of short-form video on attention spans and learning",
    )

    initial_state: ReportState = {
        "topic": topic,
        "research_notes": "",
        "summary": "",
        "draft_report": "",
        "final_report": "",
        "log": [],
        "security_status": "",
        "blocked_reason": None,
    }

    result = report_manager.invoke(initial_state)

    print("\n=== PIPELINE LOG ===")
    for entry in result["log"]:
        print("-", entry)

    if result["security_status"] == "blocked":
        print("\n" + "=" * 80)
        print("REQUEST BLOCKED BY SECURITY AGENT")
        print("=" * 80)
        print(result["final_report"])
        print(f"Reason: {result['blocked_reason']}")
        return  # nothing else ran, so nothing else to print or save

    print("\n" + "=" * 80)
    print("RESEARCH NOTES (Research Agent)")
    print("=" * 80)
    print(result["research_notes"])

    print("\n" + "=" * 80)
    print("SUMMARY (Summarization Agent)")
    print("=" * 80)
    print(result["summary"])

    print("\n" + "=" * 80)
    print("DRAFT REPORT (Writing Agent)")
    print("=" * 80)
    print(result["draft_report"])

    print("\n" + "=" * 80)
    print("FINAL POLISHED REPORT (Review Agent)")
    print("=" * 80)
    print(result["final_report"])

    # 10. Save the final report to a file (written into /app/output inside the
    # container, mapped to your host machine via a Docker volume -- see README)
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "final_report.md")
    with open(output_path, "w") as f:
        f.write(f"# Report: {topic}\n\n")
        f.write(result["final_report"])

    print(f"\nFinal report saved to {output_path}")


if __name__ == "__main__":
    main()
