from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Permission = Literal["applications.read", "applications.advance", "audit.read"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthInput(Input):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class DraftInput(Input):
    name: Text100
    contact_email: EmailStr = Field(max_length=254)
    statement: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)
    ]


class VersionInput(Input):
    expected_version: int = Field(ge=1)


class EditInput(DraftInput, VersionInput):
    pass


class AdvanceInput(VersionInput):
    reason: Reason


class DelegationInput(Input):
    permissions: list[Permission] = Field(min_length=1, max_length=3)
    application_ids: list[UUID] | None = Field(default=None, max_length=100)
    minutes: int = Field(default=15, ge=1, le=60)


class AccountOut(BaseModel):
    id: str
    email: str
    role: str
    permissions: list[str]


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: str
    delegated_by: str | None
    channel: str
    before: str | None
    after: str
    reason: str
    at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    applicant_id: str
    name: str
    contact_email: str
    statement: str
    status: Literal["draft", "submitted", "screening"]
    version: int
    created_at: datetime
    updated_at: datetime
    events: list[EventOut] = []


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    application_id: str | None
    actor_id: str
    delegated_by: str | None
    channel: str
    action: str
    data: dict
    result: str
    at: datetime


class ErrorOut(BaseModel):
    detail: str
    fields: list[str] = []
