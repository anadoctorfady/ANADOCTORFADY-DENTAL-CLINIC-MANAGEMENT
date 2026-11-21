# ANADOCTORFADY — Security: reverse engineering & code signing
# الأمان: فكّ الشيفرة والتوقيع الرقمي

> **Honest summary / الخلاصة الصادقة:** no method makes reverse engineering
> impossible. A PyInstaller one-file EXE **can** be unpacked and its Python
> bytecode read. What follows only makes that **harder**, and explains the
> Windows SmartScreen warning honestly. This app is **not** unbreakable.
>
> **لا توجد طريقة تجعل فكّ الشيفرة مستحيلاً.** ملف EXE المبني بـ PyInstaller
> **يمكن** فكّه وقراءة كود بايثون. ما يلي يصعّب ذلك فقط، ويشرح تحذير
> SmartScreen بصدق. هذا التطبيق **ليس** غير قابل للاختراق.

## 1. Reverse engineering — what is true / فكّ الشيفرة: ما الحقيقة؟

- A PyInstaller one-file EXE is a self-extracting archive: on start it
  extracts to a temp folder (`_MEIxxxxxx`). Tools like `pyinstxtractor`
  unpack it in seconds, and the `.pyc` files inside can be decompiled.
  ملف EXE هو أرشيف يستخرج نفسه عند التشغيل، وأدوات مجانية تفكّه خلال ثوانٍ.
- **Therefore: never put secrets in the code** — no passwords, API keys or
  licence checks that must stay hidden. The login here (`fady` / `1234`)
  is a local clinic login, not a security boundary; change it in Settings.
  **لذلك: لا تضع أي سرّ داخل الكود** — لا كلمات سر ولا مفاتيح API.
- What **does** help (raises the effort, does not stop a determined person):
  ما **يساعد فعلاً** (يرفع الجهد فقط ولا يوقف المصمّم):
  1. **PyArmor obfuscation (optional):** `installer\build_obfuscated.bat`
     runs `pyarmor gen -O obfuscated -r main.py src` if PyArmor is
     installed, then builds the EXE from the obfuscated code. If PyArmor
     is missing or fails, it falls back to the normal build with a warning.
     PyArmor 8 basic edition is free; advanced features are paid.
     Names/strings become unreadable, but the program still runs the same.
  2. **Strip debug info:** builds use `--noconfirm --clean`, `debug=False`
     in the `.spec`, and UPX compression when UPX is available
     (`upx=True` in `ANADOCTORFADY.spec`). This shrinks the EXE and
     removes some metadata — it is **not** protection by itself.
  3. **Do NOT use PyInstaller `--key`:** it was an "encryption" flag for
     bytecode, it is **deprecated and removed** in PyInstaller 6+, and it
     never stopped extraction anyway. This project does not use it.
     **لا تستخدم `--key`:** مُهمل ومحذوف، ولم يكن يمنع الفكّ أصلاً.
- **Bottom line:** obfuscation deters casual copying; it does not protect
  secrets and does not stop a skilled reverser. Keep patient data safe by
  keeping the **computer** safe (Windows password, backups), not by hiding code.
  **الخلاصة:** التشويش يردع النسخ العابر فقط؛ أمان بيانات المرضى يكون بحماية
  **الكمبيوتر** نفسه (كلمة سر ويندوز ونسخ احتياطي)، لا بإخفاء الكود.

## 2. Code signing & SmartScreen / التوقيع الرقمي وتحذير SmartScreen

### The "no certificate" message / رسالة "لا توجد شهادة"

- **Without a paid code-signing certificate, Windows SmartScreen WILL show
  "Windows protected your PC" / "Unknown publisher" on first run.**
  This is **not** an error and **not** a virus warning — it is Windows
  saying "I don't know who published this program".
  **بدون شهادة توقيع مدفوعة، سيظهر تحذير SmartScreen "حمى Windows جهازك" /
  "ناشر غير معروف" عند أول تشغيل. هذا ليس خطأً وليس تحذير فيروسات — بل يعني
  أن ويندوز لا يعرف من نشر البرنامج.**
- What the user clicks: **"More info" → "Run anyway"**. The app then runs
  normally, and after enough people run it (reputation builds up) the
  warning appears less often. Nothing is broken; do not "fix" it by
  disabling SmartScreen.
  ما يضغطه المستخدم: **"معلومات إضافية" ← "تشغيل على أي حال"**. بعدها يعمل
  التطبيق طبيعياً، ويقلّ التحذير مع الوقت. لا تعطّل SmartScreen.

### How to remove the warning (only way) / كيف يُزال التحذير (الطريقة الوحيدة)

- Buy a code-signing certificate and sign the EXE with `signtool`:
  اشترِ شهادة توقيع ووقّع الـ EXE بأداة `signtool`:
  - **OV certificate** (Organization Validation, ~$200–400/year): removes
    the "Unknown publisher" text, shows your clinic/company name. SmartScreen
    warning may still appear briefly until reputation builds.
  - **EV certificate** (Extended Validation, more expensive): gives
    immediate SmartScreen reputation — no warning from the first run.
  - Buy from a public CA (e.g. DigiCert, Sectigo, SSL.com). A self-signed
    certificate does **not** help: SmartScreen still warns.
    الشهادة الذاتية **لا تنفع** — التحذير سيبقى.
- The build scripts support this **optionally**: if the environment
  variables `CERT_PFX` (path to the `.pfx` file) and `CERT_PASS`
  (its password) are set, the script runs:
  سكربتات البناء تدعم ذلك **اختيارياً** إذا عُرّفت المتغيرات:
  `signtool sign /f "%CERT_PFX%" /p "%CERT_PASS%" /tr http://timestamp.digicert.com /td sha256 /fd sha256 installer\dist\ANADOCTORFADY.exe`
  - `signtool` comes with the Windows SDK / Visual Studio. If it is not
    on PATH, or the variables are not set, signing is **skipped with a
    note** and the build still succeeds — the EXE is simply unsigned.
    إذا لم توجد الشهادة أو الأداة، يُتخطّى التوقيع بملاحظة ويبقى البناء ناجحاً.
  - **Never commit the `.pfx` file or its password to the zip/repo.**
    **لا تضع ملف الشهادة أو كلمة سره أبداً داخل الحزمة.**
- Antivirus false positives are a separate, common PyInstaller issue:
  add the folder to the antivirus exclusions or restore from quarantine.
  إنذار مضاد الفيروسات مشكلة منفصلة وشائعة مع PyInstaller — أضف المجلد
  للاستثناءات.

## 3. Checklist before distributing the EXE / قبل توزيع الـ EXE

1. `python run_tests.py` passes (test gate).
2. Build on Windows with `installer\build_exe.bat` (or the x86/x64 one).
3. Optional: `installer\build_obfuscated.bat` for PyArmor obfuscation.
4. Optional: set `CERT_PFX`/`CERT_PASS` and re-run a build script to sign.
5. Create the Desktop shortcut: right-click EXE → Send to → Desktop,
   or run `installer\create_shortcut.vbs` (shortcut carries the logo icon).
6. Tell users about the first-run SmartScreen click ("More info → Run anyway").
