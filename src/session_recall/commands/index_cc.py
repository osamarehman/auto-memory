"""cc-index command — build or update the Claude Code session index."""
import sys
from ..util.format_output import output


def run(args) -> int:
    try:
        from ..backends.claude_code.index import build_index, INDEX_PATH
        from ..backends.claude_code.detect import CC_PROJECTS_DIR
    except ImportError as e:
        print(f"error: Claude Code backend unavailable: {e}", file=sys.stderr)
        return 1

    if getattr(args, "status", False):
        exists = INDEX_PATH.exists()
        projects_exist = CC_PROJECTS_DIR.exists()
        data = {
            "index_path": str(INDEX_PATH),
            "index_exists": exists,
            "projects_dir": str(CC_PROJECTS_DIR),
            "projects_dir_exists": projects_exist,
        }
        if exists:
            import sqlite3
            try:
                conn = sqlite3.connect(str(INDEX_PATH))
                row = conn.execute("SELECT COUNT(*) as n FROM cc_sessions").fetchone()
                data["indexed_sessions"] = row[0] if row else 0
                conn.close()
            except Exception:
                data["indexed_sessions"] = "unknown"
        output(data, json_mode=getattr(args, "json", False))
        return 0

    rebuild = getattr(args, "rebuild", False)
    print(f"{'Rebuilding' if rebuild else 'Updating'} Claude Code session index...", file=sys.stderr)

    stats = build_index(rebuild=rebuild, verbose=True)
    data = {
        "indexed": stats["indexed"],
        "skipped": stats["skipped"],
        "total_files": stats["total"],
        "index_path": str(INDEX_PATH),
    }
    output(data, json_mode=getattr(args, "json", False))
    return 0
