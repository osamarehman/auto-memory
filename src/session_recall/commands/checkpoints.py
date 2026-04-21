"""List recent checkpoints with session context."""
import sys
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..config import DB_PATH
from ..util.detect_repo import detect_repo
from ..util.format_output import output

_BASE = """SELECT c.checkpoint_number, c.title, c.overview, c.created_at,
           c.session_id, s.summary as session_summary FROM checkpoints c
           JOIN sessions s ON s.id = c.session_id"""


def run(args) -> int:
    conn = connect_ro(DB_PATH)
    problems = schema_check(conn)
    if problems:
        for p in problems:
            print(f"   - {p}", file=sys.stderr)
        conn.close()
        return 2
    repo = getattr(args, 'repo', None) or detect_repo()
    limit = getattr(args, 'limit', None) or 5
    days = getattr(args, 'days', None)
    date_filter = " AND c.created_at >= datetime('now', ?)" if days else ""
    date_param = (f"-{days} days",) if days else ()
    if repo and repo != "all":
        sql = _BASE + f" WHERE s.repository = ?{date_filter} ORDER BY c.created_at DESC LIMIT ?"
        rows = conn.execute(sql, (repo, *date_param, limit)).fetchall()
    else:
        where = f" WHERE 1=1{date_filter}" if days else ""
        sql = _BASE + where + " ORDER BY c.created_at DESC LIMIT ?"
        rows = conn.execute(sql, (*date_param, limit)).fetchall()
    checkpoints = [{
        "checkpoint_number": r["checkpoint_number"], "title": r["title"],
        "overview": (r["overview"] or "")[:300], "date": (r["created_at"] or "")[:10],
        "session_id": r["session_id"][:8], "session_summary": r["session_summary"],
    } for r in rows]
    output({"repo": repo or "all", "count": len(checkpoints), "checkpoints": checkpoints},
           json_mode=getattr(args, 'json', False))
    conn.close()
    return 0
