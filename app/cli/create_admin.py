from __future__ import annotations

import argparse
import asyncio
import getpass

from app.common.logging import configure_logging
from app.common.security import hash_password
from app.db.repositories import AdminRepository
from app.db.session import async_session_factory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update a web admin account.")
    parser.add_argument("--username", required=True, help="Admin username.")
    parser.add_argument("--password", help="Admin password. If omitted, prompt securely.")
    parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create or update the account as inactive.",
    )
    return parser


async def create_admin(username: str, password: str, is_active: bool) -> None:
    async with async_session_factory() as session:
        repository = AdminRepository(session)
        await repository.upsert(
            username=username,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        await session.commit()


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()
    password = args.password or getpass.getpass("Admin password: ")
    asyncio.run(
        create_admin(
            username=args.username,
            password=password,
            is_active=not args.inactive,
        ),
    )
    print(f"Admin account '{args.username}' has been created or updated.")


if __name__ == "__main__":
    main()
