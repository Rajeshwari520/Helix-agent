"""Request / response models (pydantic).

Categories come from the active domain (data/kgit/domain.json), so they are
checked with a validator instead of a fixed list.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app import config

Channel = Literal["email", "web_form", "chat"]
Priority = Literal["Low", "Medium", "High", "Critical"]
Status = Literal["New", "Triaged", "Assigned", "In Progress", "Waiting on Customer",
                 "Escalated", "Resolved", "Closed"]


def _check_category(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in config.domain().categories:
        raise ValueError(f"category must be one of {config.domain().categories}")
    return value


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=5000)
    channel: Channel = "web_form"
    customer_ref: str = Field(default="CUST-ANON", max_length=50)


class TicketUpdate(BaseModel):
    status: Optional[Status] = None
    category: Optional[str] = None
    priority: Optional[Priority] = None
    team: Optional[str] = None
    assignee_id: Optional[int] = None

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return _check_category(value)


class Ticket(BaseModel):
    id: str
    customer_ref: str
    channel: str
    subject: str
    body: str
    status: str
    category: Optional[str] = None
    priority: Optional[str] = None
    team: Optional[str] = None
    assignee_id: Optional[int] = None
    needs_escalation: bool
    escalation_reasons: list[str]
    sla_first_response_due: Optional[str] = None
    sla_resolution_due: Optional[str] = None
    created_at: str
    updated_at: str


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)


class FAQCreate(BaseModel):
    category: str
    question: str = Field(min_length=5)
    answer: str = Field(min_length=5)

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        return _check_category(value)


class FAQApprove(BaseModel):
    version: int
    approved_by: str = Field(min_length=2)
