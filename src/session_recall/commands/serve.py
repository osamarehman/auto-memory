"""serve command — start MCP tool server."""
import sys

from ..mcp_server import _IMPORT_ERROR_MSG


def run(args) -> int:
    backend_name = getattr(args, "backend", None)
    try:
        from ..mcp_server import run_stdio
    except ImportError:
        print(_IMPORT_ERROR_MSG, file=sys.stderr)
        return 1
    try:
        run_stdio(backend_name)
        return 0
    except ImportError:
        print(_IMPORT_ERROR_MSG, file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
