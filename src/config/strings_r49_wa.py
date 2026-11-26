"""Round 49 section B: WhatsApp reminder strings (keys wa.*).

Merged into src/config/strings.py by the coordinator with:
    from src.config.strings_r49_wa import EN as _a, AR as _b; EN.update(_a); AR.update(_b)
Language purity: EN values contain no Arabic, AR values no Latin
(the one exception is the frame title pair, kept separate keys).
"""
EN = {
    "wa.frame_title": "WhatsApp reminders",
    "wa.enabled": "Enable automatic reminders",
    "wa.number": "Sender number (display):",
    "wa.phone_id": "Phone Number ID:",
    "wa.token": "Permanent access token:",
    "wa.template": "Template name:",
    "wa.template_lang": "Template language:",
    "wa.guide_btn": "Setup guide",
    "wa.test_btn": "Send test",
    "wa.save_btn": "Save",
    "wa.saved": "WhatsApp reminder settings saved.",
    "wa.guide_title": "WhatsApp reminders - setup guide",
    "wa.test_title": "Send test message",
    "wa.test_prompt": "Destination number (international format):",
    "wa.test_ok": "Test message sent.",
    "wa.test_fail": "Test message failed: {detail}",
    "wa.not_configured": "Fill in the Phone Number ID, token and template name first, then save.",
    "wa.hint": "Each centre enters its OWN number and credentials. They stay on this device only and are never synced.",
    "wa.template_heading": "Message template to submit for approval",
}
AR = {
    "wa.frame_title": "تذكيرات واتساب",
    "wa.enabled": "تفعيل التذكيرات التلقائية",
    "wa.number": "رقم الإرسال (للعرض):",
    "wa.phone_id": "معرّف رقم الهاتف:",
    "wa.token": "رمز الوصول الدائم:",
    "wa.template": "اسم القالب:",
    "wa.template_lang": "لغة القالب:",
    "wa.guide_btn": "دليل الإعداد",
    "wa.test_btn": "إرسال تجريبي",
    "wa.save_btn": "حفظ",
    "wa.saved": "تم حفظ إعدادات تذكيرات واتساب.",
    "wa.guide_title": "تذكيرات واتساب - دليل الإعداد",
    "wa.test_title": "إرسال رسالة تجريبية",
    "wa.test_prompt": "رقم الوجهة (بالصيغة الدولية):",
    "wa.test_ok": "تم إرسال الرسالة التجريبية.",
    "wa.test_fail": "فشل إرسال الرسالة التجريبية: {detail}",
    "wa.not_configured": "أدخل معرّف رقم الهاتف والرمز واسم القالب أولاً ثم احفظ.",
    "wa.hint": "كل مركز يدخل رقمه وبياناته الخاصة به. تبقى على هذا الجهاز فقط ولا تتم مزامنتها أبداً.",
    "wa.template_heading": "قالب الرسالة المطلوب تقديمه للموافقة",
}
