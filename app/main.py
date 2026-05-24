from __future__ import annotations

from app.common.logging import configure_logging, get_logger


logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Use 'python -m app.bot.main' or 'python -m app.web.main'.")


if __name__ == "__main__":
    main()

