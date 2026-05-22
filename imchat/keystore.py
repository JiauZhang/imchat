import os
import stat
from pathlib import Path
from typing import Dict, Any
from conippets import json


IMCHAT_HOME_ENV = "IMCHAT_HOME"
DEFAULT_IMCHAT_HOME = "~/.imchat"


def get_imchat_home() -> Path:
    env_value = os.environ.get(IMCHAT_HOME_ENV)
    if env_value:
        return Path(env_value).expanduser().resolve()
    return Path(DEFAULT_IMCHAT_HOME).expanduser().resolve()


def load_keys(platform: str) -> Dict[str, Any]:
    path = get_imchat_home() / f"{platform}.json"
    if not path.exists():
        return {}
    try:
        return json.read(str(path))
    except Exception:
        return {}


def save_keys(platform: str, data: Dict[str, Any]) -> None:
    path = get_imchat_home() / f"{platform}.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    json.write(str(path), data)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def delete_keys(platform: str) -> None:
    path = get_imchat_home() / f"{platform}.json"
    if path.exists():
        path.unlink()