"""Complete PLAY_ON_DESKTOP / STREAM_ON_DESKTOP / PLAY_ACTIVITY quests."""
import random
from typing import Optional

import config
from .. import control
from ..api import DiscordAPI, get_retry_after, unauthorized_hint
from ..logger import Colors, log, log_progress
from ..quest_utils import (
    get_quest_name, get_seconds_done, get_seconds_needed, get_task_type,
)


def complete(api: DiscordAPI, quest: dict, stream_key: Optional[str] = None) -> bool:
    name = get_quest_name(quest)
    qid = quest["id"]
    task_type = get_task_type(quest)
    needed = get_seconds_needed(quest)
    done = get_seconds_done(quest)

    remaining = max(0, needed - done)
    log(f"🎮 {task_type}: {Colors.BOLD}{name}{Colors.RESET} "
        f"(~{remaining // 60:.0f} min remaining)", "info")

    key = stream_key or f"call:0:{random.randint(1000, 30000)}"
    log(f"[{name}] stream_key={key}, need {needed}s, done {done:.0f}s", "debug")
    errors = 0

    while done < needed:
        if control.stopped():
            return False
        try:
            r = api.post(f"/quests/{qid}/heartbeat", {"stream_key": key, "terminal": False})

            if r.status_code == 200:
                errors = 0
                body = r.json()
                progress = body.get("progress") or {}
                if task_type in progress:
                    done = progress[task_type].get("value", done)
                log_progress(qid, f"  [{name}] {done:.0f}/{needed}s")
                if body.get("completed_at") or done >= needed:
                    break
            elif r.status_code == 401:
                log(f"[{name}] {unauthorized_hint(api)}", "error")
                return False
            elif r.status_code == 429:
                wait = get_retry_after(r, 10) + 1
                log(f"  Rate limited – waiting {wait:.0f}s", "warn")
                control.sleep(wait)
                continue
            else:
                errors += 1
                log(f"  Heartbeat error ({r.status_code}): {r.text[:200]}", "warn")
        except Exception as e:
            errors += 1
            log(f"  Heartbeat error: {e}", "error")

        if errors >= config.MAX_CONSECUTIVE_ERRORS:
            log(f"Skipping \"{name}\" after {errors} consecutive errors", "error")
            return False

        control.sleep(config.HEARTBEAT_INTERVAL)

    try:
        api.post(f"/quests/{qid}/heartbeat", {"stream_key": key, "terminal": True})
    except Exception:
        pass
    log(f"✅ Completed: {Colors.BOLD}{name}{Colors.RESET}", "ok")
    return True
