"""Helpers for reading quest data (supports both camelCase and snake_case)."""
from datetime import datetime, timezone
from typing import Optional

import config


def _get(d: Optional[dict], *keys):
    if d is None:
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def get_task_config(quest: dict) -> Optional[dict]:
    cfg = quest.get("config", {})
    return _get(cfg, "taskConfig", "task_config", "taskConfigV2", "task_config_v2")


def get_quest_name(quest: dict) -> str:
    cfg = quest.get("config", {})
    msgs = cfg.get("messages", {})
    for keys in (("questName", "quest_name"), ("gameTitle", "game_title")):
        v = _get(msgs, *keys)
        if v:
            return v.strip()
    app_name = cfg.get("application", {}).get("name")
    return app_name or f"Quest#{quest.get('id', '?')}"


def get_expires_at(quest: dict) -> Optional[str]:
    return _get(quest.get("config", {}), "expiresAt", "expires_at")


def get_user_status(quest: dict) -> dict:
    us = _get(quest, "userStatus", "user_status")
    return us if isinstance(us, dict) else {}


def is_enrolled(quest: dict) -> bool:
    return bool(_get(get_user_status(quest), "enrolledAt", "enrolled_at"))


def is_completed(quest: dict) -> bool:
    return bool(_get(get_user_status(quest), "completedAt", "completed_at"))


def is_claimed(quest: dict) -> bool:
    return bool(_get(get_user_status(quest), "claimedAt", "claimed_at"))


def get_enrolled_at(quest: dict) -> Optional[str]:
    return _get(get_user_status(quest), "enrolledAt", "enrolled_at")


def get_task_type(quest: dict) -> Optional[str]:
    tc = get_task_config(quest)
    if not tc or "tasks" not in tc:
        return None
    for t in config.ENABLED_TASKS:
        if tc["tasks"].get(t) is not None:
            return t
    return None


def get_seconds_needed(quest: dict) -> int:
    tc = get_task_config(quest)
    t = get_task_type(quest)
    if not tc or not t:
        return 0
    return tc["tasks"][t].get("target", 0)


def get_seconds_done(quest: dict) -> float:
    t = get_task_type(quest)
    if not t:
        return 0
    progress = get_user_status(quest).get("progress") or {}
    return (progress.get(t) or {}).get("value", 0)


def get_remaining_seconds(quest: dict) -> float:
    return max(0, get_seconds_needed(quest) - get_seconds_done(quest))


def seconds_until_expiry(quest: dict) -> Optional[float]:
    exp = _parse_dt(get_expires_at(quest))
    if not exp:
        return None
    return (exp - datetime.now(timezone.utc)).total_seconds()


def get_starts_at(quest: dict) -> Optional[str]:
    return _get(quest.get("config", {}), "startsAt", "starts_at")


def seconds_until_start(quest: dict) -> Optional[float]:
    st = _parse_dt(get_starts_at(quest))
    if not st:
        return None
    return (st - datetime.now(timezone.utc)).total_seconds()


def is_expired(quest: dict) -> bool:
    left = seconds_until_expiry(quest)
    return left is not None and left <= 0


def get_task_names(quest: dict) -> list:
    """Names of all task types in the quest (including types the script does not support)."""
    tc = get_task_config(quest)
    if not tc or "tasks" not in tc:
        return []
    return list((tc["tasks"] or {}).keys())
