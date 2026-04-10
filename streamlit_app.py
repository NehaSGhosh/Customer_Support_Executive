import time

import streamlit as st

from app.graph import SupportMultiAgent
from app.logger import logger
from app.config import MIN_QUERY_LENGTH, MAX_QUERY_LENGTH

COOLDOWN_SECONDS = 5

st.set_page_config(page_title="Customer Support Multi-Agent", layout="wide")
st.title("Customer Support Multi-Agent System")
st.caption("Ask questions over SQL customer data and policy PDFs")

if "last_submit_time" not in st.session_state:
    st.session_state["last_submit_time"] = 0.0
if "is_running" not in st.session_state:
    st.session_state["is_running"] = False
if "query" not in st.session_state:
    st.session_state["query"] = ""

agent = SupportMultiAgent()

sample_queries = [
    "What is the current refund policy?",
    "Give me a quick overview of customer Rachel Moore's profile and past support ticket details.",
    "Does Michael's latest complaint qualify for refund under the current refund policy?",
]

with st.sidebar:
    st.subheader("Try examples")
    for q in sample_queries:
        if st.button(q):
            st.session_state["query"] = q

query = st.text_area(
    "Enter your question",
    value=st.session_state.get("query", ""),
    height=120,
)
st.session_state["query"] = query
logger.debug("User query received in UI")

now = time.time()
seconds_remaining = max(
    0,
    COOLDOWN_SECONDS - int(now - st.session_state["last_submit_time"]),
)

if seconds_remaining > 0:
    st.info(f"Please wait {seconds_remaining} more second(s) before submitting another request.")

run_clicked = st.button(
    "Run",
    disabled=st.session_state["is_running"] or seconds_remaining > 0,
)

if run_clicked:
    cleaned_query = query.strip()

    if not cleaned_query:
        st.warning("Please enter a question before running the app.")
    else:
        st.session_state["is_running"] = True
        try:
            with st.spinner("Thinking..."):
                if not cleaned_query or len(cleaned_query.strip()) < MIN_QUERY_LENGTH:
                    st.error("Please enter a valid question")
                if len(cleaned_query) > MAX_QUERY_LENGTH:
                    st.error("Query too long (max 1000 characters)")
                result = agent.run(cleaned_query)
                st.session_state["last_submit_time"] = time.time()

            st.subheader("Answer")
            st.write(result.get("final_answer", "No answer was generated."))

            with st.expander("Execution details"):
                st.json(
                    {
                        "intent": result.get("intent"),
                        "tools_called": result.get("tools_called"),
                        "sql_result": result.get("sql_result"),
                        "policy_result": result.get("policy_result"),
                    }
                )
        except Exception as exc:
            logger.exception("Unhandled application error while processing user request")
            st.error(
                "Something went wrong while processing your request. "
                "Please try again in a moment."
            )
            st.caption(f"Details: {exc}")
        finally:
            st.session_state["is_running"] = False