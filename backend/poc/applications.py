from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .accounts import Context, audit
from .db import Application, Audit, StatusEvent, now


def view(db: Session, app: Application, detail=False):
    result = {
        key: getattr(app, key)
        for key in (
            "id",
            "applicant_id",
            "name",
            "contact_email",
            "statement",
            "status",
            "version",
            "created_at",
            "updated_at",
        )
    }
    result["events"] = (
        db.scalars(
            select(StatusEvent)
            .where(StatusEvent.application_id == app.id)
            .order_by(StatusEvent.at, StatusEvent.id)
        ).all()
        if detail
        else []
    )
    return result


def object_for(db: Session, ctx: Context, application_id: str, permission=None, lock=False):
    if permission:
        ctx.require(permission)
    statement = select(Application).where(Application.id == application_id)
    app = db.scalar(statement.with_for_update() if lock else statement)
    if not app:
        raise HTTPException(404, "申请不存在或不可访问")
    if ctx.account.role == "applicant":
        allowed = app.applicant_id == ctx.account.id
    else:
        allowed = ctx.permits_object(app.id) and app.status != "draft"
    if not allowed:
        raise HTTPException(404, "申请不存在或不可访问")
    return app


def event(db, ctx, app, before, reason):
    db.add(
        StatusEvent(
            application_id=app.id,
            actor_id=ctx.actor_id,
            delegated_by=ctx.delegated_by,
            channel=ctx.channel,
            before=before,
            after=app.status,
            reason=reason,
        )
    )
    audit(
        db,
        ctx,
        "application.status",
        app.id,
        before=before,
        after=app.status,
        reason=reason,
        version=app.version,
    )
    db.flush()


def applicant_only(ctx):
    if ctx.account.role != "applicant":
        raise HTTPException(403, "此操作仅限申请人")


def create(db, ctx, data):
    applicant_only(ctx)
    # Serialize the one-application POC boundary even across concurrent creation requests.
    from .db import Account

    db.scalar(select(Account).where(Account.id == ctx.account.id).with_for_update())
    if db.scalar(select(Application.id).where(Application.applicant_id == ctx.account.id)):
        raise HTTPException(409, "POC 仅支持一份申请，请继续编辑已有申请")
    app = Application(applicant_id=ctx.account.id, **data.model_dump())
    db.add(app)
    db.flush()
    event(db, ctx, app, None, "创建草稿")
    return view(db, app, True)


def list_own(db, ctx):
    applicant_only(ctx)
    apps = db.scalars(select(Application).where(Application.applicant_id == ctx.account.id)).all()
    audit(db, ctx, "applications.own_list", count=len(apps))
    return [view(db, app) for app in apps]


def own_detail(db, ctx, app_id):
    applicant_only(ctx)
    app = object_for(db, ctx, app_id)
    audit(db, ctx, "application.read", app.id)
    return view(db, app, True)


def edit(db, ctx, app_id, data):
    applicant_only(ctx)
    app = object_for(db, ctx, app_id, lock=True)
    check_version(app, data.expected_version)
    if app.status != "draft":
        raise HTTPException(409, "仅草稿可以编辑")
    for key, value in data.model_dump(exclude={"expected_version"}).items():
        setattr(app, key, value)
    app.version += 1
    app.updated_at = now()
    audit(
        db,
        ctx,
        "application.edit",
        app.id,
        fields=["name", "contact_email", "statement"],
        version=app.version,
    )
    db.flush()
    return view(db, app, True)


def check_version(app, version):
    if app.version != version:
        raise HTTPException(409, "申请已更新，请刷新后重试")


def transition(db, ctx, app_id, data, staff=False):
    if not staff:
        applicant_only(ctx)
    app = object_for(db, ctx, app_id, "applications.advance" if staff else None, lock=True)
    check_version(app, data.expected_version)
    before, after = ("submitted", "screening") if staff else ("draft", "submitted")
    if app.status != before:
        raise HTTPException(409, "当前状态不允许此操作")
    app.status = after
    app.version += 1
    app.updated_at = now()
    event(db, ctx, app, before, data.reason if staff else "申请人提交申请")
    return view(db, app, True)


def list_staff(db, ctx, status=None, offset=0, limit=50):
    ctx.require("applications.read")
    query = select(Application).where(Application.status != "draft")
    for scope in [ctx.account.application_scope] + (
        [ctx.credential.application_scope] if ctx.channel == "ai" else []
    ):
        if scope is not None:
            query = query.where(Application.id.in_(scope))
    if status:
        query = query.where(Application.status == status)
    apps = db.scalars(
        query.order_by(Application.created_at.desc(), Application.id).offset(offset).limit(limit)
    ).all()
    audit(db, ctx, "applications.list", status=status, offset=offset, limit=limit, count=len(apps))
    return [view(db, app) for app in apps]


def detail_staff(db, ctx, app_id):
    app = object_for(db, ctx, app_id, "applications.read")
    audit(db, ctx, "application.read", app.id)
    return view(db, app, True)


def read_audit(db, ctx, app_id):
    app = object_for(db, ctx, app_id, "audit.read")
    records = db.scalars(
        select(Audit)
        .where(Audit.application_id == app.id)
        .order_by(Audit.at.desc(), Audit.id)
        .limit(100)
    ).all()
    audit(db, ctx, "audit.read", app.id, limit=100)
    return records
