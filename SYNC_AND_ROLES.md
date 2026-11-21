# Specialties, Notes, Clipboard, Scans, Sync & Roles
# التخصصات والملاحظات والحافظة والمسح والمزامنة والصلاحيات

## 1. Dental specialties / تخصصات طب الأسنان

8 built-in specialties, each with ready tables for complaint, symptoms,
diagnosis and procedures (EN + AR): General (عام), Orthodontics (تقويم),
Oral Surgery (جراحة), Endodontics (لبية / علاج جذور), Pediatric (أطفال),
Periodontics (لثة), Implantology (زراعة), Prosthodontics (تعويضات).

- Pick a specialty at the top of the Clinical tab; the "📋 جاهز:" phrase
  rows filter to that specialty.
- **Manage templates / إدارة القوالب** (button next to the picker): add, edit
  or delete your own phrases per specialty + category, or add a whole new
  specialty (EN + AR name). Seeded phrases cannot be edited or deleted;
  your own phrases can. Data: `src/data/specialties.json` + table
  `specialty_templates` (module `src/models/specialty_templates.py`).

## 2. Notes table / جدول الملاحظات

At the END of the Clinical tab (after costs) there is an optional
**Notes / ملاحظات** section where the doctor writes notes about the
service provided to the patient. Notes are saved in the patient file,
appear as the final section (7) of the patient PDF report, and can be
edited or deleted only by their author or by an admin.

## 3. Clipboard multi-copy / النسخ المتعدد من الحافظة

- **Ctrl+Shift+V** opens the clipboard history picker in EVERY table
  field (complaint, symptom, diagnosis, procedure, cost, notes).
- Tick several copied items and press **Paste selected / لصق المحدد**
  to paste them all at once, one per line; or **Paste all / لصق الكل**.
- **Copy row / نسخ الصف** buttons on the clinical tables copy the
  selected row into the history (last 20 items), so the doctor never
  retypes the same text for every patient or table. The ready-phrase
  picker ("📋 جاهز:") works in the same fields.

## 4. CBCT & intraoral scans / صور CBCT والمسح داخل الفم — honest limits

The **Scans / صور CBCT والمسح** tab in the patient file stores:
- CBCT `.dcm` (DICOM): file is stored; header metadata (patient, study
  date, modality) is shown only if `pydicom` is installed. pydicom is an
  OPTIONAL dependency (`requirements.txt`, commented) — the app works
  fully without it, and shows a clear message in that case. A 2D slice
  preview is NOT rendered inside the app yet; the tab shows the DICOM
  header details.
- Intraoral scans `.stl` / `.ply` / `.obj`: file is stored; triangle /
  vertex / face counts are shown when parseable. **3D viewing is NOT
  possible inside the Tkinter app** — use the **Open externally /
  فتح خارجياً** button to open the file in a 3D viewer.
- 2D images (`.png` / `.jpg` / `.tiff`): displayed inline with Pillow.
- Files live in `anadoctorfady/scans/<file_number>/`. Delete is allowed
  for admin / doctor only.

## 5. Multi-device online sync / ربط عدة أجهزة أونلاين

Offline-first: every device works fully offline. When a sync server URL
is set (Settings → Multi-device sync) and the device is online, queued
changes push and other devices' changes pull in a background thread.

**Host the server** (any always-on Windows/Linux PC or VPS with Python 3):
```
python server/sync_server.py --port 8001
```
Default DB `server/clinic_sync.db`. Reachable from each device by LAN IP
(e.g. `http://192.168.1.10:8001`) or over the internet (public IP/domain +
port forwarding / firewall rule for 8001).

**On each device:** Settings → Multi-device sync → set **Sync server URL**
(e.g. `http://192.168.1.10:8001`) and **Center ID** (`main` for one center;
a distant branch uses its own ID, e.g. `branch2`). Empty URL = standalone,
fully offline. Linked centers share by pointing at the same sync server.

**Conflicts:** last-write-wins by `updated_at` timestamp (documented in
`server/SYNC_README.md`). Synced records carry author + `center_id`, so
opening a patient file shows procedures, treatments and notes from every
doctor of the same center (or linked centers on the same server).

## 6. Users & roles / المستخدمون والصلاحيات

| Role | Clinical records | Payments (add) | Payments (edit) | Manage users | Attendance view |
|---|---|---|---|---|---|
| **admin** (full) | ✅ | ✅ (for any doctor) | ✅ | ✅ | ✅ |
| **doctor** | ✅ | ✅ (for self only) | ❌ | ❌ | ❌ |
| **nurse** | view only | ✅ (for any treating doctor) | ❌ | ❌ | ❌ (can clock in/out) |

Rules are enforced in `src/models/permissions.py` AND in the UI
(buttons disabled/hidden) AND in the models (`update_payment_checked`
returns False for non-admin). The existing user `fady` is admin.

**Create the first extra users** (admin only, no in-app screen yet):
```
# 1. Get a token:
curl -X POST http://<server>:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"fady","password":"1234"}'
# 2. Create a user (roles: admin / doctor / nurse):
curl -X POST http://<server>:8001/users \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"username":"doctor1","password":"<strong-password>","role":"doctor","center_id":"main"}'
```
Duplicate username → 409.

**Password policy / سياسة كلمة السر (exact): every user changes ONLY
their own password; no user changes another user's password EXCEPT the
admin (root), who may change any user's password.**
- Self-change: `POST /auth/change-password` with `{"old_password",
  "new_password"}` (min 4 chars). Wrong old password → 401.
- Admin changing another user: same endpoint with `{"username": "<name>",
  "new_password": "..."}` — `old_password` NOT required. Non-admin
  trying this → 403. Unknown user → 404.
- In the app: Settings → "Change Password / تغيير كلمة السر" changes
  YOUR password only (old + new + confirm). It updates the local DB
  and, when a sync URL is set, the server too (logs in with the old
  password first); offline, the local change still succeeds and the
  server password is left unchanged until next login.
- Admin deleting a user: `DELETE /users/<username>` (admin only).
  Unknown user → 404. **The last remaining admin cannot be deleted
  (400)** — so always create + verify a replacement admin first.

**Username rule / قاعدة اسم المستخدم (exact): every user logs in with
their OWN name, not the default `fady`; an admin or a user can create
a new username + password, but AFTER a username is created, nobody can
change it EXCEPT the admin (root).**
- Usernames: 3-32 chars, no spaces (they appear in URLs).
- Rename (admin only, even renaming oneself needs the admin role):
  `POST /users/<old-username>/rename` with `{"new_username": "<new>"}`.
  Non-admin → 403. Unknown source user → 404. New name taken → 409.
  Invalid new name → 400. Password, role and center_id stay unchanged;
  the renamed user logs in with the NEW name + the SAME password.
- In the app: Settings → "Rename User / إعادة تسمية مستخدم" (admin
  only — other users see only the note that renaming is admin-only).
  It renames locally and, when a sync URL is set, on the server too.
  The old "Change Login" box that let any user rename themselves was
  removed; password change stays in its own section.
- Known limitation: historical sync/attendance records keep the OLD
  author name string (they are not rewritten); only the login name
  changes.
- Daily use: never work as `fady` — every person logs in with their
  own name. Create real users with their own names, then change
  `fady`'s password or delete `fady` (never delete the last admin).

**Safe first hosting / الاستضافة الآمنة الأولى (in this order, LAN only
— do NOT open port 8001 to the internet before step 5):** 1. start the
server, 2. log in as `fady` / `1234`, 3. create a new admin with a
strong password (`POST /users`), 4. verify the new admin login,
5. as the new admin, change `fady`'s password (`POST
/auth/change-password`) or delete `fady` (`DELETE /users/fady`).
Create every real user with their own name (`POST /users` with their
own username + password) — never share `fady` for daily work.
The old temporary direct-DB-delete workaround is NO LONGER NEEDED.
Note: the server recreates the default admin `fady` / `1234` on startup
only if the users table is completely empty.

## 7. Attendance / الحضور والانصراف

The app records attendance automatically: **on every login ("in") and
every logout ("out")** with the exact timestamp + device id, locally
first (works offline) and synced to the server when online.
Admins open **الحضور / Attendance** (top bar, admin only) to list
entries per user per day with exact in/out times.

## 8. Tests / الاختبارات

`run_tests.py` — **23/23 PASS**, all `.py` files ≤ 200 lines:
`test_specialties`, `test_scans`, `test_clipboard_multi`,
`test_sync_roles` (incl. a real local sync server in a thread),
`test_password_change` (self/admin password policy + delete user, also
against a real local server), `test_username_rename` (admin-only rename,
server + local, also against a real local server),
`test_finance_permissions` (admin full / doctor own-only / nurse none;
nurse-enters-payment-credited-to-treating-doctor; day/month/period
totals; gate lock/re-lock), `test_screenshot_fixes` (About text, finance
re-auth gate, clinical cost loader, rename refresh).

## 9. Finance tab permissions / صلاحيات تبويب المالية

The Finance tab is **ADMIN-only in full**; a doctor sees ONLY their own
income (daily / monthly / for a chosen period); a nurse sees **no finance
at all**. Enforced in `src/models/permissions.py` (`finance_scope`) +
`src/ui/finance.py` (role overlay shown after the re-auth gate) +
`src/models/finance.py` (`doctor_income`).

**Attribution — treating doctor, not who typed it:** the nurse collects
the money, so a payment is credited to the **TREATING DOCTOR** (`doctor`
field), never to the person who entered it. The payment form has a
"Treating doctor / الطبيب المعالج" selector (defaults to the logged-in
doctor). `entered_by` records the logged-in user who typed the entry,
for audit only — it never decides whose income it is. Old rows with NULL
doctor are visible to the admin only (never in any doctor's income).

**Finance sync — multi-center (2026-11-07):** financial records DO sync
now, via the existing sync server (port 8001): `/sync/push` + `/sync/pull`
carry a `financials` collection (kind payment / expense / lab / salary)
and an `employees` collection. Every record carries `center_id` + `doctor`
+ `entered_by` + amounts + date + `updated_at`; last-write-wins on
`updated_at`, same as patients/visits. Offline-first: empty sync URL =
standalone, local finance only, everything still works offline.
Client: `src/models/finance_sync.py` (`split_financial_queue`,
`apply_financial_pull`, `queue_synced_row`); server: `server/finance_sync.py`.

**Server-side role filtering (enforced in `server/finance_sync.py` —
`pull_financials` / `push_financials`, using the Bearer token's
role/username stored at login):** on `/sync/pull` the admin gets ALL
centers' financials; a doctor gets ONLY records where `doctor` == their
own username (any center — it is their own income); a nurse gets NO
financial records at all. On `/sync/push` a non-admin may push a payment
only when `doctor` is an existing doctor/admin username in the server's
`users` table AND either `doctor` == their own username (own payment) or
`entered_by` == their own username (a nurse — or a doctor — recording a
payment for the treating doctor); a nurse cannot credit a payment to
herself, and a payment with an empty or unknown `doctor` is refused
(403). Expenses / lab / salary / employee records are admin-only
(403 otherwise). A doctor's "My income" now spans all synced centers,
still with NO center totals, NO other doctors, NO expenses.

**Admin per-center breakdown:** the Finance tab has a "Centers / المراكز"
tab (`src/ui/finance_views.py`, totals in `src/models/finance.py`
`per_center_totals`): one row per `center_id` with income, expenses
(incl. salaries), lab, debts, net. Standalone (no synced data) it lists
just the local center. Expenses and lab costs carry `center_id`
(migration in `src/models/sync.py` `ensure_finance_columns`); rows with
NULL `center_id` count under the device's center.

**Salaries — admin-only (2026-11-07):** the Finance tab has a "Salaries /
الرواتب" tab (`src/ui/salaries_view.py`, model `src/models/salaries.py`,
gated by `permissions.can_manage_salaries`). Employees live in a SEPARATE
`employees` table — id, name, job title (doctor / nurse / other), monthly
salary, `center_id`, `linked_username` (NULL = no app login), phone,
active flag. **An employee with NULL `linked_username` can NEVER log in:**
login consults ONLY the `users` table (local `src/utils/auth.py`, server
`server/auth.py`) — nothing in the salaries code authenticates.
Salary payments (employee, month `YYYY-MM`, amount, payment date,
`entered_by`, `center_id`) show per employee per month: monthly salary,
paid so far, remaining. **Salary payments count as CENTER EXPENSES:**
they appear in the admin per-center breakdown as part of that center's
expenses. They sync like other financials (admin sees all centers);
doctors see NO salary data — not even their own salary — because salary
records carry no `doctor` field, so the server-side pull filter excludes
them for every doctor; nurses get none. The `employees` table itself
also syncs, admin-only (`pull_employees` / `push_employees` in
`server/finance_sync.py`). Only the admin can add employees, set
salaries, and record salary payments.

## User management screen (2026-11-07, admin-only)
- New "Users / المستخدمون" tab in the main notebook, visible only to the
  admin (hidden for doctors/nurses); refreshed on login and on rebuild.
- Create user: username 3-32 chars, no spaces; password min 4 chars; role
  doctor/nurse/admin; center defaults to this device's center. Duplicate
  names are refused. Every user logs in with their own name + password.
- Creation is local-first (local `clinic.db` users table, `src/utils/auth.py`
  `create_user`), then the sync server via the existing admin-only
  `POST /users` (201 created, 409 name taken) when a sync URL is set, using
  the admin password entered in the form as the server login. Offline / no
  sync URL / no admin password: local creation succeeds and the screen says
  so explicitly — the server account is NOT created yet.
- Delete user (admin-only): the last remaining admin can never be deleted,
  locally or on the server (`DELETE /users/<name>`). The admin cannot delete
  their own account from this screen.
- Local user list shows username / role / center (center = this device's
  center; per-user center is stored server-side only).

## Sync Now button (2026-11-07)
- Where: Settings tab, inside the "Multi-device sync / مزامنة الأجهزة"
  frame, next to "Save sync settings" — button "🔄 Sync Now / مزامنة الآن"
  (`src/ui/sync_now_ui.py`, `attach_sync_button`; `settings_ui.py` only
  imports it and calls it — that file is at the 200-line limit).
- Password: asked EVERY sync in a small masked prompt (Entry show="•",
  same pattern as the finance re-auth gate) for the currently logged-in
  user. It is NEVER saved or stored anywhere — the login flow passes only
  the username on success, so the session has no password to reuse.
  Closing the prompt cancels the sync; nothing is sent.
- What happens: the button reads the URL + center ID from the frame
  (edits apply immediately, no need to Save first), then calls
  `sync_now(conn, url, user, password, center)` — login, push the queued
  changes, pull the server's newer records. A refused push stays queued
  and retries on the next sync; server-side role filtering still applies.
- Result message (bilingual messagebox):
  - "Sync done / تمت المزامنة — pushed N • pulled patients P / visits V /
    financials F / employees E" — N = queued records accepted by the
    server, the pulled numbers are the records actually applied locally.
    Any push/pull problem is appended after the counts.
  - "Offline / بلا اتصال" — no sync URL set, or the server is unreachable.
    Nothing is lost: local changes stay queued.
  - "Login failed / فشل الدخول" — wrong password or username; check the
    password and try again.
  - "Not logged in / لم يتم تسجيل الدخول" — log in first, then sync.
