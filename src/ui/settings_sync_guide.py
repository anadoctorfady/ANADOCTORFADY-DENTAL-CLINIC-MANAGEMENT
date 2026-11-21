"""In-tab device-linking guide (Item 11): step-by-step, bilingual.
Opened from the Settings sync frame ("Linking guide" button): a
scrollable read-only text window — no external file, no browser —
so it works fully offline. Covers: the sync server, installing /
starting it, LAN vs internet, port 8001, the first-hosting safety
flow, users with their own names, sync URL + center, Sync Now,
attendance, and troubleshooting. R19 item 7: text sits inside a
RoundedFrame (its own square corners are inset by the frame pad).
"""
import tkinter as tk
from tkinter import scrolledtext
from src.config.theme import current, RADIUS_CARD
from src.ui.rounded import rounded_button; from src.ui.rounded_frame import RoundedFrame
from src.config.strings import t

GUIDE_EN = """LINKING GUIDE — connecting several devices / centers
================================================

1. WHAT THE SYNC SERVER IS
   The app works fully offline on one device. To link several devices
   (same center, or distant centers), one always-on computer runs a
   small sync server (server/sync_server.py). Devices send their new
   records to it and pull the other devices' records from it. Opening
   a patient file then shows procedures, treatments and notes from
   EVERY doctor of the center (or linked centers on the same server).
   Conflicts: last-write-wins by updated_at timestamp.

2. INSTALLING / STARTING THE SERVER
   Any always-on Windows/Linux PC or VPS with Python 3:
       python server/sync_server.py --port 8001
   Default database: server/clinic_sync.db. Keep that computer on
   whenever devices need to sync; offline devices keep working and
   sync later — nothing is lost.

3. LAN vs INTERNET — PORT 8001
   Same building (LAN): devices use the server's LAN address, e.g.
   http://192.168.1.10:8001 (the server PC's local IP + port 8001).
   Distant centers (internet): public IP or domain + port forwarding
   / firewall rule for port 8001 on the server's router. Use HTTPS
   (reverse proxy) in production when the server is on the internet.

4. FIRST-HOSTING SAFETY — DO THIS FIRST (LAN ONLY)
   The server starts with a default admin: username fady, password
   1234. Do NOT open port 8001 to the internet before step 5.
   1) Start the server.  2) Log in as fady / 1234.
   3) Create a NEW admin with a strong password (POST /users — see
      SYNC_AND_ROLES.md, or the Users tab in the app).
   4) Verify the new admin can log in.
   5) As the new admin, change fady's password (POST
      /auth/change-password) or delete fady (DELETE /users/fady).
   Never delete the last remaining admin. The server recreates the
   default fady / 1234 only if the users table is completely empty.

5. CREATING USERS — EVERYONE USES THEIR OWN NAME
   Never share fady for daily work. Create each person with their own
   username + password (admin only, Users tab or POST /users; roles:
   admin / doctor / nurse; usernames 3-32 chars, no spaces). A
   username cannot be changed afterwards except by the admin
   (Settings -> Rename User). Every user changes ONLY their own
   password (Settings -> Change Password); only the admin may change
   another user's password.

6. SETTING THE SYNC URL + CENTER (on EACH device)
   Settings -> Multi-device sync: Sync server URL, e.g.
   http://192.168.1.10:8001, and Center ID (main for one center; a
   distant branch uses its own ID, e.g. branch2). Linked centers share
   by pointing at the SAME sync server. Empty URL = standalone, fully
   offline. Press "Save sync settings".

7. SYNC NOW BUTTON
   In the same sync frame: "Sync Now / مزامنة الآن". It asks for YOUR
   password every time (masked, never saved — cancel = no sync). It
   logs in, pushes queued changes, pulls newer records, and reports
   pushed / pulled counts. A refused push stays queued and retries on
   the next sync. Finance rules still apply server-side (admin sees
   all centers; a doctor sees only their own income; a nurse sees
   no finance).

8. ATTENDANCE
   The app records attendance automatically: on every login ("in")
   and every logout ("out") with the exact time + device id, locally
   first (works offline) and synced when online. Admins open
   "Attendance / الحضور" (top bar, admin only) to list entries per
   user per day with exact in/out times.

9. TROUBLESHOOTING
   - Offline / no sync: check the URL, the server PC is on, same
     Wi-Fi/LAN, and port 8001 is not blocked by the firewall.
   - Login failed: wrong password for that username — check caps,
     or ask the admin to reset it (admin only).
   - Port closed: on the server PC open port 8001 in the firewall;
     for internet access also add port forwarding on the router.
   - Nothing is lost when sync fails: local changes stay queued and
     sync on the next successful Sync Now.
   Full details: SYNC_AND_ROLES.md and server/SYNC_README.md.
"""

GUIDE_AR = """دليل الربط خطوة بخطوة — ربط عدة أجهزة / مراكز
========================================

١. ما هو خادم المزامنة؟
   التطبيق يعمل كاملاً دون إنترنت على جهاز واحد. لربط عدة أجهزة
   (نفس المركز أو مراكز بعيدة) يعمل جهاز واحد دائم التشغيل كخادم
   مزامنة صغير (server/sync_server.py). ترسل الأجهزة سجلاتها الجديدة
   إليه وتسحب سجلات الأجهزة الأخرى منه. عند فتح ملف مريض تظهر
   الإجراءات والعلاجات والملاحظات من كل أطباء المركز (أو المراكز
   المرتبطة على نفس الخادم). عند التعارض: الأحدث كتابةً يفوز.

٢. تثبيت / تشغيل الخادم
   أي جهاز Windows/Linux أو خادم VPS دائم التشغيل مع Python 3:
       python server/sync_server.py --port 8001
   قاعدة البيانات الافتراضية: server/clinic_sync.db. أبقِ هذا الجهاز
   يعمل كلما احتاجت الأجهزة للمزامنة؛ الأجهزة دون اتصال تستمر بالعمل
   وتزامن لاحقاً — لا يضيع أي شيء.

٣. شبكة محلية أم إنترنت — المنفذ 8001
   نفس المبنى (LAN): تستخدم الأجهزة عنوان الخادم المحلي، مثلاً
   http://192.168.1.10:8001 (عنوان IP المحلي لجهاز الخادم + المنفذ 8001).
   مراكز بعيدة (إنترنت): عنوان IP عام أو نطاق + فتح المنفذ 8001
   في جدار الحماية / الراوتر. استخدم HTTPS عند النشر على الإنترنت.

٤. أمان الاستضافة الأولى — افعل هذا أولاً (شبكة محلية فقط)
   يبدأ الخادم بمدير افتراضي: اسم المستخدم fady وكلمة السر 1234.
   لا تفتح المنفذ 8001 للإنترنت قبل الخطوة ٥.
   ١) شغّل الخادم. ٢) ادخل باسم fady / 1234.
   ٣) أنشئ مديراً جديداً بكلمة سر قوية (POST /users — انظر
      SYNC_AND_ROLES.md أو تبويب المستخدمين في التطبيق).
   ٤) تأكد أن المدير الجديد يستطيع الدخول.
   ٥) كمدير جديد، غيّر كلمة سر fady أو احذف fady.
   لا تحذف آخر مدير أبداً. يعيد الخادم إنشاء fady / 1234 فقط إذا
   كان جدول المستخدمين فارغاً تماماً.

٥. إنشاء المستخدمين — كل شخص باسمه الخاص
   لا تشارك fady للعمل اليومي. أنشئ لكل شخص اسم مستخدم + كلمة سر
   (للمدير فقط، تبويب المستخدمين أو POST /users؛ الأدوار: مدير /
   طبيب / ممرضة؛ 3-32 حرفاً بدون مسافات). لا يمكن تغيير اسم المستخدم
   بعد إنشائه إلا من قبل المدير. كل مستخدم يغيّر كلمة سره فقط؛
   المدير وحده يغيّر كلمة سر مستخدم آخر.

٦. ضبط رابط المزامنة + المركز (على كل جهاز)
   الإعدادات ← مزامنة الأجهزة: رابط الخادم مثلاً
   http://192.168.1.10:8001 ومعرّف المركز (main لمركز واحد؛ فرع
   بعيد يستخدم معرّفاً خاصاً مثل branch2). المراكز المرتبطة تشير
   إلى نفس الخادم. رابط فارغ = جهاز مستقل دون اتصال. اضغط
   «حفظ إعدادات المزامنة».

٧. زر «مزامنة الآن»
   في نفس إطار المزامنة: «Sync Now / مزامنة الآن». يطلب كلمة سرك
   في كل مرة (مخفية، لا تُحفظ أبداً — الإلغاء = لا مزامنة). يسجّل
   الدخول ويرسل التغييرات المعلقة ويسحب السجلات الأحدث ويعرض
   عدد المُرسَل والمُستقبَل. الدفعات المرفوضة تبقى معلقة وتُعاد
   في المزامنة التالية. قواعد المالية تُطبق على الخادم (المدير
   يرى كل المراكز؛ الطبيب يرى دخله فقط؛ الممرضة لا ترى المالية).

٨. الحضور والانصراف
   يسجّل التطبيق الحضور تلقائياً: عند كل دخول («in») وكل خروج
   («out») مع الوقت الدقيق ومعرّف الجهاز، محلياً أولاً (يعمل دون
   اتصال) ثم يُزامَن عند الاتصال. يفتح المدير «الحضور» (الشريط
   العلوي، للمدير فقط) لعرض السجلات لكل مستخدم وكل يوم.

٩. حل المشاكل
   - دون اتصال / لا مزامنة: تحقق من الرابط، وأن جهاز الخادم يعمل،
     ونفس شبكة Wi-Fi، وأن المنفذ 8001 غير محظور في جدار الحماية.
   - فشل الدخول: كلمة سر خاطئة لذلك الاسم — تحقق من الأحرف الكبيرة
     أو اطلب من المدير إعادة تعيينها (للمدير فقط).
   - المنفذ مغلق: افتح المنفذ 8001 في جدار حماية جهاز الخادم؛
     وللوصول من الإنترنت أضف تحويل المنفذ في الراوتر.
   - لا يضيع أي شيء عند فشل المزامنة: تبقى التغييرات معلقة
     وتُزامَن في المزامنة الناجحة التالية.
   التفاصيل الكاملة: SYNC_AND_ROLES.md و server/SYNC_README.md.
"""

GUIDE_TEXT = GUIDE_EN + "\n" + GUIDE_AR  # legacy combined text (kept for tests)


def guide_text(lang="en"):
    """Guide body in the app language only (round 16: no mixed text)."""
    return GUIDE_AR if lang == "ar" else GUIDE_EN
GUIDE_SECTIONS = ["sync server", "port 8001", "first-hosting safety",
                  "Sync Now", "attendance", "troubleshooting",
                  "fady", "1234", "LAN", "Center ID"]


def open_linking_guide(parent):
    """Scrollable guide window in the app language. Returns the Toplevel."""
    th = current()
    lang = getattr(parent, "lang", None) or getattr(getattr(parent, "app", None), "lang", "en") or "en"
    win = tk.Toplevel(parent)
    win.title(t("sync.guide_title", lang))
    win.geometry("760x600"); win.configure(bg=th["bg"])
    wrap = RoundedFrame(win, bg=th["panel"], border=th["border"], radius=RADIUS_CARD)
    wrap.pack(fill="both", expand=True, padx=10, pady=10)
    txt = scrolledtext.ScrolledText(wrap.inner, wrap="word", bg=th["panel"],
                                    fg=th["text"], font=("Segoe UI", 10))
    txt.pack(fill="both", expand=True)
    txt.insert("1.0", guide_text(lang))
    txt.configure(state="disabled")
    rounded_button(win, text=t("sync.guide_close", lang), bg=th["accent"], fg="white",
              relief="flat", command=win.destroy).pack(pady=(0, 10))
    return win
