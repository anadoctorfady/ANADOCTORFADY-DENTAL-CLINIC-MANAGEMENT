# ANADOCTORFADY — Free Dental Clinic System

> **This app is completely free.** We ask Allah to make it ongoing charity
> (sadaqah jariyah) for Doctor **Fady Abdulkafy Dadoush** and his parents,
> wife and children.

A complete, bilingual (English / Arabic) dental clinic management system for
Windows 7 / 8 / 10 / 11. Written in Python + Tkinter with a local SQLite
database — no internet required, no subscription, no activation. Light on
laptops, modular code (no file over 200 lines), and easy to update piece by
piece.

![Login screen](docs/login.png)

## Features

- **Patients** — four-part Arabic name, Gregorian + Hijri birth date and age
  (live on entry), two mobiles + emergency phone, address, searchable
  nationality (249 countries, default Syrian), automatic file number, search
  by file no. / name / mobile / emergency phone.
- **Dental chart** — realistic graphic teeth (permanent 32 + deciduous 20),
  upper/lower jaws, per-tooth complaint, symptoms, diagnosis, procedures.
- **Costs** — total / paid / remaining auto-calculated, in SYP (default) or
  USD with a manual exchange-rate box and rate date. Default currency
  changeable in Settings (178 currencies).
- **Prescriptions** — 315 drugs by scientific (generic) name across all
  classes, 129 drug-interaction pairs with colored alerts (severe red /
  moderate amber), patient current meds + allergies, prescriptions always
  saved to the patient file, bilingual PDF.
- **Finance** — daily / period income, clinic expenses, lab costs, patient
  debts, net income = paid − expenses − lab. Password-protected, Excel + PDF
  export.
- **Appointments, X-ray images, backup / restore**, printable bilingual
  patient reports (`ANADOCTORFADY_<patient>.pdf`).
- **Reusable phrases** — auto-learning memory for complaints, symptoms,
  diagnoses, procedures (105 seed phrases) + clipboard history.
- **Bilingual EN (default) / AR** with correct joined RTL Arabic rendering
  (bundled Noto Naskh Arabic fonts), **light + dark mode**, Warm Sand design
  system.
- **Anonymous usage statistics (optional)** — when online, the app sends
  only `{install_id, app_version, platform}` every 4 hours; the server
  derives only the country from the IP and discards the IP. Count + countries
  only, nothing else, visible only to the owner. Offline = full app.
  The statistics server URL is empty by default, so nothing is sent until
  the owner hosts it (see `TELEMETRY.md`).

## Quick start (run from source)

Requires Python 3.8+ (for Windows 7 use Python 3.8.10).

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Default login: **fady / 1234** — change it in Settings after the first login.
On Linux/macOS: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && python3 main.py`
(the app targets Windows, but runs for testing on other systems).

## Build a Windows EXE

On Windows, run as Administrator (see `installer/README_BUILD.md`):

```bat
installer\build_exe_x86.bat   :: 32-bit — runs on x86 AND x64 (recommended)
installer\build_exe_x64.bat   :: 64-bit — runs on x64 only
```

Output: `installer\dist\ANADOCTORFADY_x86.exe` / `ANADOCTORFADY_x64.exe` —
a single double-click file, Python/SQLite/fonts bundled, works offline,
`clinic.db` is created automatically on first run. No Office or internet
needed. First run on Windows may show a SmartScreen "Unknown publisher"
warning (no paid code-signing certificate yet) — click "More info → Run anyway".

## Tests

Every change must pass the test gate before it is delivered:

```bat
python run_tests.py
```

Expected: **44/44 test files passed**. Also: no Python file may exceed
200 lines (`scripts/check_lines.py`).

## About — حول التطبيق

> This app is completely free and we ask Allah to make it ongoing charity
> for Doctor Fady Abdulkafy Dadoush and his parents, wife and children.

> هذا التطبيق مجاناً بالكامل و نسأل الله تعالى أن يكون صدقة جارية عن الدكتور
> فادي عبد الكافي دعدوش و عن والديه و زوجته و أولاده

Contact the developer on WhatsApp: **+963944234456** —
https://wa.me/963944234456

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Fork, branch, keep files under
200 lines, run the test gate before opening a pull request.

## License

MIT — see [LICENSE](LICENSE). Free for everyone, forever.

---

# ANADOCTORFADY — نظام عيادة أسنان مجاني

> **هذا التطبيق مجاناً بالكامل.** نسأل الله تعالى أن يكون صدقة جارية عن
> الدكتور **فادي عبد الكافي دعدوش** و عن والديه و زوجته و أولاده.

نظام متكامل لإدارة عيادة الأسنان لنظام ويندوز 7 / 8 / 10 / 11، ثنائي اللغة
(الإنجليزية / العربية)، مكتوب بلغة Python + Tkinter مع قاعدة بيانات SQLite
محلية — بدون إنترنت، بدون اشتراك، وبدون تفعيل. خفيف على الأجهزة، وكوده
معياري (لا يوجد ملف أكثر من 200 سطر) وسهل التحديث جزءاً جزءاً.

## المزايا

- **المرضى** — اسم رباعي، تاريخ ميلاد ميلادي + هجري مع العمر مباشرة عند
  الإدخال، جوالان + هاتف طوارئ، عنوان، جنسية قابلة للبحث (249 دولة،
  الافتراضي سوري)، رقم ملف تلقائي، بحث برقم الملف / الاسم / الجوال / الطوارئ.
- **مخطط الأسنان** — رسم واقعي للأسنان (32 دائم + 20 لبني)، الفكين العلوي
  والسفلي، شكوى وأعراض وتشخيص وإجراءات لكل سن.
- **التكاليف** — الإجمالي / المدفوع / المتبقي تُحسب تلقائياً، بالليرة السورية
  (افتراضي) أو الدولار مع صندوق سعر صرف يدوي وتاريخ السعر. العملة
  الافتراضية قابلة للتغيير من الإعدادات (178 عملة).
- **الوصفات** — 315 دواءً بالاسم العلمي من كل الفئات، 129 تداخلاً دوائياً
  مع تنبيهات ملونة (شديد بالأحمر / متوسط بالكهرماني)، أدوية المريض الحالية
  + الحساسية، الوصفات تُحفظ دائماً في ملف المريض، وPDF ثنائي اللغة.
- **المالية** — دخل يومي / لفترة، مصاريف العيادة، تكاليف المختبر، ديون
  المرضى، صافي الدخل = المقبوض − المصاريف − المختبر. محمية بكلمة سر،
  وتصدير Excel + PDF.
- **مواعيد، صور أشعة، نسخ احتياطي / استعادة**، وتقارير مرضى ثنائية اللغة
  قابلة للطباعة (`ANADOCTORFADY_<اسم المريض>.pdf`).
- **عبارات جاهزة** — ذاكرة تتعلم تلقائياً للشكوى والأعراض والتشخيص
  والإجراءات (105 عبارة أولية) + سجل الحافظة.
- **ثنائي اللغة إنجليزي (افتراضي) / عربي** مع عرض عربي صحيح متصل من
  اليمين لليسار (خطوط Noto Naskh Arabic مضمّنة)، **وضع فاتح + داكن**.
- **إحصاءات مجهولة (اختياري)** — عند الاتصال بالإنترنت يرسل التطبيق فقط
  `{install_id, app_version, platform}` كل 4 ساعات؛ الخادم يستنتج الدولة
  من الـ IP ثم يحذفه. عدد + دول فقط، ولا شيء غير ذلك، ولا يراها إلا المالك.
  وبدون إنترنت يعمل التطبيق كاملاً. رابط الخادم فارغ افتراضياً فلا يُرسل
  شيء حتى يستضيف المالك الخادم (انظر `TELEMETRY.md`).

## التشغيل السريع (من المصدر)

يتطلب Python 3.8+ (لويندوز 7 استخدم Python 3.8.10):

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

الدخول الافتراضي: **fady / 1234** — غيّره من الإعدادات بعد أول دخول.

## بناء ملف EXE لويندوز

على ويندوز، شغّل كمسؤول (انظر `installer/README_BUILD.md`):

```bat
installer\build_exe_x86.bat   :: 32-بت — يعمل على x86 و x64 (الموصى به)
installer\build_exe_x64.bat   :: 64-بت — يعمل على x64 فقط
```

الناتج: `installer\dist\ANADOCTORFADY_x86.exe` / `ANADOCTORFADY_x64.exe` —
ملف واحد بنقرة مزدوجة، بايثون وقاعدة البيانات والخطوط مضمّنة، يعمل بدون
إنترنت، و`clinic.db` تُنشأ تلقائياً عند أول تشغيل. قد تظهر رسالة SmartScreen
"ناشر غير معروف" عند أول تشغيل (لا توجد شهادة توقيع مدفوعة بعد) —
اضغط "More info ← Run anyway".

## الاختبارات

كل تعديل يجب أن يجتاز بوابة الاختبار قبل تسليمه:

```bat
python run_tests.py
```

المتوقع: **44/44 ملف اختبار ناجح**. ولا يجوز أن يتجاوز أي ملف بايثون
200 سطر (`scripts/check_lines.py`).

## التواصل

واتساب المطور: **+963944234456** — https://wa.me/963944234456

## المساهمة

انظر [CONTRIBUTING.md](CONTRIBUTING.md).

## الترخيص

MIT — انظر [LICENSE](LICENSE). مجاني للجميع، للأبد.
