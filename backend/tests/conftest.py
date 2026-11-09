import os
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

url = make_url(os.environ["TEST_DATABASE_URL"])
if (url.host, url.port, url.database, url.username) != (
    "127.0.0.1",
    13082,
    "recruitment_poc_test",
    "poc",
):
    raise RuntimeError(
        "Tests may only use the isolated recruitment_poc_test database on 127.0.0.1:13082"
    )
os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)

from poc.accounts import PERMISSIONS, password_hash  # noqa: E402
from poc.cli import init_db  # noqa: E402
from poc.db import Account, SessionLocal, engine  # noqa: E402
from poc.main import app  # noqa: E402

PASSWORD = secrets.token_urlsafe(24)
ORIGIN = "http://127.0.0.1:13080"


@pytest.fixture(autouse=True)
def clean_database():
    init_db()
    with engine.begin() as connection:
        connection.execute(text("DROP TRIGGER IF EXISTS simulate_failure ON audit_records"))
        connection.execute(
            text(
                "TRUNCATE audit_records, status_events, credentials, applications, accounts CASCADE"
            )
        )
    yield


@pytest.fixture
def client():
    with TestClient(app, headers={"Origin": ORIGIN}) as client:
        yield client


def applicant(client, email="alex@example.com"):
    response = client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()


def staff(client, permissions=None, scope=None, email="staff@example.com"):
    with SessionLocal.begin() as db:
        account = Account(
            email=email,
            password_hash=password_hash(PASSWORD),
            role="staff",
            permissions=sorted(PERMISSIONS if permissions is None else permissions),
            application_scope=scope,
        )
        db.add(account)
        db.flush()
        account_id = account.id
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return account_id


def draft(client):
    response = client.post(
        "/api/applications",
        json={
            "name": "Alex Demo",
            "contact_email": "alex@example.com",
            "statement": "Demonstration teaching application.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def submitted(client):
    application = draft(client)
    response = client.post(
        f"/api/applications/{application['id']}/submit",
        json={"expected_version": application["version"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def delegate(client, permissions=None, application_ids=None):
    response = client.post(
        "/api/delegations",
        json={
            "permissions": sorted(PERMISSIONS if permissions is None else permissions),
            "application_ids": application_ids,
            "minutes": 15,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
