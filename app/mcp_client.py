import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import types as mcp_types


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _server_path() -> str:
    return str(_project_root() / "app" / "mcp_server.py")


def _python_command() -> str:
    return sys.executable


async def _call_tool_async(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    server_params = StdioServerParameters(
        command=_python_command(),
        args=[_server_path()],
        env=dict(os.environ),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(tool_name, arguments)

            if getattr(result, "isError", False):
                error_texts = []
                for item in result.content:
                    if isinstance(item, mcp_types.TextContent):
                        error_texts.append(item.text)
                raise RuntimeError(
                    f"MCP tool '{tool_name}' failed: {' | '.join(error_texts) if error_texts else 'Unknown error'}"
                )

            # Best case: structured JSON-like tool output
            if hasattr(result, "structuredContent") and result.structuredContent:
                return dict(result.structuredContent)

            # Fallback: parse text content as JSON if possible
            text_parts = []
            for item in result.content:
                if isinstance(item, mcp_types.TextContent):
                    text_parts.append(item.text)

            joined = "\n".join(text_parts).strip()
            if joined:
                try:
                    parsed = json.loads(joined)
                    if isinstance(parsed, dict):
                        return parsed
                    return {"result": parsed}
                except json.JSONDecodeError:
                    return {"result_text": joined}

            return {}


def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(_call_tool_async(tool_name, arguments))