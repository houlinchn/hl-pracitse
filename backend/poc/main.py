import os
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import applications as service
from .accounts import (
    COOKIE,
    Context,
    audit,
    authenticate,
    issue_credential,
    password_hash,
    password_matches,
)
from .db import Account, Audit, Credential, SessionLocal, get_db, now
from .schemas import (
    AccountOut,
    AdvanceInput,
    ApplicationOut,
    AuditOut,
    AuthInput,
    DelegationInput,
    DraftInput,
    EditInput,
    ErrorOut,
    VersionInput,
)

app = FastAPI(
    title="Teacher Operations · Recruitment POC",
    version="0.1.0",
    responses={code: {"model": ErrorOut} for code in (401, 403, 404, 409, 422, 503)},
    description="演示数据专用；三状态招聘闭环。AI 使用短期、受限、可撤销的 Bearer 委托令牌。",
)
DB = Annotated[Session, Depends(get_db, scope="function")]
ORIGIN = os.environ.get("APP_ORIGIN", "http://127.0.0.1:13080")


@app.middleware("http")
async def security(request, call_next):
    # Same-origin UI proxy; no permissive CORS. Bearer AI routes never authenticate cookies.
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and not request.url.path.startswith("/api/ai/")
        and request.headers.get("origin") != ORIGIN
    ):
        return JSONResponse({"detail": "请求来源校验失败"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def record_denied(request, status):
    identity = getattr(request.state, "identity", ("anonymous", None, "web"))
    try:
        with SessionLocal.begin() as db:
            db.add(
                Audit(
                    actor_id=identity[0],
                    delegated_by=identity[1],
                    channel=identity[2],
                    action="request.denied",
                    result="denied",
                    data={"method": request.method, "path": request.url.path, "status": status},
                )
            )
    except SQLAlchemyError:
        pass  # A database outage must not expose credentials or replace the original error.


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    record_denied(request, exc.status_code)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def invalid_input(request, exc):
    record_denied(request, 422)
    # Pydantic's default errors echo raw input, including passwords. Return field names only.
    fields = [".".join(map(str, error["loc"][1:])) for error in exc.errors()]
    return JSONResponse(
        {"detail": "输入不符合要求，请检查字段长度、格式及必填项", "fields": fields},
        status_code=422,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse({"detail": "数据库操作失败，未保存本次更改，请稍后重试"}, status_code=503)


def context(ai=False):
    scheme = (
        HTTPBearer(auto_error=False, scheme_name="AIDelegation")
        if ai
        else APIKeyCookie(name=COOKIE, auto_error=False, scheme_name="WebSession")
    )

    def dependency(request: Request, db: DB, credential: Annotated[object, Security(scheme)]):
        ctx = authenticate(db, request, ai=ai)
        request.state.identity = (ctx.actor_id, ctx.delegated_by, ctx.channel)
        return ctx

    return dependency


WEB = Annotated[Context, Depends(context())]


def account_view(account):
    return {
        "id": account.id,
        "email": account.email,
        "role": account.role,
        "permissions": account.permissions,
    }


def set_session(response, token):
    response.set_cookie(
        COOKIE,
        token,
        max_age=8 * 3600,
        httponly=True,
        samesite="strict",
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        path="/api",
    )


@app.get("/api/health")
def health(db: DB):
    db.execute(select(1))
    return {"status": "ok", "mode": "demo-poc"}


@app.post("/api/auth/register", response_model=AccountOut, status_code=201)
def register(data: AuthInput, response: Response, db: DB):
    # Serialize equal-email registration, including concurrent requests, without IntegrityError leaks.
    from sqlalchemy import text

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:email, 0))"), {"email": data.email}
    )
    if db.scalar(select(Account).where(Account.email == data.email)):
        raise HTTPException(409, "此邮箱无法注册，请登录或使用其他演示邮箱")
    account = Account(
        email=data.email,
        password_hash=password_hash(data.password),
        role="applicant",
        permissions=[],
    )
    db.add(account)
    db.flush()
    token, credential = issue_credential(db, account)
    audit(db, Context(account, credential, "web"), "account.register")
    set_session(response, token)
    return account_view(account)


# Fixed dummy hash equalizes missing-account and wrong-password work without storing a default password.
DUMMY_HASH = password_hash(os.urandom(32).hex())


@app.post("/api/auth/login", response_model=AccountOut)
def login(data: AuthInput, response: Response, db: DB):
    account = db.scalar(select(Account).where(Account.email == data.email))
    valid = password_matches(data.password, account.password_hash if account else DUMMY_HASH)
    if not account or not valid or not account.active:
        raise HTTPException(401, "邮箱或密码不正确")
    token, credential = issue_credential(db, account)
    audit(db, Context(account, credential, "web"), "account.login")
    set_session(response, token)
    return account_view(account)


@app.get("/api/auth/me", response_model=AccountOut)
def me(ctx: WEB):
    return account_view(ctx.account)


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response, db: DB, ctx: WEB):
    ctx.credential.revoked = True
    audit(db, ctx, "account.logout")
    response.delete_cookie(COOKIE, path="/api")


@app.get("/api/applications", response_model=list[ApplicationOut])
def own_list(db: DB, ctx: WEB):
    return service.list_own(db, ctx)


@app.post("/api/applications", response_model=ApplicationOut, status_code=201)
def create(data: DraftInput, db: DB, ctx: WEB):
    return service.create(db, ctx, data)


@app.get("/api/applications/{application_id}", response_model=ApplicationOut)
def own_detail(application_id: UUID, db: DB, ctx: WEB):
    return service.own_detail(db, ctx, str(application_id))


@app.patch("/api/applications/{application_id}", response_model=ApplicationOut)
def edit(application_id: UUID, data: EditInput, db: DB, ctx: WEB):
    return service.edit(db, ctx, str(application_id), data)


@app.post("/api/applications/{application_id}/submit", response_model=ApplicationOut)
def submit(application_id: UUID, data: VersionInput, db: DB, ctx: WEB):
    return service.transition(db, ctx, str(application_id), data)


# Both transport adapters bind the exact same service functions and response contracts.
for prefix, ai in [("/api/staff", False), ("/api/ai", True)]:
    router = APIRouter(
        prefix=prefix, tags=["AI delegated capabilities" if ai else "Staff capabilities"]
    )
    CTX = Annotated[Context, Depends(context(ai))]

    @router.get("/applications", response_model=list[ApplicationOut])
    def staff_list(
        db: DB,
        ctx: CTX,
        status: Literal["submitted", "screening"] | None = None,
        offset: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
    ):
        return service.list_staff(db, ctx, status, offset, limit)

    @router.get("/applications/{application_id}", response_model=ApplicationOut)
    def staff_detail(application_id: UUID, db: DB, ctx: CTX):
        return service.detail_staff(db, ctx, str(application_id))

    @router.post("/applications/{application_id}/advance", response_model=ApplicationOut)
    def advance(application_id: UUID, data: AdvanceInput, db: DB, ctx: CTX):
        return service.transition(db, ctx, str(application_id), data, staff=True)

    @router.get("/applications/{application_id}/audit", response_model=list[AuditOut])
    def audits(application_id: UUID, db: DB, ctx: CTX):
        return service.read_audit(db, ctx, str(application_id))

    app.include_router(router)


@app.post("/api/delegations", status_code=201)
def delegate(data: DelegationInput, db: DB, ctx: WEB):
    if ctx.account.role != "staff" or not set(data.permissions) <= ctx.permissions:
        raise HTTPException(403, "委托权限不能超出本人权限")
    scope = (
        [str(value) for value in data.application_ids]
        if data.application_ids is not None
        else ctx.account.application_scope
    )
    if ctx.account.application_scope is not None and (
        scope is None or not set(scope) <= set(ctx.account.application_scope)
    ):
        raise HTTPException(403, "委托范围不能超出本人范围")
    token, credential = issue_credential(
        db, ctx.account, "delegation", data.permissions, scope, data.minutes
    )
    audit(
        db,
        ctx,
        "delegation.create",
        credential_id=credential.id,
        permissions=data.permissions,
        application_ids=scope,
        expires_at=credential.expires_at.isoformat(),
    )
    return {
        "id": credential.id,
        "token": token,
        "expires_at": credential.expires_at,
        "permissions": credential.permissions,
        "application_ids": scope,
    }


@app.get("/api/delegations")
def delegations(db: DB, ctx: WEB):
    if ctx.account.role != "staff":
        raise HTTPException(403, "仅员工可管理委托")
    rows = db.scalars(
        select(Credential)
        .where(Credential.account_id == ctx.account.id, Credential.kind == "delegation")
        .order_by(Credential.expires_at.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": row.id,
            "permissions": row.permissions,
            "application_ids": row.application_scope,
            "expires_at": row.expires_at,
            "revoked": row.revoked,
            "expired": row.expires_at <= now(),
        }
        for row in rows
    ]


@app.delete("/api/delegations/{credential_id}", status_code=204)
def revoke(credential_id: UUID, db: DB, ctx: WEB):
    credential = db.scalar(
        select(Credential)
        .where(
            Credential.id == str(credential_id),
            Credential.account_id == ctx.account.id,
            Credential.kind == "delegation",
        )
        .with_for_update()
    )
    if not credential:
        raise HTTPException(404, "委托不存在")
    credential.revoked = True
    audit(db, ctx, "delegation.revoke", credential_id=credential.id)
