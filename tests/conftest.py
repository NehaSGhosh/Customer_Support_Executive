import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_mcp_stubs() -> None:
    if "mcp" in sys.modules:
        return

    mcp_mod = types.ModuleType("mcp")

    class DummyClientSession:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def initialize(self):
            return None

        async def call_tool(self, *_args, **_kwargs):
            class _Result:
                content = []

            return _Result()

    mcp_mod.ClientSession = DummyClientSession
    sys.modules["mcp"] = mcp_mod

    mcp_client_mod = types.ModuleType("mcp.client")
    mcp_stream_mod = types.ModuleType("mcp.client.streamable_http")

    class DummyTransport:
        async def __aenter__(self):
            return (None, None, None)

        async def __aexit__(self, *_args):
            return None

    def streamable_http_client(*_args, **_kwargs):
        return DummyTransport()

    mcp_stream_mod.streamable_http_client = streamable_http_client
    sys.modules["mcp.client"] = mcp_client_mod
    sys.modules["mcp.client.streamable_http"] = mcp_stream_mod

    mcp_server_mod = types.ModuleType("mcp.server")
    mcp_fastmcp_mod = types.ModuleType("mcp.server.fastmcp")

    class DummyFastMCP:
        def __init__(self, *_args, **_kwargs):
            pass

        def tool(self):
            def _decorator(fn):
                return fn

            return _decorator

        def run(self, *_args, **_kwargs):
            return None

    mcp_fastmcp_mod.FastMCP = DummyFastMCP
    sys.modules["mcp.server"] = mcp_server_mod
    sys.modules["mcp.server.fastmcp"] = mcp_fastmcp_mod


def _install_psycopg2_stubs() -> None:
    if "psycopg2" in sys.modules:
        return

    psycopg2_mod = types.ModuleType("psycopg2")

    class OperationalError(Exception):
        pass

    def connect(*_args, **_kwargs):
        raise OperationalError("stubbed psycopg2 for tests")

    psycopg2_mod.OperationalError = OperationalError
    psycopg2_mod.connect = connect
    sys.modules["psycopg2"] = psycopg2_mod

    extras_mod = types.ModuleType("psycopg2.extras")

    class RealDictCursor:
        pass

    extras_mod.RealDictCursor = RealDictCursor
    sys.modules["psycopg2.extras"] = extras_mod


_install_mcp_stubs()
_install_psycopg2_stubs()
