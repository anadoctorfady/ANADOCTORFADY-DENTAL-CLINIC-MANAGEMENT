"""Round 49 section B: WhatsApp Cloud API setup guide, as DATA.

STEPS: list of (title_en, title_ar, body_en, body_ar). Meta UI
labels stay in English verbatim in both languages (that is how
they appear on Meta's site). The exact template bodies to submit
for approval live in TEMPLATE_EN / TEMPLATE_AR:
  {{1}} patient name, {{2}} centre name, {{3}} date, {{4}} time.
"""
TEMPLATE_NAME = "appointment_reminder"
TEMPLATE_EN = ("Hello {{1}}, this is a reminder from {{2}} of your "
               "appointment on {{3}} at {{4}}.")
TEMPLATE_AR = "مرحباً {{1}}، هذا تذكير من {{2}} بموعدك بتاريخ {{3}} الساعة {{4}}."

STEPS = [
    ("1. Create a Meta for Developers account",
     "١. إنشاء حساب Meta for Developers",
     "Go to developers.facebook.com and sign in with the Facebook "
     "account that will manage the clinic's number. Accept the "
     "developer terms if asked.",
     "انتقل إلى developers.facebook.com وسجّل الدخول بحساب فيسبوك "
     "الذي سيدير رقم العيادة. وافق على شروط المطوّرين إن طُلب منك."),
    ("2. Create an app (type: Business)",
     "٢. إنشاء تطبيق (النوع: Business)",
     "In My Apps choose Create App, pick the Business type, name "
     "it (for example your centre name) and create it.",
     "من My Apps اختر Create App، واختر النوع Business، وسمِّ "
     "التطبيق (اسم مركزك مثلاً) ثم أنشئه."),
    ("3. Add the WhatsApp product",
     "٣. إضافة منتج WhatsApp",
     "On the app dashboard, find WhatsApp and click Set up. This "
     "creates the WhatsApp Business account linked to the app.",
     "في لوحة التطبيق ابحث عن WhatsApp واضغط Set up. سيؤدي ذلك "
     "إلى إنشاء حساب WhatsApp Business مرتبط بالتطبيق."),
    ("4. Register the centre's OWN phone number",
     "٤. تسجيل رقم هاتف المركز الخاص",
     "In WhatsApp > API Setup (or WhatsApp Manager) choose Add "
     "phone number. Enter the centre's own number - it must be "
     "able to receive an SMS or a voice call, because Meta sends "
     "a verification code to it. Enter the code to finish.",
     "في WhatsApp ثم API Setup (أو WhatsApp Manager) اختر Add "
     "phone number. أدخل رقم المركز الخاص - يجب أن يستقبل رسالة "
     "SMS أو مكالمة صوتية، لأن Meta ترسل رمز تحقق إليه. أدخل "
     "الرمز للإنهاء."),
    ("5. Copy the Phone Number ID",
     "٥. نسخ معرّف رقم الهاتف (Phone Number ID)",
     "Stay on API Setup: under the registered number you will see "
     "Phone Number ID. Copy that number - you will paste it into "
     "this app's Settings (step 9). It is NOT the phone number "
     "itself.",
     "ابقَ في API Setup: تحت الرقم المسجّل ستجد Phone Number ID. "
     "انسخ هذا الرقم - ستلصقه في إعدادات هذا التطبيق (الخطوة ٩). "
     "إنه ليس رقم الهاتف نفسه."),
    ("6. Create a PERMANENT token (System User)",
     "٦. إنشاء رمز وصول دائم (System User)",
     "Go to Business Settings -> Users -> System Users -> Add. "
     "Name it, set the role to Admin, then Add Assets -> Apps -> "
     "select your app -> Full control. Then Generate New Token, "
     "choose your app and tick the permission "
     "whatsapp_business_messaging. Copy the token at once - it is "
     "shown only once. WARNING: the token shown on the API Setup "
     "page is TEMPORARY and expires in 24 hours - do not use it.",
     "انتقل إلى Business Settings ثم Users ثم System Users ثم "
     "Add. سمِّه واجعل الدور Admin، ثم Add Assets ثم Apps واختر "
     "تطبيقك مع Full control. بعدها Generate New Token واختر "
     "التطبيق وفعّل صلاحية whatsapp_business_messaging. انسخ "
     "الرمز فوراً - يظهر مرة واحدة فقط. تحذير: الرمز الظاهر في "
     "صفحة API Setup مؤقت وينتهي خلال ٢٤ ساعة - لا تستخدمه."),
    ("7. Create the message template",
     "٧. إنشاء قالب الرسالة",
     "In WhatsApp Manager -> Message templates -> Create "
     "template: category Utility, name appointment_reminder, and "
     "add BOTH languages English and Arabic with the exact body "
     "texts shown at the end of this guide ({{1}} patient name, "
     "{{2}} centre name, {{3}} date, {{4}} time).",
     "في WhatsApp Manager ثم Message templates ثم Create "
     "template: الفئة Utility، والاسم appointment_reminder، "
     "وأضف اللغتين English وArabic معاً بنصي الرسالة الدقيقين "
     "في نهاية هذا الدليل ({{1}} اسم المريض، {{2}} اسم المركز، "
     "{{3}} التاريخ، {{4}} الوقت)."),
    ("8. Wait for the Approved status",
     "٨. انتظار حالة Approved",
     "Meta reviews the template, usually within minutes to a day. "
     "Send nothing until its status shows Approved.",
     "تراجع Meta القالب، عادة خلال دقائق إلى يوم. لا ترسل شيئاً "
     "حتى تظهر حالته Approved."),
    ("9. Paste the values into this app's Settings",
     "٩. لصق القيم في إعدادات هذا التطبيق",
     "In Settings, in the WhatsApp reminders frame, paste the "
     "Phone Number ID, the permanent token and the template name "
     "(appointment_reminder), pick the template language, and "
     "press Save. These values stay on this device only - they "
     "are never synced to other centres.",
     "في الإعدادات، ضمن إطار تذكيرات واتساب، الصق معرّف رقم "
     "الهاتف والرمز الدائم واسم القالب (appointment_reminder)، "
     "واختر لغة القالب، ثم اضغط حفظ. تبقى هذه القيم على هذا "
     "الجهاز فقط - ولا تتم مزامنتها إلى مراكز أخرى أبداً."),
    ("10. Send a test message",
     "١٠. إرسال رسالة تجريبية",
     "Press Send test in the same frame and enter your own mobile "
     "number in international format. You should receive the "
     "reminder template within seconds.",
     "اضغط إرسال تجريبي في الإطار نفسه وأدخل رقم هاتفك بالصيغة "
     "الدولية. ستصلك رسالة القالب خلال ثوانٍ."),
    ("11. Tick Enable - reminders run automatically",
     "١١. فعّل التفعيل - التذكيرات تعمل تلقائياً",
     "Tick Enable and Save. While the app is running, reminders "
     "go out automatically about 48 hours and again about 24 "
     "hours before each appointment - no action needed from the "
     "doctor. Keep patient mobile numbers in international "
     "format (country code first) so delivery works.",
     "فعّل خيار التفعيل ثم احفظ. أثناء تشغيل التطبيق تُرسل "
     "التذكيرات تلقائياً قبل الموعد بنحو ٤٨ ساعة ومرة أخرى قبل "
     "نحو ٢٤ ساعة - دون أي تدخل من الطبيب. حافظ على أرقام هواتف "
     "المرضى بالصيغة الدولية (رمز الدولة أولاً) لضمان الوصول."),
]


def guide_text(lang="en"):
    """Full guide as one plain-text block in `lang`, ending with
    the exact template bodies in BOTH languages (step 7 refers
    to them)."""
    t_i, b_i = (1, 3) if lang == "ar" else (0, 2)  # (title, body) slots
    out = []
    for step in STEPS:
        out.append(step[t_i])
        out.append(step[b_i])
        out.append("")
    out.append("appointment_reminder - English:")
    out.append(TEMPLATE_EN)
    out.append("appointment_reminder - العربية:")
    out.append(TEMPLATE_AR)
    return "\n".join(out)
