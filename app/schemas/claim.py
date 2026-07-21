from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.claim import ClaimStatus


class ClaimCreate(BaseModel):
    title: str = Field(max_length=200)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title must not be empty")
        return value


class ClaimResponse(BaseModel):
    id: int
    user_id: int
    title: str
    amount: Decimal
    status: ClaimStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StatusUpdate(BaseModel):
    status: ClaimStatus
    model_config = ConfigDict(extra="forbid")

    @field_validator("status")
    @classmethod
    def completed_status_only(cls, value: ClaimStatus) -> ClaimStatus:
        if value not in {ClaimStatus.APPROVED, ClaimStatus.REJECTED}:
            raise ValueError("Status must be APPROVED or REJECTED")
        return value
