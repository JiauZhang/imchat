from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QQConfig:
    app_id: str = ""
    client_secret: str = ""
    markdown_support: bool = True

    @classmethod
    def from_env(cls) -> QQConfig:
        import os

        config = cls()
        if os.environ.get("QQBOT_APP_ID"):
            config.app_id = os.environ["QQBOT_APP_ID"]
        if os.environ.get("QQBOT_CLIENT_SECRET"):
            config.client_secret = os.environ["QQBOT_CLIENT_SECRET"]
        return config

    def resolve_client_secret(self) -> str:
        if self.client_secret:
            return self.client_secret
        import os
        return os.environ.get("QQBOT_CLIENT_SECRET", "")