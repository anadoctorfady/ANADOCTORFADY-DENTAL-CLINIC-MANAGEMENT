# Anonymous usage statistics / إحصاءات مجهولة

**Silent automatic mode — the owner's explicit decision.** No consent
dialog, no ask-once flow, nothing to click, and NO off switch — the
stats (count + countries only) do not affect the user or their privacy.
When the app is online it quietly sends an anonymous ping, at most once
every hour (owner decision 2026-11-21, round 40 — was every 4 hours). Offline, the app works fully — sending simply fails
silently and is retried later.

> قرار صاحب التطبيق: إحصاء مجهول تلقائي صامت، بدون أي نافذة موافقة
> وبدون زر إيقاف. عند الاتصال بالإنترنت يُرسل ping مجهول كل ساعة
> كحد أقصى، وبدون إنترنت يعمل التطبيق كاملاً دون أي مشكلة.

## What IS sent / ما الذي يُرسل

Exactly 4 fields, once every hour at most, only when online
(round 38: `country` added — before, it was exactly 3 fields and
the country never reached Firebase at all):

```json
{"install_id": "3f8a2c1e-9b4d-4e6a-8c1f-7a2b3c4d5e6f", "app_version": "2.1.0", "platform": "windows", "country": "SY"}
```

- `install_id` — a random UUID created on your PC. Not your name, phone or email.
- `app_version` — e.g. `2.1.0`.
- `platform` — always `windows`.
- `country` — ISO 3166 alpha-2 (e.g. `SY`), or `unknown`. Derived ON
  THIS MACHINE by `src/models/geo_country.py` — Windows region, then
  OS locale, then a timezone map — with NO external network calls
  and NO new permissions.

## What is NOT sent / ما الذي لا يُرسل أبداً

- ❌ No patient data (no names, files, teeth, diagnoses, money, X-rays).
- ❌ No names, emails, phone numbers, addresses.
- ✅ The payload's only location datum is the `country` code above,
  derived on-device (round 38). The optional server additionally
  falls back to deriving a country from the request IP when a
  client sends none or `unknown` (below).
- ❌ No location / GPS, no usage details (no clicks, no screens, no times).
- ❌ No IP stored — the IP is used once to look up the country, then discarded.
- ❌ No raw `install_id` stored on the server — only its sha256 hash.

## How the country is derived / كيف يُعرف البلد

The server sees the request IP (as every web server does), looks up its
country via a free IP-to-country service, stores only the 2-letter country
code (e.g. `SY`, `EG`), and immediately forgets the IP. If the lookup is
unavailable, the country is stored as `unknown`. The client never sends
its country or location.

## No off switch / لا يوجد زر إيقاف

By the owner's decision there is no toggle to turn the stats off: they
send only a count + countries, every hour when online, and do not
affect the user or their privacy in any way. The only way sending stops
is if no server URL is set (the `telemetry_url` setting left empty) —
then nothing is ever sent. Nothing else about the app changes.

## No UI field — how the owner (Fady) sets the URL / لا يوجد حقل في الواجهة

There is deliberately **no telemetry/statistics field anywhere in the
app UI** (Settings has no mention of it at all): the end user never
sees it, and the send stays silent and automatic. Only the owner sets
the URL, directly in the clinic database — no new data is collected
by doing this, it only tells the app *where* to send the same 4 fields:

```bash
# from the app folder, with the app closed:
sqlite3 anadoctorfady/clinic.db \
  "UPDATE settings SET value='https://stats.example.com/ping' WHERE key='telemetry_url';"
# or, with Python:
python -c "from src.models.telemetry import set_url; set_url('https://stats.example.com/ping')"
# to stop sending again, clear it:
python -c "from src.models.telemetry import set_url; set_url('')"
```

The app reads that stored URL on startup (`src/models/telemetry.py`
`get_url()` / `maybe_send_async()`); the value is never shown in the
UI and never leaves the device except as the destination of the ping.

## Firebase Realtime Database (owner's stats view) / قاعدة بيانات فايربيس

As well as the self-hosted server above, the app can send the **same
4 fields only** (`install_id`, `app_version`, `platform`, `country` —
nothing else) to the owner's Firebase Realtime Database, on the same schedule:
at most once every hour, only when online, silently, with no UI
presence anywhere. Each install gets one node that is refreshed every
hour, so the count of nodes is the count of installs:

```
installs/
  <install_id>/
    install_id:  "3f8a2c1e-..."
    app_version: "2.1.0"
    platform:    "windows"
```

The write is a plain REST `PUT` to
`<firebase_url>/installs/<install_id>.json` — no API key, no service
account, no auth token anywhere in the code. The server `POST` above
is untouched: when both destinations are set, both are attempted, and
a failure of one never blocks the other (each has its own last-sent
clock, so a failed destination retries next time instead of waiting
out the other's success).

### How the owner views the numbers / كيف يرى صاحب التطبيق الأرقام

Firebase console → Realtime Database → **Data** tab → `installs/` →
one child node per install (`installs/<install_id>`), each showing its
`app_version` and `platform`. The number of nodes under `installs/`
is the number of installs that pinged in the last period.

### Rules mode / وضع قواعد قاعدة البيانات

- **Test mode** (rules allow writes): the pings land in `installs/`
  as above.
- **Locked mode** (rules deny writes): every write is refused with
  HTTP 401/403 and the app **silently ignores it** — the app is
  completely unaffected, works fully offline or online, and nothing
  is shown to the user, ever. Check or change the mode in the
  Firebase console → Realtime Database → **Rules** tab.

#### The exact rules to paste (Locked mode → allow only the stats writes)

The owner's database is in **Locked mode**, so until these rules are
pasted the app sends nothing to Firebase at all. Paste this — exactly
as it is, replacing the whole contents of the Rules tab — in the
Firebase console → Realtime Database → **Rules** tab, then click
**Publish**:

<!-- BEGIN FIREBASE RULES (parsed by tests/test_telemetry_firebase.py — keep this block valid JSON) -->
```json
{
  "rules": {
    "installs": {
      "$install_id": {
        ".write": true,
        ".read": false
      }
    },
    ".read": false,
    ".write": false
  }
}
```
<!-- END FIREBASE RULES -->

What this allows — and what it does not:

- The app's one write, a REST `PUT` to
  `<firebase_url>/installs/<install_id>.json`
  (`src/models/telemetry.py`, `_send_firebase()`), **is permitted**:
  the `".write": true` on `installs/$install_id` grants that node
  and its children. The `".write": false` at the root is the default
  deny — it does **not** veto the deeper grant: in Realtime Database
  rules, `.read`/`.write` cascade down the path, a grant at any level
  on the path permits the operation, and a `false` is simply "no
  grant here" (only a *grant* at a shallower level cannot be revoked
  by a deeper rule). So the root `false` + the deep `true` together
  mean "locked everywhere except this one stats branch".
- **Everything else stays denied:** reads anywhere (`.read` is
  `false` at the root and under `installs/$install_id`), and writes
  anywhere outside `installs/<install_id>`.
- Honest limit: no auth is used (no API key, no service account),
  so anyone who knows the database URL could write to — or delete —
  any node under `installs/`. The rules limit the damage to that one
  stats branch; they cannot tie a write to one specific install.
  That is the design as implemented, not a rules mistake.

#### Until the rules are pasted: the app simply sends nothing

No error, no crash, no retry storm. Verified in the code
(`src/models/telemetry.py` + `src/ui/shell.py`):

- The app attempts a Firebase send **at most once per launch**:
  `shell.py` schedules `_telemetry_silent()` once, 800 ms after
  startup, and it calls `maybe_send_async()` once in a daemon
  thread. There is **no timer, no loop and no re-scheduling** while
  the app stays open — a denied write is not retried until the next
  launch, and then only once.
- A denied write (`_send_firebase()` returns `"denied"` on HTTP
  401/403) **does not update** `telemetry_last_sent_firebase`
  (that timestamp is written only on HTTP 200), so the Firebase
  clock stays "due" — the next launch tries again once. A
  permanently locked database therefore costs one short PUT attempt
  per launch and nothing more.

### How the owner sets the Firebase URL / كيف يضبط صاحب التطبيق الرابط

Exactly like `telemetry_url` above: there is deliberately **no field
in the app UI** — the owner sets it directly in the clinic database
on his own machine, with the app closed. This only tells the app
*where* to send the same 4 fields; no new data is collected. The
setting is empty by default, so a fresh build sends nothing to
Firebase, and the URL is **never hardcoded in the code** (this project
is open source — a hardcoded URL would route every open-source user's
stats to the owner's database):

```bash
# from the app folder, with the app closed:
python -c "from src.models.telemetry import set_firebase_url; set_firebase_url('https://anadoctorfady-default-rtdb.firebaseio.com/')"
# to stop Firebase sending again, clear it:
python -c "from src.models.telemetry import set_firebase_url; set_firebase_url('')"
```

## Who sees the stats / من يرى الإحصاءات

Only the owner (Fady). `GET /stats` is token-protected
(`TELEMETRY_TOKEN` on the server); nobody else can read the numbers.
The stats are only a total user count + a per-country breakdown.

## How to host the server (for Fady) / استضافة الخادم

The app sends **nothing** until you host the server and set its URL
directly in the database as above (e.g. `https://stats.example.com/ping`):

```bash
TELEMETRY_TOKEN=your-secret-token python server/telemetry_server.py
# listens on port 8000; put it behind HTTPS (reverse proxy) in production
```

- `POST /ping` — accepts only the 4 fields above (`country` optional for older clients; other extra fields → 400).
- `GET /stats?token=...` — JSON `{total_users, users_by_country, last_30_days}`.
- `GET /` — simple HTML page: total users + table by country.
- Data: SQLite `server/telemetry.db`, table `pings(date, country_code, install_hash)`.

Details: `server/README.md`. Code: `src/models/telemetry.py`,
`server/telemetry_server.py`. Tests: `tests/test_telemetry.py`,
`tests/test_telemetry_firebase.py` (mocked network — the real
Firebase is never touched by tests).
