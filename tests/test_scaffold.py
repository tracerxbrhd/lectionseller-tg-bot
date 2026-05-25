from app.bot.main import build_parser as build_bot_parser
from app.config.app_info import APP_INFO
from app.web.main import build_parser as build_web_parser
from app.web.miniapp import api_router as miniapp_api_router


def test_project_metadata_exists() -> None:
    assert APP_INFO.name == "lectionseller-tg-bot"
    assert APP_INFO.version


def test_entrypoint_parsers_accept_dry_run() -> None:
    assert build_bot_parser().parse_args(["--dry-run"]).dry_run is True
    assert build_web_parser().parse_args(["--dry-run"]).dry_run is True


def test_miniapp_api_router_is_registered() -> None:
    assert miniapp_api_router.prefix == "/miniapp/api"
