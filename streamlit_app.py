import streamlit as st
from app.graph import SupportMultiAgent
from app.logger import logger

st.set_page_config(page_title="Customer Support Multi-Agent", layout="wide")
st.title("Customer Support Multi-Agent System")
st.caption("Ask questions over SQL customer data and policy PDFs")

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

query = st.text_area("Enter your question", value=st.session_state.get("query", ""), height=120)
logger.debug(f"User query: {query}")

if st.button("Run") and query.strip():
    with st.spinner("Thinking..."):
        result = agent.run(query)

    st.subheader("Answer")
    st.write(result["final_answer"])

    with st.expander("Execution details"):
        st.json({
            "intent": result.get("intent"),
            "tools_called": result.get("tools_called"),
            "sql_result": result.get("sql_result"),
            "policy_result": result.get("policy_result"),
        })
