import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Account, Audit, Credential, now

PERMISSIONS = {"applications.read", "applications.advance", "audit.read"}
COOKIE = "recruitment_session"


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return salt + ":" + digest


def password_matches(password: str, stored: str) -> bool:
    salt, expected = stored.split(":")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)


def token_hash(token: str):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_credential(
    db: Session, account: Account, kind="session", permissions=None, scope=None, minutes=480
):
    token = secrets.token_urlsafe(32)
    credential = Credential(
        account_id=account.id,
        token_hash=token_hash(token),
        kind=kind,
        permissions=permissions or [],
        application_scope=scope,
        expires_at=now() + timedelta(minutes=minutes),
    )
    db.add(credential)
    db.flush()
    return token, credential


@dataclass
class Context:
    account: Account
    credential: Credential
    channel: str

    @property
    def actor_id(self):
        return f"ai:{self.credential.id}" if self.channel == "ai" else self.account.id

    @property
    def delegated_by(self):
        return self.account.id if self.channel == "ai" else None

    @property
    def permissions(self):
        current = set(self.account.permissions)
        return current & set(self.credential.permissions) if self.channel == "ai" else current

    def permits_object(self, application_id: str):
        scopes = [self.account.application_scope]
        if self.channel == "ai":
            scopes.append(self.credential.application_scope)
        return all(scope is None or application_id in scope for scope in scopes)

    def require(self, permission: str):
        if self.account.role != "staff" or permission not in self.permissions:
            raise HTTPException(403, "没有执行此操作的权限")


def authenticate(db: Session, request: Request, ai=False):
    if ai:
        auth = request.headers.get("authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
    else:
        token = request.cookies.get(COOKIE, "")
    credential = db.scalar(select(Credential).where(Credential.token_hash == token_hash(token)))
    expected_kind = "delegation" if ai else "session"
    if (
        not token
        or not credential
        or credential.kind != expected_kind
        or credential.revoked
        or credential.expires_at <= now()
    ):
        raise HTTPException(401, "登录或委托已失效，请重新认证")
    account = db.get(Account, credential.account_id)
    if not account or not account.active or (ai and account.role != "staff"):
        raise HTTPException(401, "身份不可用")
    return Context(account, credential, "ai" if ai else "web")


def audit(db, ctx, action, application_id=None, **data):
    db.add(
        Audit(
            actor_id=ctx.actor_id,
            delegated_by=ctx.delegated_by,
            channel=ctx.channel,
            action=action,
            application_id=application_id,
            data=data,
        )
    )
