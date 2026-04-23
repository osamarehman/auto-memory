"""MCP tool server for session-recall (stdio transport)."""
from __future__ import annotations

_IMPORT_ERROR_MSG = (
    "MCP support requires the 'mcp' package.\n"
    "Install with: pip install \"auto-memory[mcp]\""
)

try:
    from mcp.server.fastmcp import FastMCP
    _mcp_available = True
except ImportError:
    _mcp_available = False

from .backends import get_backend


def build_server(backend_name: str | None = None) -> "FastMCP":
    """Create FastMCP server and register session-recall tools."""
    if not _mcp_available:
        raise ImportError(_IMPORT_ERROR_MSG)

    srv = FastMCP("session-recall")

    @srv.tool()
    def session_list(
        backend: str | None = None,
        repo: str | None = None,
        limit: int = 10,
        days: int = 30,
    ) -> dict:
        """List recent sessions."""
        b = get_backend(backend or backend_name)
        data = b.list_sessions(repo=repo, limit=limit, days=days)
        return {"repo": repo or "all", "count": len(data), "sessions": data}

    @srv.tool()
    def session_search(
        query: str,
        backend: str | None = None,
        repo: str | None = None,
        limit: int = 10,
        days: int = 30,
    ) -> dict:
        """Full-text search across sessions."""
        b = get_backend(backend or backend_name)
        data = b.search(query, repo=repo, limit=limit, days=days)
        return {"query": query, "count": len(data), "results": data}

    @srv.tool()
    def session_show(
        session_id: str,
        backend: str | None = None,
        turns: int | None = None,
    ) -> dict:
        """Show full detail for a single session."""
        b = get_backend(backend or backend_name)
        result = b.show_session(session_id, turns=turns)
        if result is None:
            raise ValueError(f"session not found: {session_id}")
        return result

    return srv


def run_stdio(backend_name: str | None = None) -> None:
    """Start MCP server on stdio transport."""
    build_server(backend_name).run(transport="stdio")
