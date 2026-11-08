"""Real HTTP + PostgreSQL smoke. Credentials remain in memory; only demo accounts are created."""

import secrets
import subprocess
import sys
from pathlib import Path

import httpx

base = "http://127.0.0.1:13080"
headers = {"Origin": base}
suffix = secrets.token_hex(6)
password = secrets.token_urlsafe(24)
with (
    httpx.Client(base_url=base, headers=headers) as applicant,
    httpx.Client(base_url=base, headers=headers) as staff,
):
    assert applicant.get("/api/health").json()["status"] == "ok"
    response = applicant.post(
        "/api/auth/register", json={"email": f"smoke-{suffix}@example.com", "password": password}
    )
    assert response.status_code == 201
    response = applicant.post(
        "/api/applications",
        json={
            "name": f"Smoke Demo {suffix}",
            "contact_email": f"smoke-{suffix}@example.com",
            "statement": "Synthetic network smoke data only.",
        },
    )
    assert response.status_code == 201
    item = response.json()
    app_id = item["id"]
    assert (
        applicant.post(
            f"/api/applications/{app_id}/submit", json={"expected_version": 1}
        ).status_code
        == 200
    )
    if "--restart" in sys.argv:
        subprocess.run(["docker", "compose", "-p", "hl-pracitse-poc", "stop"], check=True)
        subprocess.run(
            ["docker", "compose", "-p", "hl-pracitse-poc", "up", "-d", "--wait"], check=True
        )
        persisted = applicant.get(f"/api/applications/{app_id}")
        assert persisted.status_code == 200 and persisted.json()["status"] == "submitted"
        print("PASS: full POC stop/start preserves applicant session and submitted data")
    response = staff.post(
        "/api/auth/login",
        json={
            "email": "staff@example.com",
            "password": (Path(__file__).resolve().parents[1] / ".local/staff-password")
            .read_text()
            .strip(),
        },
    )
    assert response.status_code == 200
    staff_id = response.json()["id"]
    response = staff.post(
        "/api/delegations",
        json={
            "permissions": ["applications.read", "applications.advance", "audit.read"],
            "application_ids": [app_id],
            "minutes": 1,
        },
    )
    assert response.status_code == 201
    grant = response.json()
    auth = {"Authorization": f"Bearer {grant['token']}"}
    assert staff.get("/api/ai/applications", headers=auth).json()[0]["id"] == app_id
    assert (
        staff.get(f"/api/ai/applications/{app_id}", headers=auth).json()
        == staff.get(f"/api/staff/applications/{app_id}").json()
    )
    assert (
        staff.post(
            f"/api/ai/applications/{app_id}/advance",
            headers=auth,
            json={"expected_version": 2, "reason": "Synthetic network smoke initial screening"},
        ).status_code
        == 200
    )
    assert staff.get(f"/api/staff/applications/{app_id}").json()["status"] == "screening"
    assert applicant.get(f"/api/applications/{app_id}").json()["status"] == "screening"
    rows = staff.get(f"/api/ai/applications/{app_id}/audit", headers=auth).json()
    assert any(
        row["channel"] == "ai"
        and row["delegated_by"] == staff_id
        and row["action"] == "application.status"
        for row in rows
    )
    assert staff.delete(f"/api/delegations/{grant['id']}").status_code == 204
    assert staff.get("/api/ai/applications", headers=auth).status_code == 401
    assert staff.post("/api/auth/logout").status_code == 204
    assert applicant.post("/api/auth/logout").status_code == 204
print(
    "PASS: real HTTP applicant → submit → staff read → delegated AI screening → shared persistence → audit → revoke/logout"
)
