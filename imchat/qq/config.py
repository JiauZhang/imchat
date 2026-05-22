from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GroupConfig:
    require_mention: bool = True
    ignore_other_mentions: bool = False
    tool_policy: Literal["full", "restricted", "none"] = "restricted"
    name: str = ""
    prompt: str = ""
    history_limit: int = 50


@dataclass
class QQConfig:
    app_id: str = ""
    client_secret: str = ""
    client_secret_file: str = ""

    name: str = ""
    enabled: bool = True
    system_prompt: str = ""

    dm_policy: Literal["open", "pairing", "allowlist"] = "open"
    allow_from: list[str] = field(default_factory=lambda: ["*"])

    group_policy: Literal["open", "allowlist", "disabled"] = "open"
    group_allow_from: list[str] = field(default_factory=list)
    groups: dict[str, GroupConfig] = field(default_factory=dict)

    image_server_base_url: str = ""
    markdown_support: bool = True

    url_direct_upload: bool = True
    streaming: bool = False

    deliver_debounce: dict[str, object] | None = None

    @classmethod
    def from_env(cls) -> QQConfig:
        import os

        config = cls()
        if os.environ.get("QQBOT_APP_ID"):
            config.app_id = os.environ["QQBOT_APP_ID"]
        if os.environ.get("QQBOT_CLIENT_SECRET"):
            config.client_secret = os.environ["QQBOT_CLIENT_SECRET"]
        if os.environ.get("QQBOT_IMAGE_SERVER_BASE_URL"):
            config.image_server_base_url = os.environ["QQBOT_IMAGE_SERVER_BASE_URL"]
        return config

    def resolve_client_secret(self) -> str:
        if self.client_secret:
            return self.client_secret
        if self.client_secret_file:
            import pathlib

            path = pathlib.Path(self.client_secret_file).expanduser()
            if path.exists():
                return path.read_text().strip()
        import os

        return os.environ.get("QQBOT_CLIENT_SECRET", "")