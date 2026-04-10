"""Minimal MCP server exposing the same tools used by the agent.
"""
from app.tools.sql_tool import lookup_customer_support_data
from app.tools.policy_tool import search_policy_knowledge
from app.logger import logger

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:
    raise RuntimeError(
        "The MCP SDK is required. Install dependencies from requirements.txt first."
    ) from exc

mcp = FastMCP("customer-support-tools")


@mcp.tool()
def sql_lookup(query: str) -> dict:
    """Lookup structured customer data and support ticket details."""
    return lookup_customer_support_data(query)


@mcp.tool()
def policy_search(query: str) -> dict:
    """Search uploaded policy PDFs and return relevant passages."""
    return search_policy_knowledge(query)


if __name__ == "__main__":
    logger.info("MCP SERVER STARTING...")
    mcp.run()
