"""List recent sessions for the current (or specified) repository."""
import os
import sys

from ..config import DB_PATH
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..util.detect_repo import detect_repo
from ..util.format_output import output

_QUERY_REPO = """
    SELECT s.id, s.repository, s.branch, s.summary, s.created_at, s.updated_at,
           (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.id) as turns_count,
           (SELECT COUNT(*) FROM session_files f WHERE f.session_id = s.id) as files_count
    FROM sessions s WHERE s.repository = ? AND s.created_at >= datetime('now', ?)
    ORDER BY s.created_at DESC LIMIT ?"""

_QUERY_ALL = """
    SELECT s.id, s.repository, s.branch, s.summary, s.created_at, s.updated_at,
           (SELECT COUNT(*) FROM turns t WHERE t.session_id = s.id) as turns_count,
           (SELECT COUNT(*) FROM session_files f WHERE f.session_id = s.id) as files_count
    FROM sessions s WHERE s.created_at >= datetime('now', ?)
    ORDER BY s.created_at DESC LIMIT ?"""


def run(args) -> int:
    """Execute the list subcommand. Returns exit code."""
    repo = args.repo or detect_repo()
    conn = connect_ro(DB_PATH)
    problems = schema_check(conn)
    if problems:
        print("❌ Schema drift:", file=sys.stderr)
        for p in problems:
            print(f"   - {p}", file=sys.stderr)
        conn.close()
        return 2
    limit = args.limit or 10
    days_arg = f"-{args.days or 30} days"
    if repo and repo != "all":
        rows = conn.execute(_QUERY_REPO, (repo, days_arg, limit)).fetchall()
    else:
        rows = conn.execute(_QUERY_ALL, (days_arg, limit)).fetchall()
    sessions = [
        {
            "id_short": r["id"][:8], "id_full": r["id"],
            "repository": r["repository"], "branch": r["branch"],
            "summary": r["summary"],
            "date": r["created_at"][:10] if r["created_at"] else None,
            "created_at": r["created_at"],
            "turns_count": r["turns_count"], "files_count": r["files_count"],
        }
        for r in rows
    ]
    recent_files = _recent_files(conn, repo, limit=10)
    data = {"repo": repo or "all", "count": len(sessions),
            "sessions": sessions, "recent_files": recent_files}
    output(data, json_mode=args.json)
    conn.close()
    return 0


_FILES_SQL = """SELECT sf.file_path, sf.tool_name, sf.first_seen_at, sf.session_id
FROM session_files sf JOIN sessions s ON s.id = sf.session_id
WHERE sf.file_path LIKE '%%.md'{repo_filter}
ORDER BY sf.first_seen_at DESC LIMIT ?"""


def _recent_files(conn, repo, limit=10):
    if repo and repo != "all":
        sql = _FILES_SQL.format(repo_filter=" AND s.repository = ?")
        rows = conn.execute(sql, (repo, limit)).fetchall()
    else:
        sql = _FILES_SQL.format(repo_filter="")
        rows = conn.execute(sql, (limit,)).fetchall()
    cwd = os.getcwd()
    return [{"file_path": os.path.relpath(r["file_path"], cwd)
                          if r["file_path"].startswith(cwd) else r["file_path"],
             "full_path": r["file_path"],
             "tool_name": r["tool_name"],
             "date": (r["first_seen_at"] or "")[:10],
             "session_id": r["session_id"][:8]} for r in rows]
