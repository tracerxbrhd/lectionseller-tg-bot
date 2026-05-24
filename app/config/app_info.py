from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AppInfo:
    name: str = "lectionseller-tg-bot"
    version: str = "0.1.0"


APP_INFO = AppInfo()

