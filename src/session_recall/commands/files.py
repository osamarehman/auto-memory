"""List recently touched files with session attribution."""
import sys
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..config import DB_PATH
from ..util.detect_repo import detect_repo
from ..util.format_output import output

_BASE = """SELECT sf.file_path, sf.tool_name, sf.first_seen_at,
           sf.session_id, s.summary FROM session_files sf
           JOIN sessions s ON s.id = sf.session_id"""


def run(args) -> int:
    conn = connect_ro(DB_PATH)
    problems = schema_check(conn)
    if problems:
        for p in problems:
            print(f"   - {p}", file=sys.stderr)
        conn.close()
        return 2
    repo = getattr(args, 'repo', None) or detect_repo()
    limit = getattr(args, 'limit', None) or 10
    days = getattr(args, 'days', None)
    date_filter = " AND sf.first_seen_at >= datetime('now', ?)" if days else ""
    date_param = (f"-{days} days",) if days else ()
    if repo and repo != "all":
        sql = _BASE + f" WHERE s.repository = ?{date_filter} ORDER BY sf.first_seen_at DESC LIMIT ?"
        rows = conn.execute(sql, (repo, *date_param, limit)).fetchall()
    else:
        where = f" WHERE 1=1{date_filter}" if days else ""
        sql = _BASE + where + " ORDER BY sf.first_seen_at DESC LIMIT ?"
        rows = conn.execute(sql, (*date_param, limit)).fetchall()
    files = [{
        "file_path": r["file_path"], "tool_name": r["tool_name"],
        "date": (r["first_seen_at"] or "")[:10],
        "session_id": r["session_id"][:8], "session_summary": r["summary"],
    } for r in rows]
    output({"repo": repo or "all", "count": len(files), "files": files},
           json_mode=getattr(args, 'json', False))
    conn.close()
    return 0
