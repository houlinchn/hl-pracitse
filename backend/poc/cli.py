"""Explicit initialization only. No built-in accounts or default passwords."""

import argparse
import getpass
import os
from pathlib import Path

from sqlalchemy import select, text

from .accounts import PERMISSIONS, password_hash
from .db import Account, Audit, Base, SessionLocal, engine


def init_db():
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text("""
            CREATE OR REPLACE FUNCTION poc_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'POC history is append-only'; END; $$
        """)
        )
        for table in ("status_events", "audit_records"):
            connection.execute(text(f"DROP TRIGGER IF EXISTS append_only ON {table}"))
            connection.execute(
                text(
                    f"CREATE TRIGGER append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION poc_append_only()"
                )
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db")
    staff = sub.add_parser("create-staff")
    staff.add_argument("--email", required=True)
    staff.add_argument("--password-file")
    staff.add_argument("--permission", choices=sorted(PERMISSIONS), action="append", required=True)
    staff.add_argument(
        "--application-id", action="append", help="Optional restricted application scope"
    )
    args = parser.parse_args()
    if args.command == "init-db":
        init_db()
        print("POC schema initialized; no existing data removed.")
        return
    from pydantic import EmailStr, TypeAdapter

    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    if args.password_file:
        path = Path(args.password_file)
        if path.stat().st_mode & 0o077 or path.stat().st_uid != os.getuid():
            parser.error("Password file must be owned by current user with mode 600")
        password = path.read_text().strip()
    else:
        password = getpass.getpass("New staff password (12–128 characters): ")
        if password != getpass.getpass("Repeat password: "):
            parser.error("Passwords do not match")
    if not 12 <= len(password) <= 128:
        parser.error("Password must have 12–128 characters")
    if args.application_id:
        from uuid import UUID

        scope = [str(UUID(value)) for value in args.application_id]
    else:
        scope = None
    with SessionLocal.begin() as db:
        if db.scalar(select(Account).where(Account.email == email)):
            parser.error("Account already exists; no password or role changed")
        account = Account(
            email=email,
            password_hash=password_hash(password),
            role="staff",
            permissions=sorted(set(args.permission)),
            application_scope=scope,
        )
        db.add(account)
        db.flush()
        db.add(
            Audit(
                actor_id="system:explicit-cli",
                channel="cli",
                action="staff.create",
                data={
                    "account_id": account.id,
                    "permissions": account.permissions,
                    "application_ids": scope,
                },
            )
        )
    print("Staff account created. Password was not printed or stored in audit.")


if __name__ == "__main__":
    main()
