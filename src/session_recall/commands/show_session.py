"""Show detailed info for a single session."""
import re
import sys
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..config import DB_PATH
from ..util.format_output import output

_SID_RE = re.compile(r'^[0-9a-fA-F-]{4,}$')


def run(args) -> int:
    conn = connect_ro(DB_PATH)
    problems = schema_check(conn)
    if problems:
        for p in problems:
            print(f"   - {p}", file=sys.stderr)
        conn.close()
        return 2
    sid = args.session_id.strip()
    if not _SID_RE.match(sid) or not sid.replace('-', ''):
        print(
            f"error: invalid session id '{args.session_id}' "
            f"(expected hex, 4+ chars)",
            file=sys.stderr,
        )
        conn.close()
        return 2
    sid = sid.lower()
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? OR id LIKE ?", (sid, f"{sid}%"),
    ).fetchone()
    if not row:
        print(f"No session found matching '{sid}'", file=sys.stderr)
        conn.close()
        return 1
    full_id = row["id"]
    if getattr(args, 'turns', None) is not None:
        turns_rows = conn.execute(
            "SELECT turn_index, user_message, assistant_response, timestamp "
            "FROM turns WHERE session_id = ? ORDER BY turn_index LIMIT ?",
            (full_id, args.turns),
        ).fetchall()
    else:
        turns_rows = conn.execute(
            "SELECT turn_index, user_message, assistant_response, timestamp "
            "FROM turns WHERE session_id = ? ORDER BY turn_index",
            (full_id,),
        ).fetchall()
    mx = 99999 if getattr(args, 'full', False) else 500
    turns = [{"idx": t["turn_index"], "user": (t["user_message"] or "")[:mx],
              "assistant": (t["assistant_response"] or "")[:mx], "timestamp": t["timestamp"]}
             for t in turns_rows]
    files = [dict(f) for f in conn.execute(
        "SELECT file_path, tool_name, turn_index FROM session_files WHERE session_id = ?", (full_id,)
    ).fetchall()]
    refs = [dict(r) for r in conn.execute(
        "SELECT ref_type, ref_value, turn_index FROM session_refs WHERE session_id = ?", (full_id,)
    ).fetchall()]
    cps = [{"n": c["checkpoint_number"], "title": c["title"], "overview": (c["overview"] or "")[:300]}
           for c in conn.execute(
        "SELECT checkpoint_number, title, overview FROM checkpoints "
        "WHERE session_id = ? ORDER BY checkpoint_number", (full_id,)
    ).fetchall()]
    result = {
        "id": full_id, "repository": row["repository"], "branch": row["branch"],
        "summary": row["summary"], "created_at": row["created_at"],
        "turns_count": len(turns_rows), "turns": turns,
        "files": files, "refs": refs, "checkpoints": cps,
    }
    output(result, json_mode=getattr(args, 'json', False))
    conn.close()
    return 0
