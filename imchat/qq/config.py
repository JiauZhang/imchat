from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class QQConfig:
    app_id: str = ""
    client_secret: str = ""
    markdown_support: bool = True

    @classmethod
    def from_env(cls) -> QQConfig:
        return cls(
            app_id=os.environ.get("QQBOT_APP_ID", ""),
            client_secret=os.environ.get("QQBOT_CLIENT_SECRET", ""),
        )

    def resolve_client_secret(self) -> str:
        if self.client_secret:
            return self.client_secret
        return os.environ.get("QQBOT_CLIENT_SECRET", "")