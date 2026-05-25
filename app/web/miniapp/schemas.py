from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import (
    ContentType,
    PaymentStatus,
    PurchaseStatus,
    PurchaseType,
    SupportRequestStatus,
)


class MiniAppMetaResponse(BaseModel):
    app_name: str
    api_version: str = "v1"
    miniapp_url: str
    auth_header: str
    frontend_status: Literal["planned", "scaffolded", "available"] = "planned"
    features: list[str]


class MiniAppPlannedResponse(BaseModel):
    status: Literal["planned"] = "planned"
    detail: str
    next_stage: str


class MiniAppUserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    is_admin: bool


class SectionResponse(BaseModel):
    id: int
    title: str
    description: str | None


class BlockResponse(BaseModel):
    id: int
    section_id: int
    title: str
    description: str | None
    price: Decimal
    has_access: bool = False


class LectureResponse(BaseModel):
    id: int
    block_id: int
    title: str
    short_description: str | None
    full_description: str | None
    price: Decimal
    has_access: bool = False


class ContentItemResponse(BaseModel):
    id: int
    lecture_id: int
    type: ContentType
    title: str
    protected_content_enabled: bool
    delivery_method: Literal["inline_text", "backend_file", "telegram_file_id", "unavailable"]
    is_text_available_inline: bool
    is_file_available: bool
    file_url: str | None = None
    text_content: str | None = None


class PurchasedLectureResponse(BaseModel):
    id: int
    title: str
    short_description: str | None
    purchased_at: datetime
    source_purchase_id: int | None


class LectureContentResponse(BaseModel):
    lecture: PurchasedLectureResponse
    content_items: list[ContentItemResponse]


class PurchaseResponse(BaseModel):
    id: int
    purchase_type: PurchaseType
    object_id: int
    price: Decimal
    status: PurchaseStatus
    created_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CreatePurchaseRequest(BaseModel):
    purchase_type: PurchaseType = Field(examples=[PurchaseType.LECTURE])
    object_id: int = Field(gt=0)


class CreatePaymentResponse(BaseModel):
    purchase: PurchaseResponse
    confirmation_url: str | None
    status: PurchaseStatus
    payment_status: PaymentStatus | None = None
    payment_error: bool = False
    message: str


class CheckPaymentResponse(BaseModel):
    provider_payment_id: str
    payment_status: PaymentStatus
    handled: bool
    purchase_id: int | None = None
    granted_count: int = 0
    is_paid: bool = False
    message: str


class SupportRequestCreate(BaseModel):
    message: str = Field(min_length=5, max_length=4000)


class SupportRequestResponse(BaseModel):
    id: int
    message: str
    status: SupportRequestStatus
    created_at: datetime


class SupportReplyCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
