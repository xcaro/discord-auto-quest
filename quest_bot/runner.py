"""Main loop: scan → accept → complete (videos run in parallel)."""
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import config
from . import completers, control
from .api import DiscordAPI, get_retry_after
from .filters import is_actionable, is_completable, skip_reason, sort_quests
from .logger import Colors, enabled, log
from .quest_utils import (
    get_quest_name, get_remaining_seconds, get_task_names, get_task_type,
    is_claimed, is_completed, is_enrolled, is_expired,
)
from .rewards import describe_rewards, has_allowed_reward


class QuestRunner:
    def __init__(self, api: DiscordAPI):
        self.api = api
        self.done_ids: set = set()

    # ── Fetch ─────────────────────────────────────────────────────────────────
    def fetch_quests(self, _retries: int = 3) -> List[dict]:
        try:
            r = self.api.get("/quests/@me")
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict):
                    log(f"/quests/@me: {len(data.get('quests', []))} quests, "
                        f"{len(data.get('excluded_quests', []))} excluded", "debug")
                    blocked = data.get("quest_enrollment_blocked_until")
                    if blocked:
                        log(f"Enrollment blocked until: {blocked}", "warn")
                    return data.get("quests", [])
                return data if isinstance(data, list) else []
            if r.status_code == 429 and _retries > 0:
                wait = get_retry_after(r, 10)
                log(f"Rate limited – waiting {wait:.0f}s", "warn")
                control.sleep(wait)
                return self.fetch_quests(_retries - 1)
            log(f"Quest fetch error ({r.status_code}): {r.text[:200]}", "warn")
        except Exception as e:
            log(f"Error fetching quest list: {e}", "error")
        return []

    # ── Enroll ────────────────────────────────────────────────────────────────
    def enroll_quest(self, quest: dict) -> bool:
        name, qid = get_quest_name(quest), quest["id"]
        for attempt in range(1, 4):
            try:
                r = self.api.post(f"/quests/{qid}/enroll", {
                    "location": 11,
                    "is_targeted": False,
                    "metadata_raw": None,
                    "metadata_sealed": None,
                    "traffic_metadata_raw": quest.get("traffic_metadata_raw"),
                    "traffic_metadata_sealed": quest.get("traffic_metadata_sealed"),
                })
                if r.status_code == 429:
                    wait = get_retry_after(r) + 1
                    log(f"Rate limited enrolling \"{name}\" (attempt {attempt}/3) – waiting {wait:.0f}s", "warn")
                    control.sleep(wait)
                    continue
                if r.status_code in (200, 201, 204):
                    log(f"Enrolled: {Colors.BOLD}{name}{Colors.RESET}", "ok")
                    return True
                log(f"Enroll \"{name}\" failed ({r.status_code}): {r.text[:200]}", "warn")
                return False
            except Exception as e:
                log(f"Enroll error \"{name}\": {e}", "error")
                return False
        log(f"Skipping \"{name}\" after 3 rate-limited attempts", "warn")
        return False

    def auto_accept(self, quests: List[dict]) -> List[dict]:
        if not config.AUTO_ACCEPT:
            return quests
        todo = [q for q in sort_quests(quests)
                if not is_enrolled(q) and not is_completed(q) and is_completable(q)]
        if not todo:
            return quests

        log(f"Found {len(todo)} un-enrolled quests – auto-accepting...", "info")
        for q in todo:
            if control.stopped():
                break
            self.enroll_quest(q)
            control.sleep(config.ENROLL_DELAY)
        control.sleep(2)
        return self.fetch_quests()

    # ── Display ───────────────────────────────────────────────────────────────
    @staticmethod
    def print_overview(quests: List[dict]) -> None:
        relevant = [q for q in quests if has_allowed_reward(q)]
        done = [q for q in relevant if is_completed(q)]
        expired = [q for q in relevant if is_expired(q) and not is_completed(q)]

        shown = []
        for q in relevant:
            if is_completed(q) and not config.SHOW_COMPLETED:
                continue
            if is_expired(q) and not is_completed(q) and not config.SHOW_EXPIRED:
                continue
            shown.append(q)

        log(f"Total {len(quests)} quests | matching reward {len(relevant)} "
            f"({len(quests) - len(relevant)} excluded by reward) | "
            f"done {len(done)} | expired {len(expired)} | remaining {len(shown)}", "info")

        for q in sort_quests(shown):
            reason = skip_reason(q) if not is_completed(q) else None
            if is_completed(q):
                icon = f"{Colors.GREEN}✓{Colors.RESET}"
            elif is_enrolled(q):
                icon = f"{Colors.YELLOW}{'⚠' if reason else '▶'}{Colors.RESET}"
            elif reason:
                icon = f"{Colors.RED}✗{Colors.RESET}"
            else:
                icon = f"{Colors.DIM}○{Colors.RESET}"

            task = get_task_type(q) or "/".join(get_task_names(q)) or "?"
            mins = get_remaining_seconds(q) / 60
            line = f"  {icon} {get_quest_name(q)} [{task}, ~{mins:.0f}m] → {describe_rewards(q)}"
            if reason and config.SHOW_SKIP_REASON:
                line += f"  {Colors.DIM}← {reason}{Colors.RESET}"
            log(line, "info")

        if enabled("DEBUG"):
            for q in quests:
                if not has_allowed_reward(q):
                    log(f"  · excluded by reward: {get_quest_name(q)} → {describe_rewards(q)}", "debug")
            for q in relevant:
                if q not in shown:
                    why = "done" if is_completed(q) else "expired"
                    log(f"  · hidden from table ({why}): {get_quest_name(q)}", "debug")

        QuestRunner.print_unclaimed(quests)

    @staticmethod
    def print_unclaimed(quests: List[dict]) -> None:
        unclaimed = [q for q in quests
                     if has_allowed_reward(q) and is_completed(q) and not is_claimed(q)]
        if config.WARN_UNCLAIMED and unclaimed:
            log(f"{len(unclaimed)} quests completed but reward NOT yet claimed (open Discord to claim):", "warn")
            for q in unclaimed:
                log(f"    • {get_quest_name(q)} → {describe_rewards(q)}", "warn")

    # ── Execution ─────────────────────────────────────────────────────────────
    @staticmethod
    def cooldown() -> None:
        lo, hi = config.QUEST_COOLDOWN
        if hi <= 0:
            return
        wait = random.uniform(lo, hi)
        log(f"Resting {wait:.0f}s before the next quest...", "info")
        control.sleep(wait)

    def _start(self, quest: dict) -> bool:
        log(f"━━━ Starting: {Colors.BOLD}{get_quest_name(quest)}{Colors.RESET} "
            f"(task: {get_task_type(quest)}) ━━━", "info")
        return completers.complete(self.api, quest)

    def _video_job(self, quest: dict) -> bool:
        lo, hi = config.VIDEO_START_JITTER
        if hi > 0 and control.sleep(random.uniform(lo, hi)):
            return False
        return self._start(quest)

    def run_videos(self, videos: List[dict]) -> None:
        workers = max(1, min(config.VIDEO_MAX_THREADS, len(videos)))
        log(f"🎬 {len(videos)} video quests – running with {workers} threads", "info")
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="video") as ex:
            futures = {ex.submit(self._video_job, q): q for q in videos}
            try:
                for fut in as_completed(futures):
                    q = futures[fut]
                    try:
                        ok = fut.result()
                    except Exception as e:
                        log(f"Quest error \"{get_quest_name(q)}\": {e}", "error")
                        ok = False
                    if ok:
                        self.done_ids.add(q.get("id"))
            except KeyboardInterrupt:
                control.stop_event.set()
                raise

    def run_sequential(self, quests: List[dict]) -> None:
        for i, q in enumerate(quests):
            if control.stopped():
                return
            if i > 0:
                self.cooldown()
                if control.stopped():
                    return
            if self._start(q):
                self.done_ids.add(q.get("id"))

    # ── Run one pass then stop ────────────────────────────────────────────────
    def run(self) -> None:
        log("=" * 60, "info")
        log(f"{Colors.BOLD}Discord Quest Auto-Completer{Colors.RESET}", "info")
        rewards = ", ".join(str(t) for t in sorted(config.ALLOWED_REWARD_TYPES))
        log(f"Auto-accept: {'ON' if config.AUTO_ACCEPT else 'OFF'} | "
            f"Reward types: {rewards} | Sort: {config.SORT_BY} | "
            f"Min orbs: {config.MIN_ORBS} | Video threads: {config.VIDEO_MAX_THREADS}", "info")
        log("=" * 60, "info")

        quests = self.fetch_quests()
        if not quests:
            log("No quests found", "info")
            return

        self.print_overview(quests)
        quests = self.auto_accept(quests)

        actionable = sort_quests(q for q in quests if is_actionable(q, self.done_ids))
        if not actionable:
            log("No quests need to be completed. Finished.", "info")
            return

        log(f"\n{len(actionable)} quests to complete:", "info")
        videos = [q for q in actionable if get_task_type(q) in completers.VIDEO_TASKS]
        others = [q for q in actionable if get_task_type(q) not in completers.VIDEO_TASKS]
        if videos:
            self.run_videos(videos)
        self.run_sequential(others)

        if control.stopped():
            log("Stopped on request.", "warn")
            return

        total = len(actionable)
        ok = len(self.done_ids)
        log(f"Done: {ok}/{total} quests completed.", "ok" if ok == total else "warn")
        if ok:
            self.print_unclaimed(self.fetch_quests())
        log("Finished.", "info")
