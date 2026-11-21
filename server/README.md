# Telemetry server — count + countries ONLY

Python stdlib only (no Flask, no dependencies). Stores **no IP** and
**no raw install_id** — only `(date, country_code, sha256(install_id))`
in SQLite `telemetry.db` next to this script.

## Run

```bash
# from the v2 package root:
TELEMETRY_TOKEN=your-secret-token python server/telemetry_server.py
# -> http://localhost:8000  (override port with PORT=9000)
```

In production put it behind HTTPS (nginx/Caddy reverse proxy) and set a
strong `TELEMETRY_TOKEN`. The default token `change-me` is only for
local testing — change it before exposing the server.

## Endpoints

| Method | Path | Notes |
|---|---|---|
| `POST` | `/ping` | Body must be exactly `{"install_id", "app_version", "platform"}`. Extra fields → `400`. Country is derived from the request IP via a free lookup (2s timeout; `unknown` if unreachable), then the IP is discarded. |
| `GET` | `/stats?token=...` | JSON `{"total_users", "users_by_country", "last_30_days"}`. Token required (`TELEMETRY_TOKEN` env, default `change-me`). |
| `GET` | `/` | Tiny HTML page: total users + table by country. No token (counts only, no personal data). |

## Wire the app to it

In the app: **Settings → Anonymous statistics** → paste
the server URL, e.g. `https://stats.example.com/ping` (note the `/ping`
path), then Save. Sending is silent and automatic (count + countries only,
at most once every 4 hours when online) — there is no checkbox or off
switch. Until a URL is set, the app sends nothing, because the
default URL is empty.

## Privacy statement

This server counts anonymous installs per country. It never stores IP
addresses, names, emails, phones, patient data, or raw install IDs, and
it never logs request IPs. `install_id` is a random UUID stored only as
a one-way sha256 hash, used solely to avoid counting the same install
twice on the same day.
