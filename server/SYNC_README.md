# ANADOCTORFADY Sync Server — خادم المزامنة

Multi-device online sync for the clinic (Phase 4). Stdlib only — no new
dependencies. **Offline-first / يعمل دون اتصال أولاً:** the app keeps working
locally and pushes/pulls when online.

> TELEMETRY_TOKEN is **not** used here (that belongs to the separate
> telemetry server). There is no activation in this project — do not re-add it.

## Run / التشغيل

```bash
# from the v2 package root:
python server/sync_server.py [--port 8001] [--db server/clinic_sync.db]
# -> http://localhost:8001   (db: server/clinic_sync.db, created on first run)
```

Default admin: **fady / 1234** — role `admin`, center `main`. Created only
when the `users` table is empty. **Safe first hosting (in this order,
on LAN only — do NOT open port 8001 to the internet before step 5):**
1. start the server, 2. log in as `fady` / `1234`, 3. create a new admin
with a strong password (`POST /users`), 4. verify the new admin login,
5. as the new admin, change `fady`'s password (`POST
/auth/change-password`) or delete `fady` (`DELETE /users/fady`).
**Password policy:** every user changes ONLY their own password
(`old_password` required); only an admin may change another user's
password (same endpoint, `username` given, no `old_password` needed).
The last remaining admin cannot be deleted. In production put the
server behind HTTPS (nginx/Caddy reverse proxy).

## Auth / المصادقة

`POST /auth/login` returns a token. Send it on every protected request as:

```
Authorization: Bearer <token>
```

Tokens are random `secrets.token_hex(32)`, kept in server memory, expiry **24h**.

## Endpoints

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| `GET` | `/health` | — | — | `{"ok": true}` |
| `POST` | `/auth/login` | — | `{"username", "password"}` | `{"ok", "token", "username", "role", "center_id"}` or `401` |
| `POST` | `/auth/change-password` | Bearer | `{"username"? (omit = self), "old_password" (self only), "new_password" (min 4)}` | `{"ok": true}` or `401` (wrong old) / `403` (non-admin changing others) / `404` (unknown user) / `400` (short password) |
| `DELETE` | `/users/<username>` | Bearer, admin | — | `{"ok": true}` or `404` (unknown) / `400` (last admin) |
| `GET` | `/sync/pull?since=<ISO>&center_id=<id>` | Bearer | — | `{"patients": [...], "visits": [...]}` with `updated_at > since`, filtered by `center_id` |
| `POST` | `/sync/push` | Bearer | `{"patients": [...], "visits": [...]}` | `{"ok": true, "applied": n}` |
| `POST` | `/attendance` | Bearer | `{"action": "in"\|"out", "device_id"}` | `{"ok": true, "ts": "<server ISO time>"}` |
| `GET` | `/attendance?center_id=&date=YYYY-MM-DD` | Bearer, admin | — | `{"entries": [{"username", "center_id", "action", "ts", "device_id"}]}` |
| `GET` | `/users` | Bearer, admin | — | `{"users": [{"id", "username", "role", "center_id", "created_at"}]}` (no password hashes) |
| `POST` | `/users` | Bearer, admin | `{"username", "password", "role", "center_id"}` | `201 {"ok", "username", "role", "center_id"}` or `409` if username exists |

All other paths → `404 {"ok": false, "error": "not found"}`.
Invalid JSON → `400`; missing/expired token → `401`; non-admin on an
admin endpoint → `403`. Extra unexpected top-level fields are ignored.
Request body is capped at **5 MB** (`413` if larger).

## Data model / نموذج البيانات

SQLite `clinic_sync.db`, tables:

- `users(id, username UNIQUE, password_hash, salt, role, center_id, created_at)` —
  passwords are SHA-256(salt + password), salt `secrets.token_hex(16)`
  (see `server/auth.py`: `hash_password`, `verify_password`,
  `create_default_admin`).
- `patients_sync(id, patient_file TEXT UNIQUE, center_id, data_json, updated_at, updated_by)`
- `visits_sync(id, record_id TEXT UNIQUE, patient_file, center_id, kind, data_json, updated_at, updated_by)`
- `attendance(id, username, center_id, action, ts, device_id)`

Push items: a patient item needs `patient_file` (plus `center_id`,
`updated_at` ISO timestamp, and either `data_json` string or the record
fields inline — the whole item is stored as JSON); a visit item needs
`record_id` (plus `patient_file`, `kind`, `center_id`, `updated_at`).
Pull returns each stored record as its parsed JSON merged with
`patient_file` / `record_id`, `center_id`, `updated_at`, `updated_by`.

## Conflict rule / قاعدة التعارض

**Last-write-wins on `updated_at`:** a pushed record overwrites the stored
one only if its `updated_at` is strictly newer; an older (or equal) push is
ignored and not counted in `applied`. Clients must therefore send a
monotonic ISO timestamp (UTC) on every change and pull with `since=` set to
the last successful pull time.

## Offline-first note / ملاحظة العمل دون اتصال

The server never holds the only copy: each device keeps its local SQLite
(`clinic.db`) as the source of truth while offline, then pushes its changes
and pulls others' changes when a connection is available. If the server is
unreachable, the app must keep working normally and retry later.

## Delta pull (round 39) / السحب التجزيئي

Since round 39 a pull no longer transfers the whole dataset. Every
sync table carries a `seq` column assigned **by the server** from a
per-table counter at write time (arrival order). The client stores
the highest seq it was served per (server, center, table) — its
watermark — and asks only for `seq > watermark`.

- Why not a timestamp watermark: `updated_at` is stamped by the
  *originating device's* clock. A PC whose clock runs behind would
  stamp new rows below other clients' watermarks and those rows
  would never be delivered. Server seq has no clock input at all;
  a late row with an old `updated_at` still gets a fresh seq and
  arrives on the next pull (last-write-wins then decides, as
  before). No overlap window is needed.
- The response carries the server's `server_id` (a uuid created
  with the server DB). A client whose stored id differs — fresh
  install, replaced or restored server DB — is served a FULL pull,
  so stale watermarks can never starve it. Counters are also
  re-raised to the table max on every ensure, so rows loaded by
  any other path (bulk load, pre-R39 restore) cannot strand the
  counter below them.
- Compatibility: requests without `server_id`/`seq_*` (pre-R39
  clients) get the legacy timestamp-filtered pull, unchanged.
  Pre-R39 servers ignore the new params and return a full pull;
  the new client stores nothing from such a response and simply
  keeps full-pulling. Mixed versions never corrupt data — worst
  case is a full transfer.
- Role filtering is unchanged; a table's watermark in the response
  is the max seq **served** to that user (a doctor's financials
  watermark never advances over other doctors' rows).
- Pulls use a 300s client timeout (all other calls stay at 5s):
  at 200k patients the one-time full pull is a ~441 MB response
  the server needs ~21–37s to generate on the test VM; steady-state
  delta pulls measured 2.7 KB / ~3 ms for 10 changed rows
  (loopback; a WAN will differ).
