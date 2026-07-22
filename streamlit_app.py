import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Agents Report Generator",
    page_icon="",
    layout="centered",
)

# Minimal custom styling for a cleaner, more modern look
st.markdown(
    """
    <style>
        .report-container {
            background-color: rgba(127, 127, 127, 0.08);
            border-radius: 10px;
            padding: 1.5rem;
            border: 1px solid rgba(127, 127, 127, 0.25);
        }
        .status-approved {
            color: #16a34a;
            font-weight: 600;
            font-size: 1.1rem;
        }
        .status-blocked {
            color: #dc2626;
            font-weight: 600;
            font-size: 1.1rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Configuration -- backend URL
# ---------------------------------------------------------------------------
# Kept in the sidebar (not hardcoded into the request logic) so the same
# frontend can point at localhost, a Docker container, or a deployed
# backend without editing code.
with st.sidebar:
    st.header("⚙️ Settings")
    api_base_url = st.text_input(
        "FastAPI backend URL",
        value="http://localhost:8000",
        help="Where your FastAPI server (api.py) is running.",
    )
    st.caption("Change this if your backend runs on a different host/port.")

API_ENDPOINT = f"{api_base_url.rstrip('/')}/generate-report"
REQUEST_TIMEOUT_SECONDS = 120  # report generation involves several LLM calls


# ---------------------------------------------------------------------------
# Helper: call the backend
# ---------------------------------------------------------------------------
def call_report_api(topic: str):
    """
    Send the topic to the FastAPI /generate-report endpoint.

    Returns:
        (success, data_or_error_message)
        success -- True if we got a usable JSON response back.
        data_or_error_message -- the parsed response dict, or a
        human-readable error string to display if something went wrong.
    """
    try:
        response = requests.post(
            API_ENDPOINT,
            json={"topic": topic},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.exceptions.ConnectionError:
        return False, (
            "Couldn't connect to the backend. Is the FastAPI server running? "
            f"(Tried: {API_ENDPOINT})"
        )
    except requests.exceptions.Timeout:
        return False, "The request timed out. The backend may be taking too long to respond."
    except requests.exceptions.RequestException as exc:
        return False, f"Unexpected request error: {exc}"

    if response.status_code == 422:
        return False, "The backend rejected the request (invalid input)."
    if response.status_code >= 500:
        return False, f"The backend returned a server error ({response.status_code})."
    if response.status_code != 200:
        return False, f"Unexpected response from backend (status {response.status_code})."

    return True, response.json()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(" AI Agents Report Generator")
st.caption("Multi-agent pipeline: Security → Research → Summarize → Write → Review")

# ---------------------------------------------------------------------------
# Input section -- Research Topic
# ---------------------------------------------------------------------------
st.subheader("Research Topic")
topic = st.text_input(
    label="Research Topic",
    label_visibility="collapsed",
    placeholder="e.g. The impact of AI agents on enterprise productivity in 2026",
)

generate_clicked = st.button("🚀 Generate Report", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Handle the button click
# ---------------------------------------------------------------------------
if generate_clicked:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        with st.spinner("Running the agent pipeline... this can take a minute."):
            success, result = call_report_api(topic.strip())

        if not success:
            # result is an error message string here
            st.error(f"⚠️ {result}")
        else:
            # Save to session_state so the result survives Streamlit reruns
            # (e.g. if the user interacts with something else on the page)
            st.session_state["last_result"] = result

# ---------------------------------------------------------------------------
# Display results (persisted across reruns via session_state)
# ---------------------------------------------------------------------------
if "last_result" in st.session_state:
    result = st.session_state["last_result"]

    st.divider()
    st.subheader("Security Status")

    if result["security_status"] == "blocked":
        st.markdown('<p class="status-blocked">🔴 Blocked</p>', unsafe_allow_html=True)
        st.error(result.get("blocked_reason") or "Request blocked by security policy.")
        # Per spec: do not display a report when blocked.
    else:
        st.markdown('<p class="status-approved">🟢 Approved</p>', unsafe_allow_html=True)

        st.divider()
        st.subheader("Generated Report")
        st.markdown(
            f'<div class="report-container">{result["final_report"]}</div>',
            unsafe_allow_html=True,
        )

        st.download_button(
            "⬇️ Download report (.md)",
            data=f"# Report: {result['topic']}\n\n{result['final_report']}",
            file_name="final_report.md",
            mime="text/markdown",
        )

        with st.expander("Pipeline details (research notes, summary, draft, log)"):
            st.markdown("**Research Notes**")
            st.write(result["research_notes"])
            st.markdown("**Summary**")
            st.write(result["summary"])
            st.markdown("**Draft Report**")
            st.write(result["draft_report"])
            st.markdown("**Pipeline Log**")
            for entry in result["log"]:
                st.write("-", entry)
