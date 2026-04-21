"""Full-text search across session turns and summaries."""
import re
import sys
from ..db.connect import connect_ro
from ..db.schema_check import schema_check
from ..config import DB_PATH
from ..util.detect_repo import detect_repo
from ..util.format_output import output

_SQL = """SELECT si.content, si.session_id, si.source_type,
       s.summary, s.created_at, s.repository
FROM search_index si JOIN sessions s ON s.id = si.session_id
WHERE search_index MATCH ?{repo_filter} ORDER BY rank LIMIT ?"""

_FILE_SQL = """SELECT sf.file_path, sf.session_id, sf.tool_name, sf.first_seen_at,
       s.summary, s.created_at, s.repository
FROM session_files sf JOIN sessions s ON s.id = sf.session_id
WHERE sf.file_path LIKE ?{repo_filter}
ORDER BY sf.first_seen_at DESC LIMIT ?"""

# FTS5 special chars that cause syntax errors when unquoted
_FTS5_SPECIAL = re.compile(r'[.\-(){}[\]^~*:"+/\\@#$%&!?<>=|]')


def sanitize_fts5_query(raw: str) -> str | None:
    """Escape FTS5 special characters and add prefix matching.

    Returns None for empty/whitespace-only queries.
    Strategy: split on whitespace, quote each token that contains
    special chars, append * for prefix matching on every token.
    """
    stripped = raw.strip()
    if not stripped:
        return None
    tokens = stripped.split()
    safe_tokens = []
    for tok in tokens:
        # Escape internal double quotes
        escaped = tok.replace('"', '""')
        if _FTS5_SPECIAL.search(tok):
            # Quote the whole token to treat special chars as literals
            safe_tokens.append(f'"{escaped}"')
        else:
            # Bare token with prefix wildcard for partial matching
            safe_tokens.append(f'{escaped}*')
    return " ".join(safe_tokens)


def run(args) -> int:
    conn = connect_ro(DB_PATH)
    problems = schema_check(conn)
    if problems:
        for p in problems:
            print(f"   - {p}", file=sys.stderr)
        conn.close()
        return 2
    raw_query = args.query
    repo = getattr(args, 'repo', None) or detect_repo()
    limit = getattr(args, 'limit', None) or 5
    days = getattr(args, 'days', None)
    has_repo = repo and repo != "all"
    date_clause = " AND s.created_at >= datetime('now', ?)" if days else ""
    date_param = (f"-{days} days",) if days else ()

    fts_query = sanitize_fts5_query(raw_query)
    if fts_query is None:
        data = {"query": raw_query, "repo": repo or "all", "count": 0, "results": [],
                "warning": "Empty query — nothing to search"}
        output(data, json_mode=getattr(args, 'json', False))
        conn.close()
        return 0

    if has_repo:
        sql = _SQL.format(repo_filter=" AND s.repository = ?" + date_clause)
        rows = conn.execute(sql, (fts_query, repo, *date_param, limit)).fetchall()
    else:
        sql = _SQL.format(repo_filter=date_clause)
        rows = conn.execute(sql, (fts_query, *date_param, limit)).fetchall()
    results = [{"session_id": r["session_id"][:8], "session_id_full": r["session_id"],
                "source_type": r["source_type"], "summary": r["summary"],
                "date": (r["created_at"] or "")[:10], "excerpt": (r["content"] or "")[:200]}
               for r in rows]
    seen = {(r["session_id_full"], r["source_type"]) for r in results}
    like_pat = f"%{raw_query}%"
    if has_repo:
        fsql = _FILE_SQL.format(repo_filter=" AND s.repository = ?" + date_clause)
        frows = conn.execute(fsql, (like_pat, repo, *date_param, limit)).fetchall()
    else:
        fsql = _FILE_SQL.format(repo_filter=date_clause)
        frows = conn.execute(fsql, (like_pat, *date_param, limit)).fetchall()
    for r in frows:
        if (r["session_id"], "file") in seen:
            continue
        seen.add((r["session_id"], "file"))
        results.append({"session_id": r["session_id"][:8], "session_id_full": r["session_id"],
                         "source_type": "file", "summary": r["summary"],
                         "date": (r["created_at"] or "")[:10],
                         "excerpt": f"{r['file_path']} ({r['tool_name']})"})
    results = results[:limit]
    data = {"query": raw_query, "repo": repo or "all", "count": len(results), "results": results}
    output(data, json_mode=getattr(args, 'json', False))
    conn.close()
    return 0
