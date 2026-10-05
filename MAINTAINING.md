# Maintaining · Release Checklist / 维护者发布清单

## Release checklist
1. Build release APKs (keystore required; a DEBUG-key fallback prints an explicit warning).
2. Run desktop tests: `cd desktop && python -m pytest tests/`.
3. Compute checksums:
   - `certutil -hashfile RealtimeVoiceChat-vX.Y.apk SHA256`
   - `certutil -hashfile RealtimeVoiceChat-vX.Y-Windows.zip SHA256`
4. Update the README "Checksums" section **and** paste the same hashes into the GitHub Release notes.
5. `git tag vX.Y && git push origin vX.Y`; create the Release; attach the APK + Windows zip.

## Policies / 政策
- **Windows code signing (Authenticode): intentionally NOT used.** A paid certificate is out of scope for a
  personal open-source project, and a self-signed certificate adds nothing at user privilege level
  (the client is a non-elevating user-mode program: users see only the standard SmartScreen prompt,
  never an "untrusted publisher" UAC dialog). Integrity is ensured by the published SHA-256 hashes —
  **hashes are mandatory for every release**, not optional.
- **Reproducibility**: builds use Python 3.11.9 (64-bit Windows) with `desktop/requirements.txt` pinned;
  hashes are specific to the build environment.
- **Credentials**: Android stores them encrypted (AES-GCM + Android Keystore); the desktop keeps
  `config.local.json` in cleartext (accepted trade-off: malware running as the same user could read
  either form). `config.json` / `config.local.json` are git-ignored — **never commit them**.
- **Never publish**: the trial APK (contains bundled credentials), keystore files, or logs.
