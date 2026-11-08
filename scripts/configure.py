#!/usr/bin/env python3
"""Generate local-only credentials, never print secrets or overwrite existing ones."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.umask(0o077)
(root / ".local").mkdir(exist_ok=True, mode=0o700)
path = root / ".env"
if not path.exists():
    password = secrets.token_hex(24)
    with path.open("x") as file:
        file.write(
            f"POSTGRES_PASSWORD={password}\nDATABASE_URL=postgresql+psycopg://poc:{password}@127.0.0.1:13082/recruitment_poc\nAPP_ORIGIN=http://127.0.0.1:13080\nCOOKIE_SECURE=false\n"
        )
path.chmod(0o600)
password_file = root / ".local/staff-password"
if not password_file.exists():
    with password_file.open("x") as file:
        file.write(secrets.token_urlsafe(24) + "\n")
password_file.chmod(0o600)
print(
    "Local credentials ready in ignored mode-600 files: .env and .local/staff-password (not printed)."
)
