"""HTTP client for the Discord API (thread-safe: one Session per thread)."""
import threading
import time
from typing import Optional

import requests

import config
from .agent import super_properties, user_agent
from .logger import Colors, log


def unauthorized_hint(api) -> str:
    return (f"401 Unauthorized (current agent profile: '{api.profile}'). "
            "If the token is correct, try setting \"profile\": \"desktop\" in agent.json "
            "(game-playing quests need the desktop client), or double-check the token.")


def get_retry_after(r: requests.Response, default: float = 5) -> float:
    try:
        return float(r.json().get("retry_after", default))
    except Exception:
        return default


class DiscordAPI:
    def __init__(self, token: str, agent: dict):
        self.token = token
        self._local = threading.local()
        self._lock = threading.Lock()
        self._version = 0
        self._headers: dict = {}
        self.profile = "?"
        self.set_agent(agent)

    def set_agent(self, agent: dict) -> None:
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": f"{config.LOCALE},en;q=0.9",
            "User-Agent": user_agent(agent),
            "X-Super-Properties": super_properties(agent),
            "X-Discord-Locale": config.LOCALE,
            "X-Discord-Timezone": config.TIMEZONE,
            "Origin": "https://discord.com",
            "Referer": "https://discord.com/channels/@me",
        }
        with self._lock:
            self.profile = agent.get("profile", "?")
            self._headers = headers
            self._version += 1

    def _session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None or self._local.version != self._version:
            with self._lock:
                headers, version = dict(self._headers), self._version
            s = requests.Session()
            s.headers.update(headers)
            self._local.session, self._local.version = s, version
        return s

    def _send(self, method: str, path: str, **kwargs) -> requests.Response:
        t0 = time.monotonic()
        try:
            r = getattr(self._session(), method)(f"{config.API_BASE}{path}", **kwargs)
        except Exception as e:
            log(f"{method.upper()} {path} -> ERROR {type(e).__name__}: {e}", "debug")
            raise
        ms = (time.monotonic() - t0) * 1000
        log(f"{method.upper()} {path} -> {r.status_code} ({len(r.content)}B, {ms:.0f}ms)", "debug")
        return r

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._send("get", path, **kwargs)

    def post(self, path: str, payload: Optional[dict] = None, **kwargs) -> requests.Response:
        return self._send("post", path, json=payload, **kwargs)

    def validate_token(self) -> bool:
        try:
            r = self.get("/users/@me")
            if r.status_code == 200:
                user = r.json()
                log(f"Logged in: {Colors.BOLD}{user.get('username', '?')}{Colors.RESET} "
                    f"(ID: {user['id']})", "ok")
                return True
            log(f"Invalid token (status {r.status_code})", "error")
            return False
        except Exception as e:
            log(f"Unable to connect to Discord: {e}", "error")
            return False
