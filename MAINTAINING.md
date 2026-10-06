# Maintaining · Release Checklist / 维护者发布清单

## Release checklist
1. Build release APKs (keystore required; a DEBUG-key fallback prints an explicit warning).
2. Run desktop tests: `cd desktop && python -m pytest tests/`.
3. Compute checksums **for local records only**:
   - `certutil -hashfile RealtimeVoiceChat-vX.Y.apk SHA256`
   - `certutil -hashfile RealtimeVoiceChat-vX.Y-Windows.zip SHA256`
4. `git tag vX.Y && git push origin vX.Y`; create the Release **as version notes only**.

> **No prebuilt binaries are attached to public Releases.** This is a personal, non-commercial
> learning project; per China's app-filing (备案) rules, unfiled apps must not be publicly
> distributed — so the repo stays source-only and users build their own binaries.
> Built packages live in the maintainer's private archive, hashed, never attached here.

## Policies / 政策
- **No public binary distribution**: the repo and Releases are source/notes only (see the box above).
  Integrity checking applies to privately shared builds — always attach the SHA-256 when sending
  a package to someone directly.
- **Windows code signing (Authenticode): intentionally NOT used.** A paid certificate is out of scope for a
  personal open-source project, and a self-signed certificate adds nothing at user privilege level
  (the client is a non-elevating user-mode program: users see only the standard SmartScreen prompt,
  never an "untrusted publisher" UAC dialog).
- **Reproducibility**: builds use Python 3.11.9 (64-bit Windows) with `desktop/requirements.txt` pinned;
  hashes are specific to the build environment.
- **Credentials**: Android stores them encrypted (AES-GCM + Android Keystore); on Windows the desktop
  stores them in the **Windows Credential Manager** (system-encrypted, via ctypes — no extra
  dependency), falling back to `config.local.json` in cleartext only if that write fails or on
  non-Windows systems (accepted trade-off: malware running as the same user could read either form).
  `config.json` / `config.local.json` are git-ignored — **never commit them**.
- **Never publish**: the trial APK (contains bundled credentials), keystore files, or logs.
