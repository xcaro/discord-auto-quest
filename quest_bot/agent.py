"""Agent = emulated client info, stored in agent.json and auto-updated.

Two profiles:
  - "desktop": Discord Electron. Game/stream quests (PLAY_*, STREAM_*) should use
               this profile. The constants client_version / electron /
               native_build_number have NO public source to fetch from and must be
               edited by hand; only build_number is auto-updated.
  - "browser": Chrome on the web. Every field (build number, Chrome version)
               can be fetched automatically and they always stay consistent.
"""
import base64
import copy
import json
import os
from datetime import datetime, timezone
from typing import Optional

import requests

import config
from .build_number import fetch_latest_build_number
from .logger import Colors, log

CHROME_VERSIONS_URL = (
    "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
)

DEFAULT_AGENT = {
    "profile": "desktop",          # "desktop" (recommended, same as the old version) | "browser"
    "pinned": [],                  # fields that are not auto-updated: "build_number", "chrome_version"
    "last_check": None,
    "updated_at": None,
    "build_number": 504649,
    "browser": {"chrome_version": "131.0.6778.85"},
    "desktop": {
        "client_version": "1.0.9175",
        "electron_version": "32.2.7",
        "chromium_version": "128.0.6613.186",
        "native_build_number": 59498,
        "os_version": "10.0.26100",
    },
}


# ── Save / load ───────────────────────────────────────────────────────────────
def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_agent() -> dict:
    if os.path.exists(config.AGENT_FILE):
        try:
            with open(config.AGENT_FILE, "r", encoding="utf-8") as f:
                return _merge(DEFAULT_AGENT, json.load(f))
        except Exception as e:
            log(f"Could not read {config.AGENT_FILE} ({e}), using defaults", "warn")
    return copy.deepcopy(DEFAULT_AGENT)


def save_agent(agent: dict) -> None:
    tmp = config.AGENT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(agent, f, indent=2, ensure_ascii=False)
    os.replace(tmp, config.AGENT_FILE)


# ── Update ────────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ver_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def is_stale(agent: dict) -> bool:
    last = agent.get("last_check")
    if not last:
        return True
    try:
        dt = datetime.fromisoformat(last)
        return (datetime.now(timezone.utc) - dt).total_seconds() > config.AGENT_MAX_AGE_HOURS * 3600
    except Exception:
        return True


def fetch_chrome_version() -> Optional[str]:
    try:
        r = requests.get(CHROME_VERSIONS_URL, timeout=15)
        if r.status_code == 200:
            return r.json()["channels"]["Stable"]["version"]
        log(f"Could not fetch Chrome version ({r.status_code})", "warn")
    except Exception as e:
        log(f"Error fetching Chrome version: {e}", "warn")
    return None


def refresh(agent: dict, force: bool = False) -> bool:
    """Update the agent if it is stale. Returns True if any value changed."""
    if not config.AUTO_UPDATE_AGENT:
        return False
    if not force and not is_stale(agent):
        return False

    log("Updating agent...", "info")
    pinned = set(agent.get("pinned") or [])
    changed = fetched_any = False

    if "build_number" not in pinned:
        bn = fetch_latest_build_number()
        if bn is not None:
            fetched_any = True
            old = agent["build_number"]
            if bn > old:
                log(f"build_number: {old} → {Colors.BOLD}{bn}{Colors.RESET}", "ok")
                agent["build_number"] = bn
                changed = True
            elif bn < old:
                log(f"Scraped build_number ({bn}) is lower than current ({old}), ignoring", "warn")

    if agent["profile"] == "browser" and "chrome_version" not in pinned:
        cv = fetch_chrome_version()
        if cv:
            fetched_any = True
            old = agent["browser"]["chrome_version"]
            if _ver_tuple(cv) > _ver_tuple(old):
                log(f"chrome_version: {old} → {Colors.BOLD}{cv}{Colors.RESET}", "ok")
                agent["browser"]["chrome_version"] = cv
                changed = True

    if fetched_any:                      # if every fetch failed, retry sooner next time
        agent["last_check"] = _now()
    if changed:
        agent["updated_at"] = _now()
    if fetched_any or changed:
        save_agent(agent)
    return changed


def ensure_agent() -> dict:
    """Load agent.json (create it if missing) and update it if needed."""
    existed = os.path.exists(config.AGENT_FILE)
    agent = load_agent()
    if not existed:
        save_agent(agent)
        log(f"Created {config.AGENT_FILE}", "info")
    refresh(agent)
    _log_summary(agent)
    return agent


def _log_summary(agent: dict) -> None:
    if agent["profile"] == "browser":
        detail = f"Chrome {agent['browser']['chrome_version']}"
    else:
        d = agent["desktop"]
        detail = f"Discord {d['client_version']} / Electron {d['electron_version']}"
    log(f"Agent: {agent['profile']} | {detail} | build {agent['build_number']}", "info")


# ── Build headers ─────────────────────────────────────────────────────────────
def _chrome_major(agent: dict) -> str:
    return agent["browser"]["chrome_version"].split(".")[0]


def user_agent(agent: dict) -> str:
    if agent["profile"] == "desktop":
        d = agent["desktop"]
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"discord/{d['client_version']} Chrome/{d['chromium_version']} "
            f"Electron/{d['electron_version']} Safari/537.36"
        )
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{_chrome_major(agent)}.0.0.0 Safari/537.36"
    )


def super_properties(agent: dict) -> str:
    if agent["profile"] == "desktop":
        d = agent["desktop"]
        obj = {
            "os": "Windows",
            "browser": "Discord Client",
            "release_channel": "stable",
            "client_version": d["client_version"],
            "os_version": d["os_version"],
            "os_arch": "x64",
            "app_arch": "x64",
            "system_locale": config.LOCALE,
            "browser_user_agent": user_agent(agent),
            "browser_version": d["electron_version"],
            "client_build_number": agent["build_number"],
            "native_build_number": d["native_build_number"],
            "client_event_source": None,
        }
    else:
        obj = {
            "os": "Windows",
            "browser": "Chrome",
            "device": "",
            "system_locale": config.LOCALE,
            "has_client_mods": False,
            "browser_user_agent": user_agent(agent),
            "browser_version": f"{_chrome_major(agent)}.0.0.0",
            "os_version": "10",
            "referrer": "",
            "referring_domain": "",
            "referrer_current": "",
            "referring_domain_current": "",
            "release_channel": "stable",
            "client_build_number": agent["build_number"],
            "client_event_source": None,
        }
    return base64.b64encode(json.dumps(obj).encode()).decode()
