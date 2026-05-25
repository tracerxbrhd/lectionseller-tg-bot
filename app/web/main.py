from __future__ import annotations

import argparse
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from app.common.logging import configure_logging, get_logger
from app.config.app_info import APP_INFO


logger = get_logger(__name__)


def create_app() -> object:
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import PlainTextResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.trustedhost import TrustedHostMiddleware

    from app.config.settings import get_settings
    from app.web.admin.router import router as admin_router
    from app.web.miniapp import api_router as miniapp_api_router
    from app.web.miniapp import frontend_router as miniapp_frontend_router
    from app.web.routers.payments import router as payments_router

    settings = get_settings()
    app = FastAPI(title=APP_INFO.name, version=APP_INFO.version, debug=settings.app_debug)
    if settings.allowed_host_list:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
    app.mount(
        "/app/assets",
        StaticFiles(directory="frontend/miniapp/dist/assets", check_dir=False),
        name="miniapp-assets",
    )
    app.include_router(miniapp_frontend_router)
    app.include_router(miniapp_api_router)
    app.include_router(admin_router)
    app.include_router(payments_router)

    @app.middleware("http")
    async def admin_csrf_guard(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path.startswith("/admin") and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            source = request.headers.get("origin") or request.headers.get("referer")
            source_host = urlparse(source).hostname if source else None
            request_host = request.url.hostname
            allowed_hosts = {host.lower() for host in settings.allowed_host_list}
            if "*" not in allowed_hosts and (
                source_host is None
                or request_host is None
                or source_host.lower() not in allowed_hosts | {request_host.lower()}
            ):
                return PlainTextResponse("CSRF validation failed.", status_code=403)

        return await call_next(request)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.app_env}

    return app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lecture seller web application")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate that the web entrypoint can be imported and started.",
    )
    return parser


def main(app_factory: Callable[[], object] | None = None) -> None:
    configure_logging()
    args = build_parser().parse_args()

    if args.dry_run:
        logger.info("Web scaffold dry-run completed.")
        return

    factory = app_factory or create_app
    factory()
    logger.info("Web application factory completed. Run it with uvicorn in deployment.")


if __name__ == "__main__":
    main()
