"""Colored, leveled (LOG_LEVEL) logging that is thread-safe."""
import threading
import time
from datetime import datetime

import config


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


# LOG_LEVEL values from config.py
LEVELS = {"DEBUG": 10, "PROGRESS": 15, "INFO": 20, "WARNING": 30, "ERROR": 40}

# Message type -> level. "ok" (success) counts as INFO.
_MSG_LEVEL = {"debug": 10, "progress": 15, "info": 20, "ok": 20, "warn": 30, "error": 40}

_PREFIX = {
    "info": f"{Colors.CYAN}[INFO]{Colors.RESET}",
    "ok": f"{Colors.GREEN}[  OK]{Colors.RESET}",
    "warn": f"{Colors.YELLOW}[WARN]{Colors.RESET}",
    "error": f"{Colors.RED}[ ERR]{Colors.RESET}",
    "progress": f"{Colors.DIM}[PROG]{Colors.RESET}",
    "debug": f"{Colors.DIM}[DBG ]{Colors.RESET}",
}

_lock = threading.Lock()
_last_progress: dict = {}
_invalid_warned = False


def _threshold() -> int:
    global _invalid_warned
    name = str(getattr(config, "LOG_LEVEL", "INFO")).strip().upper()
    if name in LEVELS:
        return LEVELS[name]
    if not _invalid_warned:
        _invalid_warned = True
        print(f"{Colors.YELLOW}[WARN]{Colors.RESET} LOG_LEVEL '{config.LOG_LEVEL}' is invalid "
              f"(choose from: {', '.join(LEVELS)}), using INFO", flush=True)
    return LEVELS["INFO"]


def enabled(level_name: str) -> bool:
    """True if a message at level_name would be printed."""
    return LEVELS[level_name.upper()] >= _threshold()


def log(msg: str, level: str = "info") -> None:
    if _MSG_LEVEL.get(level, 20) < _threshold():
        return
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = _PREFIX.get(level, f"[{level.upper()}]")
    if level == "debug":
        t = threading.current_thread().name
        if t != "MainThread":
            msg = f"[{t}] {msg}"
    with _lock:
        print(f"{Colors.DIM}{ts}{Colors.RESET} {prefix} {msg}", flush=True)


def log_progress(key: str, msg: str, force: bool = False) -> None:
    """Progress line, limited to 1 line per PROGRESS_LOG_INTERVAL seconds per key."""
    if not enabled("PROGRESS"):
        return
    now = time.monotonic()
    with _lock:
        if not force and now - _last_progress.get(key, 0) < config.PROGRESS_LOG_INTERVAL:
            return
        _last_progress[key] = now
    log(msg, "progress")
