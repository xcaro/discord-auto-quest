"""Decide which quests to do and in what order."""
from typing import Iterable, List, Optional

import config
from .quest_utils import (
    get_remaining_seconds, get_task_names, get_task_type, is_completed,
    is_enrolled, seconds_until_expiry, seconds_until_start,
)
from .rewards import get_orb_quantity, get_rewards, has_allowed_reward


def skip_reason(quest: dict) -> Optional[str]:
    """Reason a quest can NOT be done. None means it can be done."""
    left = seconds_until_expiry(quest)
    if left is not None and left <= 0:
        return "already expired"

    until = seconds_until_start(quest)
    if until is not None and until > 0:
        return f"not started yet ({until / 3600:.1f}h left)"

    if not get_task_type(quest):
        names = ", ".join(get_task_names(quest)) or "?"
        return f"unsupported task: {names}"

    if not has_allowed_reward(quest):
        return "reward not in ALLOWED_REWARD_TYPES"

    types = {r.get("type") for r in get_rewards(quest)}
    if types == {config.REWARD_ORBS} and get_orb_quantity(quest) < config.MIN_ORBS:
        return f"only {get_orb_quantity(quest)} orbs (< MIN_ORBS {config.MIN_ORBS})"

    if (config.SKIP_IF_CANNOT_FINISH and left is not None
            and get_remaining_seconds(quest) > left - config.EXPIRY_SAFETY_MARGIN):
        return "cannot finish before it expires"
    return None


def is_completable(quest: dict) -> bool:
    return skip_reason(quest) is None


def is_actionable(quest: dict, done_ids: set) -> bool:
    return (
        is_enrolled(quest)
        and not is_completed(quest)
        and is_completable(quest)
        and quest.get("id") not in done_ids
    )


def sort_quests(quests: Iterable[dict]) -> List[dict]:
    keys = {
        "remaining_time": lambda q: get_remaining_seconds(q),
        "orbs": lambda q: -get_orb_quantity(q),
        "expiry": lambda q: seconds_until_expiry(q) or float("inf"),
    }
    return sorted(quests, key=keys.get(config.SORT_BY, keys["expiry"]))
