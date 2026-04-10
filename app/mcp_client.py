import asyncio
import concurrent.futures
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import json

SERVER_URL = "http://127.0.0.1:8000/mcp"


async def _call_tool_async(tool_name: str, arguments: dict):
    async with streamable_http_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.content:
                raw = result.content[0].text
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return {"raw": raw}
            return {}

def call_tool(tool_name: str, arguments: dict):
    def _run():
        return asyncio.run(_call_tool_async(tool_name, arguments))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_run)
        return future.result()