from __future__ import annotations

from html import escape
import mimetypes
from pathlib import Path
from typing import Literal, NoReturn

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ContentType, PaymentStatus
from app.common.logging import get_logger
from app.config.app_info import APP_INFO
from app.config.settings import Settings, get_settings
from app.db.models import User
from app.db.repositories import (
    AccessRepository,
    CatalogRepository,
    PaymentRepository,
    PurchaseRepository,
    SupportRepository,
)
from app.services.access import AccessService
from app.services.catalog import BlockDTO, CatalogService, LectureDTO, SectionDTO
from app.services.content import (
    ContentAccessError,
    ContentItemDTO,
    ContentLibraryService,
    PurchasedLectureDTO,
)
from app.services.payments import (
    CheckoutService,
    PaymentConfigurationError,
    PaymentConfirmationError,
    PaymentConfirmationResult,
    PaymentConfirmationService,
    PaymentProviderError,
    YooKassaPaymentService,
)
from app.services.purchases import PurchaseDTO, PurchaseError, PurchaseService
from app.services.support import SupportRequestDTO, SupportRequestError, SupportService
from app.web.dependencies import get_db_session
from app.web.miniapp.dependencies import (
    TELEGRAM_INIT_DATA_HEADER,
    require_miniapp_admin,
    require_miniapp_user,
)
from app.web.miniapp.schemas import (
    BlockResponse,
    CheckPaymentResponse,
    CreatePaymentResponse,
    CreatePurchaseRequest,
    LectureResponse,
    LectureContentResponse,
    MiniAppMetaResponse,
    MiniAppPlannedResponse,
    MiniAppUserResponse,
    ContentItemResponse,
    PurchasedLectureResponse,
    PurchaseResponse,
    SectionResponse,
    SupportReplyCreate,
    SupportRequestCreate,
    SupportRequestResponse,
)


logger = get_logger(__name__)
api_router = APIRouter(prefix="/miniapp/api", tags=["miniapp"])
frontend_router = APIRouter(tags=["miniapp"])
ContentDeliveryMethod = Literal["inline_text", "backend_file", "telegram_file_id", "unavailable"]
MINIAPP_DIST_DIR = Path("frontend/miniapp/dist")
MINIAPP_INDEX_PATH = MINIAPP_DIST_DIR / "index.html"


@frontend_router.get("/app", response_class=HTMLResponse, include_in_schema=False)
@frontend_router.get("/app/", response_class=HTMLResponse, include_in_schema=False)
@frontend_router.get("/app/{path:path}", response_class=HTMLResponse, include_in_schema=False)
async def miniapp_frontend(path: str = "") -> Response:
    if MINIAPP_INDEX_PATH.exists():
        return FileResponse(MINIAPP_INDEX_PATH, media_type="text/html")

    return HTMLResponse(
        content=(
            "<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>LectionSeller Mini App</title></head><body>"
            "<main style=\"font-family:system-ui,sans-serif;max-width:560px;margin:48px auto;"
            "padding:0 20px;line-height:1.5\">"
            "<h1>LectionSeller Mini App</h1>"
            "<p>Frontend build is not available. Rebuild the web Docker image.</p>"
            "</main></body></html>"
        ),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@api_router.get("/meta", response_model=MiniAppMetaResponse)
async def miniapp_meta() -> MiniAppMetaResponse:
    settings = get_settings()
    return MiniAppMetaResponse(
        app_name=APP_INFO.name,
        miniapp_url=settings.effective_miniapp_url,
        auth_header=TELEGRAM_INIT_DATA_HEADER,
        frontend_status="scaffolded",
        features=[
            "catalog",
            "purchases",
            "payments",
            "content",
            "support",
            "admin_support",
        ],
    )


@api_router.get(
    "/auth/me",
    response_model=MiniAppUserResponse,
)
async def miniapp_me(user: User = Depends(require_miniapp_user)) -> MiniAppUserResponse:
    return _user_response(user)


@api_router.get(
    "/catalog/sections",
    response_model=list[SectionResponse],
)
async def list_sections(
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SectionResponse]:
    sections = await _catalog_service(session).list_sections()
    return [_section_response(section) for section in sections]


@api_router.get(
    "/catalog/sections/{section_id}/blocks",
    response_model=list[BlockResponse],
)
async def list_section_blocks(
    section_id: int,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[BlockResponse]:
    section = await _catalog_service(session).get_section(section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section is not available.",
        )
    blocks = await _catalog_service(session).list_blocks(section_id)
    return [_block_response(block) for block in blocks]


@api_router.get(
    "/catalog/blocks/{block_id}/lectures",
    response_model=list[LectureResponse],
)
async def list_block_lectures(
    block_id: int,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[LectureResponse]:
    block = await _catalog_service(session).get_block(block_id)
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block is not available.",
        )
    lectures = await _catalog_service(session).list_lectures(block_id)
    return [_lecture_response(lecture) for lecture in lectures]


@api_router.post(
    "/purchases",
    response_model=CreatePaymentResponse,
)
async def create_purchase(
    request: CreatePurchaseRequest,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> CreatePaymentResponse:
    purchase_repository = PurchaseRepository(session)
    try:
        purchase = await _purchase_service(session, purchase_repository).create_pending_purchase(
            user_id=user.id,
            purchase_type=request.purchase_type,
            object_id=request.object_id,
        )
    except PurchaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This item is not available for purchase.",
        ) from exc

    payment_url: str | None = None
    payment_status: PaymentStatus | None = None
    payment_error = False
    message = (
        "YooKassa is not configured yet. The purchase request was created, "
        "but no payment link is available."
    )

    purchase_model = await purchase_repository.get(purchase.id)
    if settings.yookassa_enabled and purchase_model is not None:
        try:
            payment = await _checkout_service(settings, session).get_or_create_payment(
                purchase_model,
            )
        except PaymentConfigurationError:
            logger.exception("Mini App payment creation failed: YooKassa is misconfigured.")
            payment_error = True
            message = "Payment provider is misconfigured. Please contact support."
        except PaymentProviderError:
            logger.exception("Mini App payment creation failed for purchase %s.", purchase.id)
            payment_error = True
            message = "Payment provider is temporarily unavailable. Please try again later."
        else:
            payment_url = payment.confirmation_url
            payment_status = payment.status
            message = (
                "Payment link was created. Open YooKassa and then check the payment status."
                if payment_url
                else "Payment was created, but YooKassa did not return a confirmation URL."
            )

    return CreatePaymentResponse(
        purchase=_purchase_response(purchase),
        confirmation_url=payment_url,
        status=purchase.status,
        payment_status=payment_status,
        payment_error=payment_error,
        message=message,
    )


@api_router.post(
    "/payments/{purchase_id}/check",
    response_model=CheckPaymentResponse,
)
async def check_payment(
    purchase_id: int,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> CheckPaymentResponse:
    try:
        result = await _confirmation_service(settings, session).confirm_by_purchase_id(
            purchase_id=purchase_id,
            user_id=user.id,
            raw_context={"miniapp_manual_check": {"telegram_id": user.telegram_id}},
        )
    except PaymentConfigurationError as exc:
        logger.exception("Mini App payment check failed: YooKassa is misconfigured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is not configured.",
        ) from exc
    except PaymentProviderError as exc:
        logger.exception("Mini App payment check failed for purchase %s.", purchase_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is temporarily unavailable.",
        ) from exc
    except PaymentConfirmationError as exc:
        logger.exception("Mini App payment confirmation failed for purchase %s.", purchase_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not confirm this payment.",
        ) from exc

    return _check_payment_response(result)


@api_router.get(
    "/purchases/my",
    response_model=list[PurchasedLectureResponse],
)
async def list_my_purchases(
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[PurchasedLectureResponse]:
    lectures = await _content_service(session).list_purchased_lectures(user.id)
    return [_purchased_lecture_response(lecture) for lecture in lectures]


@api_router.get(
    "/content/lectures/{lecture_id}",
    response_model=LectureContentResponse,
)
async def list_lecture_content(
    lecture_id: int,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> LectureContentResponse:
    return await _lecture_content_response(
        user_id=user.id,
        lecture_id=lecture_id,
        session=session,
    )


@api_router.get(
    "/content/items/{content_item_id}/file",
    response_class=FileResponse,
)
async def get_content_file(
    content_item_id: int,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    try:
        item = await _content_service(session).get_content_item(
            user_id=user.id,
            content_item_id=content_item_id,
        )
    except ContentAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content item is not available.",
        ) from exc

    if item.type == ContentType.TEXT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Text content is available inline.",
        )
    if item.telegram_file_id and not item.file_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram file source is available only inside the bot.",
        )
    if not item.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content file is not configured.",
        )

    path = _resolve_local_content_path(item.file_path, settings.upload_dir)
    return FileResponse(
        path,
        media_type=_media_type(item.type, path),
        filename=path.name,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@api_router.post(
    "/support/requests",
    response_model=SupportRequestResponse,
    responses={status.HTTP_501_NOT_IMPLEMENTED: {"model": MiniAppPlannedResponse}},
)
async def create_support_request(
    request: SupportRequestCreate,
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> SupportRequestResponse:
    try:
        support_request = await _support_service(session).create_request(
            user_id=user.id,
            message=request.message,
        )
    except SupportRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support message must contain 5 to 4000 characters.",
        ) from exc

    await _notify_support_admins(settings, support_request, user)
    return _support_request_response(support_request)


@api_router.get(
    "/support/requests",
    response_model=list[SupportRequestResponse],
)
async def list_support_requests(
    user: User = Depends(require_miniapp_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[SupportRequestResponse]:
    requests = await _support_service(session).list_user_requests(user.id)
    return [_support_request_response(request) for request in requests]


@api_router.get(
    "/admin/support/requests",
    responses={status.HTTP_501_NOT_IMPLEMENTED: {"model": MiniAppPlannedResponse}},
)
async def admin_list_support_requests(user: User = Depends(require_miniapp_admin)) -> None:
    _planned("Admin support queue will be restricted to Telegram admins.", "stage-9-admin-support")


@api_router.post(
    "/admin/support/requests/{request_id}/reply",
    responses={status.HTTP_501_NOT_IMPLEMENTED: {"model": MiniAppPlannedResponse}},
)
async def admin_reply_to_support_request(
    request_id: int,
    request: SupportReplyCreate,
    user: User = Depends(require_miniapp_admin),
) -> None:
    _planned(
        f"Admin reply to support request {request_id} will notify the user in Telegram.",
        "stage-9-admin-support",
    )


def _user_response(user: User) -> MiniAppUserResponse:
    return MiniAppUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_admin=user.is_admin,
    )


def _catalog_service(session: AsyncSession) -> CatalogService:
    return CatalogService(CatalogRepository(session))


def _purchase_service(
    session: AsyncSession,
    purchase_repository: PurchaseRepository,
) -> PurchaseService:
    return PurchaseService(
        purchase_repository=purchase_repository,
        catalog_repository=CatalogRepository(session),
    )


def _checkout_service(settings: Settings, session: AsyncSession) -> CheckoutService:
    return CheckoutService(
        payment_repository=PaymentRepository(session),
        payment_service=YooKassaPaymentService(settings),
    )


def _confirmation_service(
    settings: Settings,
    session: AsyncSession,
) -> PaymentConfirmationService:
    purchase_repository = PurchaseRepository(session)
    catalog_repository = CatalogRepository(session)
    return PaymentConfirmationService(
        payment_repository=PaymentRepository(session),
        purchase_repository=purchase_repository,
        access_service=AccessService(
            access_repository=AccessRepository(session),
            purchase_repository=purchase_repository,
            catalog_repository=catalog_repository,
        ),
        payment_service=YooKassaPaymentService(settings),
    )


def _content_service(session: AsyncSession) -> ContentLibraryService:
    return ContentLibraryService(
        access_repository=AccessRepository(session),
        catalog_repository=CatalogRepository(session),
    )


def _support_service(session: AsyncSession) -> SupportService:
    return SupportService(SupportRepository(session))


def _purchase_response(purchase: PurchaseDTO) -> PurchaseResponse:
    return PurchaseResponse(
        id=purchase.id,
        purchase_type=purchase.purchase_type,
        object_id=purchase.object_id,
        price=purchase.price,
        status=purchase.status,
        created_at=purchase.created_at,
    )


def _check_payment_response(result: PaymentConfirmationResult) -> CheckPaymentResponse:
    return CheckPaymentResponse(
        provider_payment_id=result.provider_payment_id,
        payment_status=result.status,
        handled=result.handled,
        purchase_id=result.purchase_id,
        granted_count=result.granted_count,
        is_paid=result.status == PaymentStatus.SUCCEEDED,
        message=_payment_check_message(result.status),
    )


def _payment_check_message(payment_status: PaymentStatus) -> str:
    if payment_status == PaymentStatus.SUCCEEDED:
        return "Payment is confirmed. Access has been granted."
    if payment_status in {PaymentStatus.PENDING, PaymentStatus.WAITING_FOR_CAPTURE}:
        return "Payment is not confirmed yet. Please check again in a few seconds."
    if payment_status == PaymentStatus.CANCELED:
        return "Payment was canceled. You can create a new purchase."
    return "Payment failed. Please try again."


async def _lecture_content_response(
    *,
    user_id: int,
    lecture_id: int,
    session: AsyncSession,
) -> LectureContentResponse:
    service = _content_service(session)
    try:
        lecture = await service.get_purchased_lecture(
            user_id=user_id,
            lecture_id=lecture_id,
        )
        content_items = await service.list_lecture_content(
            user_id=user_id,
            lecture_id=lecture_id,
        )
    except ContentAccessError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lecture is not available.",
        ) from exc

    return LectureContentResponse(
        lecture=_purchased_lecture_response(lecture),
        content_items=[_content_item_response(item) for item in content_items],
    )


def _purchased_lecture_response(lecture: PurchasedLectureDTO) -> PurchasedLectureResponse:
    return PurchasedLectureResponse(
        id=lecture.id,
        title=lecture.title,
        short_description=lecture.short_description,
        purchased_at=lecture.purchased_at,
        source_purchase_id=lecture.source_purchase_id,
    )


def _content_item_response(item: ContentItemDTO) -> ContentItemResponse:
    delivery_method = _delivery_method(item)
    return ContentItemResponse(
        id=item.id,
        lecture_id=item.lecture_id,
        type=item.type,
        title=item.title,
        protected_content_enabled=item.protected_content_enabled,
        delivery_method=delivery_method,
        is_text_available_inline=item.type == ContentType.TEXT and bool(item.text_content),
        is_file_available=delivery_method == "backend_file",
        file_url=(
            f"/miniapp/api/content/items/{item.id}/file"
            if delivery_method == "backend_file"
            else None
        ),
        text_content=item.text_content if item.type == ContentType.TEXT else None,
    )


def _delivery_method(
    item: ContentItemDTO,
) -> ContentDeliveryMethod:
    if item.type == ContentType.TEXT and item.text_content:
        return "inline_text"
    if item.file_path:
        return "backend_file"
    if item.telegram_file_id:
        return "telegram_file_id"
    return "unavailable"


def _resolve_local_content_path(file_path: str, upload_dir: str) -> Path:
    base_dir = Path(upload_dir).resolve()
    candidate = Path(file_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()

    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content file is not available.",
        ) from exc

    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content file does not exist.",
        )
    return resolved


def _media_type(content_type: ContentType, path: Path) -> str:
    guessed_type = mimetypes.guess_type(path.name)[0]
    if guessed_type:
        return guessed_type
    return {
        ContentType.PDF: "application/pdf",
        ContentType.VIDEO: "video/mp4",
        ContentType.AUDIO: "audio/mpeg",
        ContentType.IMAGE: "image/jpeg",
    }.get(content_type, "application/octet-stream")


def _support_request_response(request: SupportRequestDTO) -> SupportRequestResponse:
    return SupportRequestResponse(
        id=request.id,
        message=request.message,
        status=request.status,
        created_at=request.created_at,
    )


async def _notify_support_admins(
    settings: Settings,
    support_request: SupportRequestDTO,
    user: User,
) -> None:
    admin_ids = settings.admin_telegram_id_list
    if not admin_ids:
        logger.warning(
            "Mini App support request %s created, but no admin IDs configured.",
            support_request.id,
        )
        return
    if settings.bot_token is None:
        logger.warning(
            "Mini App support request %s created, but bot token is not configured.",
            support_request.id,
        )
        return

    bot = Bot(
        settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        text = _render_support_admin_notification(support_request, user)
        for admin_id in admin_ids:
            try:
                await bot.send_message(admin_id, text)
            except TelegramAPIError:
                logger.exception(
                    "Could not notify admin %s about Mini App support request %s.",
                    admin_id,
                    support_request.id,
                )
    finally:
        await bot.session.close()


def _render_support_admin_notification(
    support_request: SupportRequestDTO,
    user: User,
) -> str:
    username = f"@{user.username}" if user.username else "без username"
    full_name = " ".join(
        part for part in [user.first_name, user.last_name] if part
    ) or "имя не указано"
    return (
        f"<b>Новое обращение #{support_request.id} из Mini App</b>\n\n"
        f"Пользователь: {escape(full_name)} ({escape(username)})\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n\n"
        f"{escape(support_request.message)}"
    )


def _section_response(section: SectionDTO) -> SectionResponse:
    return SectionResponse(
        id=section.id,
        title=section.title,
        description=section.description,
    )


def _block_response(block: BlockDTO) -> BlockResponse:
    return BlockResponse(
        id=block.id,
        section_id=block.section_id,
        title=block.title,
        description=block.description,
        price=block.price,
    )


def _lecture_response(lecture: LectureDTO) -> LectureResponse:
    return LectureResponse(
        id=lecture.id,
        block_id=lecture.block_id,
        title=lecture.title,
        short_description=lecture.short_description,
        full_description=lecture.full_description,
        price=lecture.price,
    )


def _planned(detail: str, next_stage: str) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=MiniAppPlannedResponse(detail=detail, next_stage=next_stage).model_dump(),
    )
