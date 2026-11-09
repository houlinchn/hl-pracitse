from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from conftest import ORIGIN, PASSWORD, applicant, delegate, draft, staff, submitted
from fastapi.testclient import TestClient
from poc.accounts import COOKIE, PERMISSIONS, token_hash
from poc.db import Account, Application, Audit, Credential, SessionLocal, StatusEvent, engine, now
from poc.main import app
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError


def count(db, model, **where):
    return db.scalar(select(func.count()).select_from(model).filter_by(**where))


def test_end_to_end_web_and_ai_same_services(client):
    owner = applicant(client)
    item = draft(client)
    app_id = item["id"]
    assert item["status"] == "draft" and len(item["events"]) == 1
    assert client.get("/api/applications").json()[0]["id"] == app_id
    response = client.patch(
        f"/api/applications/{app_id}",
        json={
            "name": "Alex Edited",
            "contact_email": "edit@example.com",
            "statement": "Edited sample",
            "expected_version": 1,
        },
    )
    assert response.status_code == 200 and response.json()["version"] == 2
    item = client.post(f"/api/applications/{app_id}/submit", json={"expected_version": 2}).json()
    assert item["status"] == "submitted"
    staff_id = staff(client)
    assert client.get("/api/staff/applications").json()[0]["name"] == "Alex Edited"
    grant = delegate(client, application_ids=[app_id])
    headers = {"Authorization": f"Bearer {grant['token']}"}
    web_detail = client.get(f"/api/staff/applications/{app_id}").json()
    ai_detail = client.get(f"/api/ai/applications/{app_id}", headers=headers).json()
    assert web_detail == ai_detail
    assert client.get("/api/ai/applications", headers=headers).json()[0]["id"] == app_id
    advanced = client.post(
        f"/api/ai/applications/{app_id}/advance",
        headers=headers,
        json={"expected_version": 3, "reason": "Sample meets initial criteria"},
    )
    assert advanced.status_code == 200
    assert advanced.json()["status"] == "screening"
    last = advanced.json()["events"][-1]
    assert last["before"] == "submitted" and last["after"] == "screening"
    assert last["actor_id"] == f"ai:{grant['id']}" and last["delegated_by"] == staff_id
    assert last["channel"] == "ai" and last["at"] and last["reason"]
    audits = client.get(f"/api/ai/applications/{app_id}/audit", headers=headers).json()
    record = next(
        row for row in audits if row["action"] == "application.status" and row["channel"] == "ai"
    )
    assert record["data"]["before"] == "submitted" and record["data"]["after"] == "screening"
    assert record["delegated_by"] == staff_id and record["result"] == "success"
    assert grant["token"] not in str(audits) and PASSWORD not in str(audits)
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": owner["email"], "password": PASSWORD})
    assert client.get(f"/api/applications/{app_id}").json()["status"] == "screening"


def test_web_advance_events_and_audit(client):
    applicant(client)
    item = submitted(client)
    staff_id = staff(client)
    response = client.post(
        f"/api/staff/applications/{item['id']}/advance",
        json={"reason": "Web screening reason", "expected_version": 2},
    )
    assert response.status_code == 200
    event = response.json()["events"][-1]
    assert (
        event["actor_id"] == staff_id
        and event["delegated_by"] is None
        and event["channel"] == "web"
    )
    assert client.get(f"/api/staff/applications/{item['id']}/audit").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api/auth/me",
        "/api/applications",
        "/api/staff/applications",
        f"/api/staff/applications/{uuid4()}",
        f"/api/staff/applications/{uuid4()}/audit",
        "/api/ai/applications",
        "/api/delegations",
    ],
)
def test_unauthenticated(client, path):
    assert client.get(path).status_code == 401


def test_registration_cannot_assign_staff_or_actor(client):
    data = {
        "email": "evil@example.com",
        "password": PASSWORD,
        "role": "staff",
        "permissions": list(PERMISSIONS),
    }
    assert client.post("/api/auth/register", json=data).status_code == 422
    who = applicant(client)
    assert who["role"] == "applicant" and who["permissions"] == []
    item = submitted(client)
    assert client.get("/api/staff/applications").status_code == 403
    assert client.get(f"/api/staff/applications/{item['id']}").status_code == 403
    assert client.get(f"/api/staff/applications/{item['id']}/audit").status_code == 403
    assert (
        client.post(
            f"/api/staff/applications/{item['id']}/advance",
            json={"reason": "forged", "expected_version": 2},
            headers={"actor_id": "staff", "delegated_by": "staff"},
        ).status_code
        == 403
    )
    assert (
        client.post("/api/delegations", json={"permissions": list(PERMISSIONS)}).status_code == 403
    )


def test_cross_applicant_read_edit_submit(client):
    applicant(client)
    item = draft(client)
    applicant(client, "other@example.com")
    assert client.get("/api/applications").json() == []
    assert client.get(f"/api/applications/{item['id']}").status_code == 404
    assert (
        client.patch(
            f"/api/applications/{item['id']}",
            json={
                "name": "X",
                "contact_email": "x@example.com",
                "statement": "X",
                "expected_version": 1,
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/applications/{item['id']}/submit", json={"expected_version": 1}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "  "),
        ("name", "x" * 101),
        ("contact_email", "invalid"),
        ("statement", ""),
        ("statement", "x" * 5001),
        ("actor_id", "forged"),
    ],
)
def test_draft_validation(client, field, value):
    applicant(client)
    data = {"name": "Demo", "contact_email": "demo@example.com", "statement": "Sample"}
    data[field] = value
    assert client.post("/api/applications", json=data).status_code == 422
    assert client.get("/api/applications").json() == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"reason": ""},
        {"reason": "   ", "expected_version": 2},
        {"reason": "x" * 1001, "expected_version": 2},
        {"reason": "ok", "expected_version": 0},
        {"reason": "ok", "expected_version": 2, "actor_id": "forged"},
        {"reason": "ok", "expected_version": 2, "delegated_by": "forged"},
        {"reason": "ok", "expected_version": 2, "status": "hired"},
    ],
)
def test_advance_input_validation_and_no_success_records(client, body):
    applicant(client)
    item = submitted(client)
    staff(client)
    for prefix, headers in [
        ("staff", {}),
        ("ai", {"Authorization": f"Bearer {delegate(client)['token']}"}),
    ]:
        response = client.post(
            f"/api/{prefix}/applications/{item['id']}/advance", headers=headers, json=body
        )
        assert response.status_code == 422
    with SessionLocal() as db:
        assert db.get(Application, item["id"]).status == "submitted"
        assert count(db, StatusEvent, application_id=item["id"]) == 2
        assert count(db, Audit, action="application.status", application_id=item["id"]) == 2


def test_delegation_wrong_kind_expired_revoked_invalid_and_no_cookie_fallback(client):
    applicant(client)
    item = submitted(client)
    staff(client)
    session_token = client.cookies.get(COOKIE)
    assert client.get("/api/ai/applications").status_code == 401
    assert (
        client.get(
            "/api/ai/applications", headers={"Authorization": f"Bearer {session_token}"}
        ).status_code
        == 401
    )
    assert (
        client.get("/api/ai/applications", headers={"Authorization": "Bearer invalid"}).status_code
        == 401
    )
    grant = delegate(client)
    headers = {"Authorization": f"Bearer {grant['token']}"}
    with TestClient(app, headers={"Origin": ORIGIN}) as anonymous:
        assert anonymous.get("/api/staff/applications", headers=headers).status_code == 401
        anonymous.cookies.set(COOKIE, grant["token"])
        assert anonymous.get("/api/staff/applications").status_code == 401
    with SessionLocal.begin() as db:
        row = db.scalar(
            select(Credential).where(Credential.token_hash == token_hash(grant["token"]))
        )
        row.expires_at = now() - timedelta(seconds=1)
    assert client.get("/api/ai/applications", headers=headers).status_code == 401
    grant = delegate(client)
    assert client.delete(f"/api/delegations/{grant['id']}").status_code == 204
    assert (
        client.get(
            f"/api/ai/applications/{item['id']}",
            headers={"Authorization": f"Bearer {grant['token']}"},
        ).status_code
        == 401
    )
    assert "token" not in str(client.get("/api/delegations").json())


def test_delegation_cannot_expand_scope_or_current_permissions(client):
    applicant(client)
    item = submitted(client)
    applicant(client, "other@example.com")
    other = submitted(client)
    staff_id = staff(client, scope=[item["id"]])
    assert [row["id"] for row in client.get("/api/staff/applications").json()] == [item["id"]]
    assert client.get(f"/api/staff/applications/{other['id']}").status_code == 404
    assert client.get(f"/api/staff/applications/{other['id']}/audit").status_code == 404
    assert (
        client.post(
            "/api/delegations",
            json={"permissions": ["applications.read"], "application_ids": [other["id"]]},
        ).status_code
        == 403
    )
    grant = delegate(client, permissions=["applications.read"], application_ids=[item["id"]])
    headers = {"Authorization": f"Bearer {grant['token']}"}
    assert client.get(f"/api/ai/applications/{other['id']}", headers=headers).status_code == 404
    assert (
        client.get(f"/api/ai/applications/{item['id']}/audit", headers=headers).status_code == 403
    )
    assert (
        client.post(
            f"/api/ai/applications/{item['id']}/advance",
            headers=headers,
            json={"reason": "No", "expected_version": 2},
        ).status_code
        == 403
    )
    with SessionLocal.begin() as db:
        db.get(Account, staff_id).permissions = []
    assert client.get("/api/ai/applications", headers=headers).status_code == 403
    assert (
        client.post("/api/delegations", json={"permissions": ["applications.read"]}).status_code
        == 403
    )
    with SessionLocal.begin() as db:
        db.get(Account, staff_id).active = False
    assert client.get("/api/ai/applications", headers=headers).status_code == 401


def test_empty_scope_and_delegation_narrower_than_staff(client):
    applicant(client)
    item = submitted(client)
    staff(client)
    grant = delegate(client, application_ids=[])
    headers = {"Authorization": f"Bearer {grant['token']}"}
    assert client.get("/api/ai/applications", headers=headers).json() == []
    assert client.get(f"/api/ai/applications/{item['id']}", headers=headers).status_code == 404
    assert (
        client.get(f"/api/ai/applications/{item['id']}/audit", headers=headers).status_code == 404
    )
    assert (
        client.post(
            f"/api/ai/applications/{item['id']}/advance",
            headers=headers,
            json={"expected_version": 2, "reason": "Denied"},
        ).status_code
        == 404
    )
    assert client.get(f"/api/staff/applications/{item['id']}").status_code == 200


def test_drafts_private_and_staff_cannot_create(client):
    applicant(client)
    item = draft(client)
    staff(client)
    assert client.get("/api/staff/applications").json() == []
    assert client.get(f"/api/staff/applications/{item['id']}").status_code == 404
    assert (
        client.post(
            "/api/applications",
            json={"name": "Demo", "contact_email": "demo@example.com", "statement": "Sample"},
        ).status_code
        == 403
    )
    grant = delegate(client)
    assert (
        client.get(
            f"/api/ai/applications/{item['id']}",
            headers={"Authorization": f"Bearer {grant['token']}"},
        ).status_code
        == 404
    )


def test_duplicate_create_submit_and_illegal_edits(client):
    applicant(client)
    item = draft(client)
    assert (
        client.post(
            "/api/applications",
            json={"name": "Demo", "contact_email": "demo@example.com", "statement": "Again"},
        ).status_code
        == 409
    )
    path = f"/api/applications/{item['id']}"
    assert client.post(path + "/submit", json={"expected_version": 1}).status_code == 200
    assert client.post(path + "/submit", json={"expected_version": 1}).status_code == 409
    assert client.post(path + "/submit", json={"expected_version": 2}).status_code == 409
    assert (
        client.patch(
            path,
            json={
                "name": "Demo",
                "contact_email": "demo@example.com",
                "statement": "Again",
                "expected_version": 2,
            },
        ).status_code
        == 409
    )
    staff(client)
    advance_path = f"/api/staff/applications/{item['id']}/advance"
    assert (
        client.post(advance_path, json={"expected_version": 2, "reason": "Sample"}).status_code
        == 200
    )
    assert (
        client.post(advance_path, json={"expected_version": 3, "reason": "Again"}).status_code
        == 409
    )


@pytest.mark.parametrize("operation", ["create", "submit", "advance", "edit"])
def test_concurrent_writers_commit_once(client, operation):
    applicant(client)
    if operation == "create":
        path = "/api/applications"
        body = {"name": "Demo", "contact_email": "demo@example.com", "statement": "Sample"}
        method = "POST"
    else:
        item = draft(client) if operation in {"submit", "edit"} else submitted(client)
        method = "PATCH" if operation == "edit" else "POST"
        if operation == "advance":
            staff(client)
            path = f"/api/staff/applications/{item['id']}/advance"
            body = {"expected_version": 2, "reason": "Concurrent sample"}
        elif operation == "edit":
            path = f"/api/applications/{item['id']}"
            body = {
                "expected_version": 1,
                "name": "Changed",
                "contact_email": "demo@example.com",
                "statement": "Sample",
            }
        else:
            path = f"/api/applications/{item['id']}/submit"
            body = {"expected_version": 1}
    cookie = client.cookies.get(COOKIE)

    def call(_):
        with TestClient(
            app, headers={"Origin": ORIGIN, "Cookie": f"{COOKIE}={cookie}"}
        ) as concurrent_client:
            return concurrent_client.request(method, path, json=body).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(call, range(4)))
    assert sorted(codes) == [201 if operation == "create" else 200, 409, 409, 409]
    with SessionLocal() as db:
        if operation == "create":
            assert count(db, Application) == 1 and count(db, StatusEvent) == 1
        elif operation == "edit":
            assert db.get(Application, item["id"]).version == 2
            assert count(db, Audit, action="application.edit") == 1
        else:
            assert count(db, StatusEvent, application_id=item["id"]) == (
                3 if operation == "advance" else 2
            )


def test_database_failure_rolls_back_state_event_and_audit(client):
    applicant(client)
    item = draft(client)
    with engine.begin() as conn:
        conn.execute(
            text("""CREATE OR REPLACE FUNCTION simulate_poc_failure() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN IF NEW.action = 'application.status' THEN RAISE EXCEPTION 'simulated audit insert failure'; END IF; RETURN NEW; END; $$""")
        )
        conn.execute(
            text(
                "CREATE TRIGGER simulate_failure BEFORE INSERT ON audit_records FOR EACH ROW EXECUTE FUNCTION simulate_poc_failure()"
            )
        )
    response = client.post(f"/api/applications/{item['id']}/submit", json={"expected_version": 1})
    assert response.status_code == 503
    with SessionLocal() as db:
        state = db.get(Application, item["id"])
        assert state.status == "draft" and state.version == 1
        assert count(db, StatusEvent, application_id=item["id"]) == 1
        assert count(db, Audit, action="application.status", application_id=item["id"]) == 1


@pytest.mark.parametrize("model", [Audit, StatusEvent])
def test_history_immutable_in_postgres(client, model):
    applicant(client)
    draft(client)
    with pytest.raises(DBAPIError), SessionLocal.begin() as db:
        db.execute(update(model).values(actor_id="tampered"))
    with pytest.raises(DBAPIError), SessionLocal.begin() as db:
        db.execute(text(f"DELETE FROM {model.__tablename__}"))


def test_auth_validation_redaction_duplicate_email_and_logout(client):
    secret = "too-short"
    response = client.post("/api/auth/register", json={"email": "not-an-email", "password": secret})
    assert response.status_code == 422 and secret not in response.text
    assert (
        client.post(
            "/api/auth/login", json={"email": "absent@example.com", "password": PASSWORD}
        ).status_code
        == 401
    )
    account = applicant(client, "ALEX@example.com")
    assert account["email"] == "alex@example.com"
    assert (
        client.post(
            "/api/auth/register", json={"email": "alex@example.com", "password": PASSWORD}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "alex@example.com", "password": PASSWORD + "wrong"}
        ).status_code
        == 401
    )
    token = client.cookies.get(COOKIE)
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me", headers={"Cookie": f"{COOKIE}={token}"}).status_code == 401
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(Credential).where(Credential.token_hash == token_hash(token))
            ).token_hash
            != token
        )
        assert PASSWORD not in str([row.data for row in db.scalars(select(Audit)).all()])
        assert secret not in str([row.data for row in db.scalars(select(Audit)).all()])


def test_csrf_and_invalid_pagination(client):
    assert (
        client.post(
            "/api/auth/register",
            headers={"Origin": "https://evil.example"},
            json={"email": "x@example.com", "password": PASSWORD},
        ).status_code
        == 403
    )
    staff(client)
    for query in ["limit=101", "limit=0", "offset=-1", "status=hired"]:
        assert client.get("/api/staff/applications?" + query).status_code == 422
    assert client.get("/api/staff/applications").json() == []
    assert client.get(f"/api/staff/applications/{uuid4()}").status_code == 404


def test_delegation_other_staff_cannot_revoke_and_cannot_redelegate(client):
    staff(client)
    grant = delegate(client)
    with TestClient(app, headers={"Origin": ORIGIN}) as ai_client:
        assert (
            ai_client.post(
                "/api/delegations",
                headers={"Authorization": f"Bearer {grant['token']}"},
                json={"permissions": ["applications.read"]},
            ).status_code
            == 401
        )
    staff(client, email="second-staff@example.com")
    assert client.delete(f"/api/delegations/{grant['id']}").status_code == 404
    assert client.get("/api/delegations").json() == []


def test_openapi_capability_parity(client):
    paths = client.get("/openapi.json").json()["paths"]
    for suffix in [
        "/applications",
        "/applications/{application_id}",
        "/applications/{application_id}/advance",
        "/applications/{application_id}/audit",
    ]:
        assert paths[f"/api/staff{suffix}"].keys() == paths[f"/api/ai{suffix}"].keys()
        for method in paths[f"/api/staff{suffix}"]:

            def without_titles(value):
                if isinstance(value, dict):
                    return {k: without_titles(v) for k, v in value.items() if k != "title"}
                if isinstance(value, list):
                    return [without_titles(item) for item in value]
                return value

            assert without_titles(
                paths[f"/api/staff{suffix}"][method]["responses"]
            ) == without_titles(paths[f"/api/ai{suffix}"][method]["responses"])
            expected = "WebSession"
            assert paths[f"/api/staff{suffix}"][method]["security"] == [{expected: []}]
            assert paths[f"/api/ai{suffix}"][method]["security"] == [{"AIDelegation": []}]


def test_session_expiry_and_staff_permissions_independent(client):
    applicant(client)
    item = submitted(client)
    staff(client, permissions=["applications.read"])
    assert client.get(f"/api/staff/applications/{item['id']}").status_code == 200
    assert client.get(f"/api/staff/applications/{item['id']}/audit").status_code == 403
    assert (
        client.post(
            f"/api/staff/applications/{item['id']}/advance",
            json={"expected_version": 2, "reason": "Denied"},
        ).status_code
        == 403
    )
    token = client.cookies.get(COOKIE)
    with SessionLocal.begin() as db:
        credential = db.scalar(select(Credential).where(Credential.token_hash == token_hash(token)))
        credential.expires_at = now() - timedelta(seconds=1)
    assert client.get("/api/auth/me").status_code == 401


def test_existing_delegation_respects_new_object_scope(client):
    applicant(client)
    item = submitted(client)
    staff_id = staff(client)
    grant = delegate(client)
    headers = {"Authorization": f"Bearer {grant['token']}"}
    assert client.get(f"/api/ai/applications/{item['id']}", headers=headers).status_code == 200
    with SessionLocal.begin() as db:
        db.get(Account, staff_id).application_scope = []
    assert client.get("/api/ai/applications", headers=headers).json() == []
    assert client.get(f"/api/ai/applications/{item['id']}", headers=headers).status_code == 404
    assert (
        client.get(f"/api/ai/applications/{item['id']}/audit", headers=headers).status_code == 404
    )
    assert (
        client.post(
            f"/api/ai/applications/{item['id']}/advance",
            headers=headers,
            json={"expected_version": 2, "reason": "Denied"},
        ).status_code
        == 404
    )


def test_web_and_ai_concurrent_advance(client):
    applicant(client)
    item = submitted(client)
    staff(client)
    grant = delegate(client)
    cookie = client.cookies.get(COOKIE)

    def call(index):
        ai = bool(index % 2)
        headers = (
            {"Authorization": f"Bearer {grant['token']}"}
            if ai
            else {"Cookie": f"{COOKIE}={cookie}"}
        )
        with TestClient(app, headers={"Origin": ORIGIN, **headers}) as concurrent:
            return concurrent.post(
                f"/api/{'ai' if ai else 'staff'}/applications/{item['id']}/advance",
                json={"expected_version": 2, "reason": "Mixed concurrency"},
            ).status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = list(pool.map(call, range(4)))
    assert sorted(codes) == [200, 409, 409, 409]
    with SessionLocal() as db:
        assert count(db, StatusEvent, application_id=item["id"]) == 3
        assert count(db, Audit, application_id=item["id"], action="application.status") == 3
