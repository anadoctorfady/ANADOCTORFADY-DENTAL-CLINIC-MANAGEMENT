"""Round 39: client-side delta-sync watermarks.

One row per (server_url, center_id, table): the highest server
`seq` this client has been served for that table, plus the
server_id those watermarks belong to. The server assigns seq in
arrival order (see server/sync_helpers.py), so a watermark is a
pure position in the server's change stream — client clock skew
cannot make it skip rows the way a timestamp watermark could, and
no overlap window is needed: apply is idempotent, but with seq
nothing is re-sent in the first place.

Server identity rule: if a pull response's server_id differs from
the stored one (fresh install, replaced or restored server DB),
absorb_response REPLACES the stored watermarks with the response's
values instead of max-merging — the response to a mismatched
request is a full pull, and max-merging would keep stale high
watermarks from the old server and starve the client forever.
Against a pre-R39 server the response carries no server_id at all:
absorb_response stores nothing and every pull stays a full pull,
exactly the old behaviour."""
TABLES = ("patients", "visits", "financials", "employees", "referrals")


def ensure_state_table(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS sync_watermarks(
        server_url TEXT, center_id TEXT, table_name TEXT,
        seq INTEGER DEFAULT 0, server_id TEXT DEFAULT '',
        PRIMARY KEY(server_url, center_id, table_name))""")
    conn.commit()


def load_state(conn, server_url, center_id):
    """-> (server_id, {table: seq}) with 0 for unseen tables."""
    ensure_state_table(conn)
    marks = {t: 0 for t in TABLES}
    sid = ""
    for t, s, i in conn.execute(
            "SELECT table_name, seq, server_id FROM sync_watermarks"
            " WHERE server_url=? AND center_id=?",
            (server_url, center_id)).fetchall():
        if t in marks:
            marks[t] = s or 0
        if i:
            sid = i
    return sid, marks


def request_params(conn, server_url, center_id):
    """Query params for a delta pull: stored server_id + watermarks."""
    sid, marks = load_state(conn, server_url, center_id)
    params = {"server_id": sid}
    for t in TABLES:
        params[f"seq_{t}"] = str(marks[t])
    return params


def absorb_response(conn, server_url, center_id, res):
    """Store watermarks from a pull response. True when the response
    carried delta state (R39 server); False for a legacy server, in
    which case nothing is stored."""
    sid = res.get("server_id") if isinstance(res, dict) else None
    marks = res.get("watermarks") if isinstance(res, dict) else None
    if not sid or not isinstance(marks, dict):
        return False
    old_sid, old = load_state(conn, server_url, center_id)
    replace = sid != old_sid
    cur = conn.cursor()
    for t in TABLES:
        v = marks.get(t)
        if v is None:
            new = 0 if replace else old[t]
        else:
            new = int(v) if replace else max(old[t], int(v))
        cur.execute("INSERT OR REPLACE INTO sync_watermarks"
                    "(server_url, center_id, table_name, seq, server_id)"
                    " VALUES(?,?,?,?,?)",
                    (server_url, center_id, t, new, sid))
    conn.commit()
    return True
