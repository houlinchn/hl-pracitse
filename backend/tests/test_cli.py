import os
import subprocess
import sys

from conftest import PASSWORD
from poc.db import Account, Audit, SessionLocal
from sqlalchemy import select


def invoke(*args):
    return subprocess.run(
        [sys.executable, "-m", "poc.cli", *args], capture_output=True, text=True, env=os.environ
    )


def test_explicit_staff_initialization_and_no_default_accounts(tmp_path):
    with SessionLocal() as db:
        assert db.scalars(select(Account)).all() == []
    path = tmp_path / "password"
    path.write_text(PASSWORD)
    path.chmod(0o600)
    args = [
        "create-staff",
        "--email",
        "cli@example.com",
        "--password-file",
        str(path),
        "--permission",
        "applications.read",
    ]
    result = invoke(*args)
    assert result.returncode == 0 and PASSWORD not in result.stdout + result.stderr
    with SessionLocal() as db:
        account = db.scalar(select(Account))
        assert account.role == "staff" and account.permissions == ["applications.read"]
        assert account.password_hash != PASSWORD
        audit = db.scalar(select(Audit))
        assert audit.actor_id == "system:explicit-cli" and audit.action == "staff.create"
        assert PASSWORD not in str(audit.data)
    assert invoke(*args).returncode != 0
    with SessionLocal() as db:
        assert len(db.scalars(select(Account)).all()) == 1


def test_cli_rejects_readable_password_file_and_invalid_permission(tmp_path):
    path = tmp_path / "password"
    path.write_text(PASSWORD)
    path.chmod(0o644)
    result = invoke(
        "create-staff",
        "--email",
        "cli@example.com",
        "--password-file",
        str(path),
        "--permission",
        "applications.read",
    )
    assert result.returncode != 0 and PASSWORD not in result.stderr
    assert (
        invoke(
            "create-staff", "--email", "cli@example.com", "--permission", "payroll.approve"
        ).returncode
        != 0
    )
    with SessionLocal() as db:
        assert db.scalars(select(Account)).all() == []
