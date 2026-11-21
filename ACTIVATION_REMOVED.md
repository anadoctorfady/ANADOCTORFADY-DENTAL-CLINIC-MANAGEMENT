# Activation — REMOVED / تم إلغاء التفعيل

**Owner decision, 2026-11-05:** activation was removed entirely from
ANADOCTORFADY. The app is **auto-activated** — it opens straight to the
login screen (default `fady / 1234`), with no activation window, no Machine
ID, no activation code, and no secret anywhere.

- Deleted: `src/models/activation.py`, `src/ui/activation_ui.py`,
  `tools/generate_activation.py`, `activation_secret.EXAMPLE.txt`,
  `ACTIVATION.md`, `tests/test_activation.py`.
- The old offline-HMAC activation could never succeed in a shipped build
  (the secret was never inside the EXE) — that bug is now moot: there is
  nothing left to verify, no secret, and no HMAC in the app.
- The app is completely free, as stated in About / حول (sadaqah jariyah
  for Doctor Fady Abdulkafy Dadoush and his parents, wife and children).
- Guard: `tests/test_no_activation.py` fails the gate if any activation
  code, HMAC, or Machine ID ever comes back into `src/`.
