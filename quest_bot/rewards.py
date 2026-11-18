"""Read and classify quest rewards."""
from typing import List

import config
from .quest_utils import _get

REWARD_LABELS = {
    config.REWARD_ORBS: "💎 Orbs",
    config.REWARD_DECORATION: "🖼️  Avatar Decoration",
    config.REWARD_CODE: "🎁 Out-of-game code",
}


def get_rewards(quest: dict) -> List[dict]:
    cfg = quest.get("config", {})
    rc = _get(cfg, "rewardsConfig", "rewards_config") or {}
    return rc.get("rewards") or []


def has_allowed_reward(quest: dict) -> bool:
    return any(r.get("type") in config.ALLOWED_REWARD_TYPES for r in get_rewards(quest))


def get_orb_quantity(quest: dict) -> int:
    total = 0
    for r in get_rewards(quest):
        if r.get("type") == config.REWARD_ORBS:
            total += _get(r, "orb_quantity", "orbQuantity") or 0
    return total


def describe_rewards(quest: dict) -> str:
    parts = []
    for r in get_rewards(quest):
        t = r.get("type")
        name = (r.get("messages") or {}).get("name", "?")
        parts.append(f"{REWARD_LABELS.get(t, f'type {t}')} {name}")
    return ", ".join(parts) or "?"
