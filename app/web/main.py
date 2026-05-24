from __future__ import annotations

import argparse
from collections.abc import Callable

from app.common.logging import configure_logging, get_logger
from app.config.app_info import APP_INFO


logger = get_logger(__name__)


def create_app() -> object:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from app.config.settings import get_settings
    from app.web.admin.router import router as admin_router
    from app.web.routers.payments import router as payments_router

    settings = get_settings()
    app = FastAPI(title=APP_INFO.name, version=APP_INFO.version, debug=settings.app_debug)
    app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
    app.include_router(admin_router)
    app.include_router(payments_router)

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
