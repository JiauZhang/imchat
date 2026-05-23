from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import aiohttp

from .exceptions import AuthError

logger = logging.getLogger("imchat.qq.auth")

TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
API_BASE = "https://api.sgroup.qq.com"


@dataclass
class _TokenEntry:
    token: str
    expires_at: float


class AuthManager:

    def __init__(self) -> None:
        self._token_cache: dict[str, _TokenEntry] = {}
        self._fetch_locks: dict[str, asyncio.Lock] = {}
        self._bg_tasks: dict[str, asyncio.Task[None]] = {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def get_access_token(self, app_id: str, client_secret: str) -> str:
        app_id = app_id.strip()
        cached = self._token_cache.get(app_id)

        if cached:
            refresh_ahead = min(5 * 60, (cached.expires_at - time.time()) / 3)
            if time.time() < cached.expires_at - refresh_ahead:
                return cached.token

        lock = self._fetch_locks.setdefault(app_id, asyncio.Lock())
        async with lock:
            cached = self._token_cache.get(app_id)
            if cached:
                refresh_ahead = min(5 * 60, (cached.expires_at - time.time()) / 3)
                if time.time() < cached.expires_at - refresh_ahead:
                    return cached.token

            token = await self._fetch_token(app_id, client_secret)
            return token

    async def _fetch_token(self, app_id: str, client_secret: str) -> str:
        body = {"appId": app_id, "clientSecret": client_secret}
        headers = {"Content-Type": "application/json"}

        session = await self._get_session()
        try:
            async with session.post(TOKEN_URL, json=body, headers=headers) as resp:
                try:
                    data = await resp.json()
                except Exception as e:
                    raise AuthError(f"Failed to parse access_token response: {e}") from e

                if not data.get("access_token"):
                    raise AuthError(f"Failed to get access_token: {data}")

                expires_in = int(data.get("expires_in", 7200))
                expires_at = time.time() + expires_in
                token = data["access_token"]

                self._token_cache[app_id] = _TokenEntry(token=token, expires_at=expires_at)
                return token
        except aiohttp.ClientError as e:
            raise AuthError(f"Network error getting access_token: {e}") from e

    def clear_token_cache(self, app_id: str | None = None) -> None:
        if app_id:
            self._token_cache.pop(app_id, None)
        else:
            self._token_cache.clear()

    def get_token_status(self, app_id: str) -> dict[str, object]:
        cached = self._token_cache.get(app_id)
        if not cached:
            return {"status": "none", "expires_at": None}
        remaining = cached.expires_at - time.time()
        is_valid = remaining > min(5 * 60, remaining / 3)
        return {"status": "valid" if is_valid else "expired", "expires_at": cached.expires_at}

    def start_background_refresh(
        self,
        app_id: str,
        client_secret: str,
        refresh_ahead: float = 5 * 60,
        random_offset: float = 30,
        min_interval: float = 60,
        retry_delay: float = 5,
    ) -> None:
        if app_id in self._bg_tasks:
            return

        task = asyncio.create_task(
            self._refresh_loop(app_id, client_secret, refresh_ahead, random_offset, min_interval, retry_delay)
        )
        self._bg_tasks[app_id] = task

    def stop_background_refresh(self, app_id: str | None = None) -> None:
        if app_id:
            task = self._bg_tasks.pop(app_id, None)
            if task:
                task.cancel()
        else:
            for task in self._bg_tasks.values():
                task.cancel()
            self._bg_tasks.clear()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _refresh_loop(
        self,
        app_id: str,
        client_secret: str,
        refresh_ahead: float,
        random_offset: float,
        min_interval: float,
        retry_delay: float,
    ) -> None:
        import random

        while True:
            try:
                await self.get_access_token(app_id, client_secret)
                cached = self._token_cache.get(app_id)
                if cached:
                    expires_in = cached.expires_at - time.time()
                    refresh_in = max(expires_in - refresh_ahead - random.random() * random_offset, min_interval)
                    await asyncio.sleep(refresh_in)
                else:
                    await asyncio.sleep(min_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(retry_delay)