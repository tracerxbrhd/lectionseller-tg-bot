from __future__ import annotations

import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import ContentType, PurchaseStatus, SupportRequestStatus
from app.common.security import (
    create_signed_admin_session,
    verify_password,
    verify_signed_admin_session,
)
from app.config.settings import Settings, get_settings
from app.db.models import (
    AccessGrant,
    AdminAccount,
    Block,
    ContentItem,
    Lecture,
    Payment,
    Purchase,
    Section,
    SupportRequest,
    User,
)
from app.db.repositories import AccessRepository, AdminRepository
from app.web.dependencies import get_db_session


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/web/templates")

ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7


async def _require_admin(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AdminAccount:
    settings = get_settings()
    token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if not token:
        raise _login_redirect()

    admin_id = verify_signed_admin_session(
        token,
        secret=settings.app_secret_key.get_secret_value(),
    )
    if admin_id is None:
        raise _login_redirect()

    admin = await AdminRepository(session).get(admin_id)
    if admin is None or not admin.is_active:
        raise _login_redirect()
    return admin


def _login_redirect() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Location": "/admin/login"},
    )


@router.get("", include_in_schema=False)
async def admin_root() -> RedirectResponse:
    return _redirect("/admin/dashboard")


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request) -> HTMLResponse:
    return _template(request, "admin/login.html", {"error": None})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings = get_settings()
    repository = AdminRepository(session)
    admin = await repository.get_by_username(username.strip())
    if admin is None or not admin.is_active or not verify_password(password, admin.password_hash):
        return _template(
            request,
            "admin/login.html",
            {"error": "Неверный логин или пароль."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    await repository.mark_login(admin)
    response = _redirect("/admin/dashboard")
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        create_signed_admin_session(
            admin_id=admin.id,
            secret=settings.app_secret_key.get_secret_value(),
            ttl_seconds=ADMIN_SESSION_TTL_SECONDS,
        ),
        max_age=ADMIN_SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.app_env != "local",
        samesite="lax",
    )
    return response


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = _redirect("/admin/login")
    response.delete_cookie(ADMIN_SESSION_COOKIE)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    paid_revenue = await _scalar(
        session,
        select(func.coalesce(func.sum(Purchase.price), 0)).where(
            Purchase.status == PurchaseStatus.PAID,
        ),
    )
    stats = {
        "users": await _count(session, User),
        "sections": await _count(session, Section),
        "blocks": await _count(session, Block),
        "lectures": await _count(session, Lecture),
        "purchases": await _count(session, Purchase),
        "paid_purchases": await _scalar(
            session,
            select(func.count(Purchase.id)).where(Purchase.status == PurchaseStatus.PAID),
        ),
        "revenue": paid_revenue,
        "support_open": await _scalar(
            session,
            select(func.count(SupportRequest.id)).where(
                SupportRequest.status == SupportRequestStatus.OPEN,
            ),
        ),
    }
    latest_support = await session.execute(
        select(SupportRequest, User)
        .select_from(SupportRequest)
        .join(User, SupportRequest.user_id == User.id)
        .order_by(SupportRequest.created_at.desc())
        .limit(5),
    )
    latest_purchases = await session.execute(
        select(Purchase, User)
        .select_from(Purchase)
        .join(User, Purchase.user_id == User.id)
        .order_by(Purchase.created_at.desc())
        .limit(5),
    )
    return _admin_template(
        request,
        "admin/dashboard.html",
        admin,
        {
            "stats": stats,
            "latest_support": list(latest_support.all()),
            "latest_purchases": list(latest_purchases.all()),
        },
    )


@router.get("/sections", response_class=HTMLResponse)
async def sections_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    sections = await session.scalars(select(Section).order_by(Section.sort_order, Section.id))
    return _admin_template(request, "admin/sections.html", admin, {"sections": list(sections)})


@router.get("/sections/new", response_class=HTMLResponse)
async def section_new_form(
    request: Request,
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(request, "admin/section_form.html", admin, {"section": None})


@router.post("/sections")
async def section_create(
    title: str = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    session.add(
        Section(
            title=title.strip(),
            description=_optional_text(description),
            sort_order=sort_order,
            is_active=is_active,
        ),
    )
    return _redirect("/admin/sections")


@router.get("/sections/{section_id}/edit", response_class=HTMLResponse)
async def section_edit_form(
    request: Request,
    section_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    section = await _get_or_404(session, Section, section_id)
    return _admin_template(request, "admin/section_form.html", admin, {"section": section})


@router.post("/sections/{section_id}")
async def section_update(
    section_id: int,
    title: str = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    section = await _get_or_404(session, Section, section_id)
    section.title = title.strip()
    section.description = _optional_text(description)
    section.sort_order = sort_order
    section.is_active = is_active
    return _redirect("/admin/sections")


@router.post("/sections/{section_id}/delete")
async def section_delete(
    section_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    await session.delete(await _get_or_404(session, Section, section_id))
    return _redirect("/admin/sections")


@router.get("/blocks", response_class=HTMLResponse)
async def blocks_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(Block, Section)
        .select_from(Block)
        .join(Section, Block.section_id == Section.id)
        .order_by(Section.sort_order, Block.sort_order, Block.id),
    )
    return _admin_template(request, "admin/blocks.html", admin, {"rows": list(rows.all())})


@router.get("/blocks/new", response_class=HTMLResponse)
async def block_new_form(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/block_form.html",
        admin,
        {"block": None, "sections": await _list_sections(session)},
    )


@router.post("/blocks")
async def block_create(
    section_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    session.add(
        Block(
            section_id=section_id,
            title=title.strip(),
            description=_optional_text(description),
            price=_decimal(price),
            sort_order=sort_order,
            is_active=is_active,
        ),
    )
    return _redirect("/admin/blocks")


@router.get("/blocks/{block_id}/edit", response_class=HTMLResponse)
async def block_edit_form(
    request: Request,
    block_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/block_form.html",
        admin,
        {
            "block": await _get_or_404(session, Block, block_id),
            "sections": await _list_sections(session),
        },
    )


@router.post("/blocks/{block_id}")
async def block_update(
    block_id: int,
    section_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form("0"),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    block = await _get_or_404(session, Block, block_id)
    block.section_id = section_id
    block.title = title.strip()
    block.description = _optional_text(description)
    block.price = _decimal(price)
    block.sort_order = sort_order
    block.is_active = is_active
    return _redirect("/admin/blocks")


@router.post("/blocks/{block_id}/delete")
async def block_delete(
    block_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    await session.delete(await _get_or_404(session, Block, block_id))
    return _redirect("/admin/blocks")


@router.get("/lectures", response_class=HTMLResponse)
async def lectures_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(Lecture, Block, Section)
        .select_from(Lecture)
        .join(Block, Lecture.block_id == Block.id)
        .join(Section, Block.section_id == Section.id)
        .order_by(Section.sort_order, Block.sort_order, Lecture.sort_order, Lecture.id),
    )
    return _admin_template(request, "admin/lectures.html", admin, {"rows": list(rows.all())})


@router.get("/lectures/new", response_class=HTMLResponse)
async def lecture_new_form(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/lecture_form.html",
        admin,
        {"lecture": None, "blocks": await _list_blocks(session)},
    )


@router.post("/lectures")
async def lecture_create(
    block_id: int = Form(...),
    title: str = Form(...),
    short_description: str = Form(""),
    full_description: str = Form(""),
    price: str = Form("0"),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    session.add(
        Lecture(
            block_id=block_id,
            title=title.strip(),
            short_description=_optional_text(short_description),
            full_description=_optional_text(full_description),
            price=_decimal(price),
            sort_order=sort_order,
            is_active=is_active,
        ),
    )
    return _redirect("/admin/lectures")


@router.get("/lectures/{lecture_id}/edit", response_class=HTMLResponse)
async def lecture_edit_form(
    request: Request,
    lecture_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/lecture_form.html",
        admin,
        {
            "lecture": await _get_or_404(session, Lecture, lecture_id),
            "blocks": await _list_blocks(session),
        },
    )


@router.post("/lectures/{lecture_id}")
async def lecture_update(
    lecture_id: int,
    block_id: int = Form(...),
    title: str = Form(...),
    short_description: str = Form(""),
    full_description: str = Form(""),
    price: str = Form("0"),
    sort_order: int = Form(0),
    is_active: bool = Form(False),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    lecture = await _get_or_404(session, Lecture, lecture_id)
    lecture.block_id = block_id
    lecture.title = title.strip()
    lecture.short_description = _optional_text(short_description)
    lecture.full_description = _optional_text(full_description)
    lecture.price = _decimal(price)
    lecture.sort_order = sort_order
    lecture.is_active = is_active
    return _redirect("/admin/lectures")


@router.post("/lectures/{lecture_id}/delete")
async def lecture_delete(
    lecture_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    await session.delete(await _get_or_404(session, Lecture, lecture_id))
    return _redirect("/admin/lectures")


@router.get("/content", response_class=HTMLResponse)
async def content_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(ContentItem, Lecture, Block, Section)
        .select_from(ContentItem)
        .join(Lecture, ContentItem.lecture_id == Lecture.id)
        .join(Block, Lecture.block_id == Block.id)
        .join(Section, Block.section_id == Section.id)
        .order_by(Section.sort_order, Block.sort_order, Lecture.sort_order, ContentItem.sort_order),
    )
    return _admin_template(request, "admin/content.html", admin, {"rows": list(rows.all())})


@router.get("/content/new", response_class=HTMLResponse)
async def content_new_form(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/content_form.html",
        admin,
        {
            "item": None,
            "lectures": await _list_lectures(session),
            "content_types": list(ContentType),
            "error": None,
        },
    )


@router.post("/content")
async def content_create(
    request: Request,
    lecture_id: int = Form(...),
    type: ContentType = Form(...),
    title: str = Form(...),
    file_path: str = Form(""),
    telegram_file_id: str = Form(""),
    text_content: str = Form(""),
    protected_content_enabled: bool = Form(False),
    sort_order: int = Form(0),
    upload: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> Response:
    source_path = await _save_upload(upload, lecture_id)
    values = {
        "id": None,
        "lecture_id": lecture_id,
        "type": type,
        "title": title.strip(),
        "file_path": source_path or _optional_text(file_path),
        "telegram_file_id": _optional_text(telegram_file_id),
        "text_content": _optional_text(text_content),
        "protected_content_enabled": protected_content_enabled,
        "sort_order": sort_order,
    }
    error = _content_validation_error(
        type=values["type"],
        file_path=values["file_path"],
        telegram_file_id=values["telegram_file_id"],
        text_content=values["text_content"],
    )
    if error:
        return await _content_form_error(request, session, admin, SimpleNamespace(**values), error)
    session.add(
        ContentItem(
            lecture_id=values["lecture_id"],
            type=values["type"],
            title=values["title"],
            file_path=values["file_path"],
            telegram_file_id=values["telegram_file_id"],
            text_content=values["text_content"],
            protected_content_enabled=values["protected_content_enabled"],
            sort_order=values["sort_order"],
        ),
    )
    return _redirect("/admin/content")


@router.get("/content/{item_id}/edit", response_class=HTMLResponse)
async def content_edit_form(
    request: Request,
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/content_form.html",
        admin,
        {
            "item": await _get_or_404(session, ContentItem, item_id),
            "lectures": await _list_lectures(session),
            "content_types": list(ContentType),
            "error": None,
        },
    )


@router.post("/content/{item_id}")
async def content_update(
    request: Request,
    item_id: int,
    lecture_id: int = Form(...),
    type: ContentType = Form(...),
    title: str = Form(...),
    file_path: str = Form(""),
    telegram_file_id: str = Form(""),
    text_content: str = Form(""),
    protected_content_enabled: bool = Form(False),
    sort_order: int = Form(0),
    upload: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> Response:
    item = await _get_or_404(session, ContentItem, item_id)
    uploaded_path = await _save_upload(upload, lecture_id)
    values = {
        "id": item.id,
        "lecture_id": lecture_id,
        "type": type,
        "title": title.strip(),
        "file_path": uploaded_path or _optional_text(file_path),
        "telegram_file_id": _optional_text(telegram_file_id),
        "text_content": _optional_text(text_content),
        "protected_content_enabled": protected_content_enabled,
        "sort_order": sort_order,
    }
    error = _content_validation_error(
        type=values["type"],
        file_path=values["file_path"],
        telegram_file_id=values["telegram_file_id"],
        text_content=values["text_content"],
    )
    if error:
        return await _content_form_error(request, session, admin, SimpleNamespace(**values), error)

    item.lecture_id = values["lecture_id"]
    item.type = values["type"]
    item.title = values["title"]
    item.file_path = values["file_path"]
    item.telegram_file_id = values["telegram_file_id"]
    item.text_content = values["text_content"]
    item.protected_content_enabled = values["protected_content_enabled"]
    item.sort_order = values["sort_order"]
    return _redirect("/admin/content")


@router.post("/content/{item_id}/delete")
async def content_delete(
    item_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    await session.delete(await _get_or_404(session, ContentItem, item_id))
    return _redirect("/admin/content")


@router.get("/users", response_class=HTMLResponse)
async def users_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    users = await session.scalars(select(User).order_by(User.created_at.desc()).limit(200))
    return _admin_template(request, "admin/users.html", admin, {"users": list(users)})


@router.post("/users/{user_id}/toggle-block")
async def user_toggle_block(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    user = await _get_or_404(session, User, user_id)
    user.is_blocked = not user.is_blocked
    return _redirect("/admin/users")


@router.post("/users/{user_id}/toggle-admin")
async def user_toggle_admin_flag(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    user = await _get_or_404(session, User, user_id)
    user.is_admin = not user.is_admin
    return _redirect("/admin/users")


@router.get("/purchases", response_class=HTMLResponse)
async def purchases_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(Purchase, User)
        .select_from(Purchase)
        .join(User, Purchase.user_id == User.id)
        .order_by(Purchase.created_at.desc())
        .limit(300),
    )
    return _admin_template(request, "admin/purchases.html", admin, {"rows": list(rows.all())})


@router.get("/payments", response_class=HTMLResponse)
async def payments_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(Payment, User, Purchase)
        .select_from(Payment)
        .join(User, Payment.user_id == User.id)
        .join(Purchase, Payment.purchase_id == Purchase.id)
        .order_by(Payment.created_at.desc())
        .limit(300),
    )
    return _admin_template(request, "admin/payments.html", admin, {"rows": list(rows.all())})


@router.get("/support", response_class=HTMLResponse)
async def support_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(SupportRequest, User)
        .select_from(SupportRequest)
        .join(User, SupportRequest.user_id == User.id)
        .order_by(SupportRequest.created_at.desc())
        .limit(300),
    )
    return _admin_template(
        request,
        "admin/support.html",
        admin,
        {"rows": list(rows.all()), "statuses": list(SupportRequestStatus)},
    )


@router.post("/support/{request_id}/status")
async def support_update_status(
    request_id: int,
    status_value: SupportRequestStatus = Form(..., alias="status"),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    support_request = await _get_or_404(session, SupportRequest, request_id)
    support_request.status = status_value
    return _redirect("/admin/support")


@router.get("/access", response_class=HTMLResponse)
async def access_list(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> HTMLResponse:
    rows = await session.execute(
        select(AccessGrant, User, Lecture)
        .select_from(AccessGrant)
        .join(User, AccessGrant.user_id == User.id)
        .join(Lecture, AccessGrant.lecture_id == Lecture.id)
        .order_by(AccessGrant.granted_at.desc())
        .limit(300),
    )
    return _admin_template(
        request,
        "admin/access.html",
        admin,
        {
            "rows": list(rows.all()),
            "users": await _list_users(session),
            "lectures": await _list_lectures(session),
        },
    )


@router.post("/access")
async def access_create(
    user_id: int = Form(...),
    lecture_id: int = Form(...),
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    await _get_or_404(session, User, user_id)
    await _get_or_404(session, Lecture, lecture_id)
    repository = AccessRepository(session)
    if not await repository.has_active_access(user_id=user_id, lecture_id=lecture_id):
        await repository.create_grant(
            user_id=user_id,
            lecture_id=lecture_id,
            granted_by_admin_id=admin.id,
        )
    return _redirect("/admin/access")


@router.post("/access/{grant_id}/revoke")
async def access_revoke(
    grant_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: AdminAccount = Depends(_require_admin),
) -> RedirectResponse:
    _ = admin
    grant = await _get_or_404(session, AccessGrant, grant_id)
    grant.is_active = False
    grant.revoked_at = datetime.now(UTC)
    return _redirect("/admin/access")


def _template(
    request: Request,
    template_name: str,
    context: dict[str, Any],
    *,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        context,
        status_code=status_code,
    )


def _admin_template(
    request: Request,
    template_name: str,
    admin: AdminAccount,
    context: dict[str, Any] | None = None,
) -> HTMLResponse:
    actual_context = dict(context or {})
    actual_context["admin"] = admin
    return _template(request, template_name, actual_context)


def _redirect(location: str) -> RedirectResponse:
    return RedirectResponse(location, status_code=status.HTTP_303_SEE_OTHER)


async def _get_or_404(session: AsyncSession, model: type[Any], object_id: int) -> Any:
    instance = await session.get(model, object_id)
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return instance


async def _count(session: AsyncSession, model: type[Any]) -> int:
    return int(await _scalar(session, select(func.count()).select_from(model)))


async def _scalar(session: AsyncSession, statement: Select[tuple[Any]]) -> Any:
    result = await session.execute(statement)
    return result.scalar_one()


async def _list_sections(session: AsyncSession) -> list[Section]:
    result = await session.scalars(select(Section).order_by(Section.sort_order, Section.id))
    return list(result.all())


async def _list_blocks(session: AsyncSession) -> Sequence[tuple[Block, Section]]:
    result = await session.execute(
        select(Block, Section)
        .select_from(Block)
        .join(Section, Block.section_id == Section.id)
        .order_by(Section.sort_order, Block.sort_order, Block.id),
    )
    return list(result.all())


async def _list_lectures(session: AsyncSession) -> Sequence[tuple[Lecture, Block, Section]]:
    result = await session.execute(
        select(Lecture, Block, Section)
        .select_from(Lecture)
        .join(Block, Lecture.block_id == Block.id)
        .join(Section, Block.section_id == Section.id)
        .order_by(Section.sort_order, Block.sort_order, Lecture.sort_order, Lecture.id),
    )
    return list(result.all())


async def _list_users(session: AsyncSession) -> list[User]:
    result = await session.scalars(select(User).order_by(User.created_at.desc()).limit(500))
    return list(result.all())


def _optional_text(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def _decimal(value: str) -> Decimal:
    normalized = value.replace(",", ".").strip()
    try:
        amount = Decimal(normalized).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid price.",
        ) from exc
    if amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price cannot be negative.",
        )
    return amount


async def _save_upload(upload: UploadFile | None, lecture_id: int) -> str | None:
    if upload is None or not upload.filename:
        return None

    settings = get_settings()
    file_name = _safe_file_name(upload.filename)
    relative_path = Path("content") / str(lecture_id) / f"{int(time.time())}_{file_name}"
    full_path = Path(settings.upload_dir) / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(await upload.read())
    return relative_path.as_posix()


def _safe_file_name(file_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file_name).name)
    return cleaned or "upload.bin"


def _content_validation_error(
    *,
    type: ContentType,
    file_path: str | None,
    telegram_file_id: str | None,
    text_content: str | None,
) -> str | None:
    if type == ContentType.TEXT and not text_content:
        return "Для текстового материала нужно заполнить текст."
    if type != ContentType.TEXT and not file_path and not telegram_file_id:
        return "Для файлового материала нужен upload, file_path или telegram_file_id."
    return None


async def _content_form_error(
    request: Request,
    session: AsyncSession,
    admin: AdminAccount,
    item: ContentItem | SimpleNamespace,
    error: str,
) -> HTMLResponse:
    return _admin_template(
        request,
        "admin/content_form.html",
        admin,
        {
            "item": item,
            "lectures": await _list_lectures(session),
            "content_types": list(ContentType),
            "error": error,
        },
    )
