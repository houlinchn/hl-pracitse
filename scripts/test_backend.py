"""Run PostgreSQL tests only against this POC's separate test database."""

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

root = Path(__file__).resolve().parents[1]
url = make_url(os.environ["DATABASE_URL"])
if (url.host, url.port, url.database, url.username) != (
    "127.0.0.1",
    13082,
    "recruitment_poc",
    "poc",
):
    sys.exit("Refusing to prepare tests outside the documented isolated local POC database")
test_url = url.set(database="recruitment_poc_test")
with psycopg.connect(
    url.set(drivername="postgresql").render_as_string(hide_password=False),
    autocommit=True,
) as conn:
    if not conn.execute(
        "SELECT 1 FROM pg_database WHERE datname='recruitment_poc_test'"
    ).fetchone():
        conn.execute("CREATE DATABASE recruitment_poc_test")
env = dict(os.environ, TEST_DATABASE_URL=test_url.render_as_string(hide_password=False))
raise SystemExit(
    subprocess.call(
        [sys.executable, "-m", "pytest", "-q", *sys.argv[1:]],
        cwd=root / "backend",
        env=env,
    )
)
