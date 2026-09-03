# Lesson: Installer config encoding

Windows PowerShell `Set-Content -Encoding UTF8` may write BOM and break `json.loads`. Write config via Python (`scripts/write_install_config.py`) and read with `utf-8-sig`.
