"""Round 44 strings: the semi-automatic update notice + dialog.
EN + AR dicts with a local reader (same pattern as strings_r41:
prefer these dicts, then EN, then t())."""
from src.config.strings import t

EN = {
    "update.available": "New version available",
    "update.title": "Update available",
    "update.body": ("Version {version} is ready. Downloading takes a "
                    "moment; then the installer runs and the app "
                    "restarts with the new version. Your patients, "
                    "settings and data are never touched."),
    "update.download": "Download & install",
    "update.later": "Later",
    "update.downloading": "Downloading…",
    "update.installing": "Starting the installer…",
    "update.failed": ("The download did not complete. Nothing was "
                      "installed — please try again later."),
    "update.invalid": ("The downloaded file failed the safety check, "
                       "so it was deleted and nothing was installed."),
}

AR = {
    "update.available": "يتوفر إصدار جديد",
    "update.title": "يتوفر تحديث",
    "update.body": ("الإصدار {version} جاهز. يستغرق التنزيل لحظات، ثم "
                    "يعمل المثبّت ويُعاد تشغيل التطبيق بالإصدار الجديد. "
                    "مرضاك وإعداداتك وبياناتك لا تُمسّ أبداً."),
    "update.download": "تنزيل وتثبيت",
    "update.later": "لاحقاً",
    "update.downloading": "جارٍ التنزيل…",
    "update.installing": "جارٍ تشغيل المثبّت…",
    "update.failed": ("لم يكتمل التنزيل. لم يُثبَّت أي شيء — حاول "
                      "مرة أخرى لاحقاً."),
    "update.invalid": ("لم يجتز الملف المنزَّل فحص السلامة، فحُذف "
                       "ولم يُثبَّت أي شيء."),
}


def r44_t(key, lang="en"):
    """Round-44 string: this module first, then t()."""
    d = AR if lang == "ar" else EN
    return d.get(key) or EN.get(key) or t(key, lang)
