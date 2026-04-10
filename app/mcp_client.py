import asyncio
import json
import sys
import threading
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = "http://127.0.0.1:8000/mcp"


def _is_win_10054(exc: BaseException) -> bool:
    return (
        isinstance(exc, ConnectionResetError)
        and getattr(exc, "winerror", None) == 10054
    )


def _install_loop_exception_suppressor(loop: asyncio.AbstractEventLoop) -> None:
    default_handler = loop.get_exception_handler()

    def _handler(event_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        if exc and _is_win_10054(exc):
            # Suppress benign Windows socket reset noise during transport shutdown.
            return

        if default_handler is not None:
            default_handler(event_loop, context)
        else:
            event_loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


class MCPClient:
    def __init__(self, server_url: str):
        self.server_url = server_url

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

        self._transport_cm = None
        self._session_cm = None
        self._session: Optional[ClientSession] = None

        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._startup_error: Optional[Exception] = None

        self._start_background_loop()

    def _start_background_loop(self) -> None:
        def _runner():
            if sys.platform.startswith("win"):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            _install_loop_exception_suppressor(self._loop)

            try:
                self._loop.run_until_complete(self._connect())
            except Exception as exc:
                self._startup_error = exc
            finally:
                self._ready.set()

            self._loop.run_forever()

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()
        self._ready.wait()

        if self._startup_error:
            raise RuntimeError(
                f"Failed to initialize MCP client: {self._startup_error}"
            ) from self._startup_error

    async def _connect(self) -> None:
        self._transport_cm = streamable_http_client(self.server_url)
        read, write, _ = await self._transport_cm.__aenter__()

        self._session_cm = ClientSession(read, write)
        self._session = await self._session_cm.__aenter__()
        await self._session.initialize()

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._session is None:
            raise RuntimeError("MCP session is not initialized.")

        result = await self._session.call_tool(tool_name, arguments)

        if result.content:
            raw = result.content[0].text
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {"raw": raw}

        return {}

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if self._loop is None:
            raise RuntimeError("MCP client event loop is not available.")

        with self._lock:
            future = asyncio.run_coroutine_threadsafe(
                self._call_tool_async(tool_name, arguments),
                self._loop,
            )
            return future.result()

    async def _close_async(self) -> None:
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except ConnectionResetError:
                pass

        if self._transport_cm is not None:
            try:
                await self._transport_cm.__aexit__(None, None, None)
            except ConnectionResetError:
                pass

    def close(self) -> None:
        if self._loop is None:
            return

        future = asyncio.run_coroutine_threadsafe(self._close_async(), self._loop)
        try:
            future.result(timeout=5)
        except Exception:
            pass

        self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)


_client: Optional[MCPClient] = None


def _get_client() -> MCPClient:
    global _client
    if _client is None:
        _client = MCPClient(SERVER_URL)
    return _client


def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    client = _get_client()
    return client.call_tool(tool_name, arguments)


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None