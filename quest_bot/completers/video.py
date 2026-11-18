"""Complete WATCH_VIDEO / WATCH_VIDEO_ON_MOBILE quests (safe to run multi-threaded)."""
import random
import time
from datetime import datetime

import config
from .. import control
from ..api import DiscordAPI, get_retry_after, unauthorized_hint
from ..logger import Colors, log, log_progress
from ..quest_utils import (
    get_enrolled_at, get_quest_name, get_seconds_done, get_seconds_needed,
)


def complete(api: DiscordAPI, quest: dict) -> bool:
    name = get_quest_name(quest)
    qid = quest["id"]
    needed = get_seconds_needed(quest)
    done = get_seconds_done(quest)

    enrolled_str = get_enrolled_at(quest)
    if enrolled_str:
        enrolled_ts = datetime.fromisoformat(enrolled_str.replace("Z", "+00:00")).timestamp()
    else:
        enrolled_ts = time.time()

    log(f"🎬 Video: {Colors.BOLD}{name}{Colors.RESET} ({done:.0f}/{needed}s)", "info")

    errors = 0
    while done < needed:
        if control.stopped():
            return False

        max_allowed = (time.time() - enrolled_ts) + config.VIDEO_MAX_FUTURE
        timestamp = done + config.VIDEO_SPEED

        if max_allowed - done >= config.VIDEO_SPEED:
            try:
                r = api.post(f"/quests/{qid}/video-progress", {
                    "timestamp": min(needed, timestamp + random.random())
                })
                if r.status_code == 200:
                    errors = 0
                    if r.json().get("completed_at"):
                        log(f"✅ Completed: {Colors.BOLD}{name}{Colors.RESET}", "ok")
                        return True
                    done = min(needed, timestamp)
                    log_progress(qid, f"  [{name}] {done:.0f}/{needed}s")
                elif r.status_code == 401:
                    log(f"[{name}] {unauthorized_hint(api)}", "error")
                    return False
                elif r.status_code == 429:
                    wait = get_retry_after(r) + 1
                    log(f"  [{name}] Rate limited – waiting {wait:.0f}s", "warn")
                    control.sleep(wait)
                    continue
                else:
                    errors += 1
                    log(f"  [{name}] Video progress error ({r.status_code}): {r.text[:200]}", "warn")
            except Exception as e:
                errors += 1
                log(f"  [{name}] Error: {e}", "error")

            if errors >= config.MAX_CONSECUTIVE_ERRORS:
                log(f"Skipping \"{name}\" after {errors} consecutive errors", "error")
                return False

        if timestamp >= needed:
            break
        control.sleep(config.VIDEO_INTERVAL)

    if control.stopped():
        return False
    try:
        api.post(f"/quests/{qid}/video-progress", {"timestamp": needed})
    except Exception:
        pass
    log(f"✅ Completed: {Colors.BOLD}{name}{Colors.RESET}", "ok")
    return True
