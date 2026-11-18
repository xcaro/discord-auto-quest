"""Pick the right completer for the task type."""
from ..api import DiscordAPI
from ..logger import log
from ..quest_utils import get_quest_name, get_task_type
from . import heartbeat, video

VIDEO_TASKS = ("WATCH_VIDEO", "WATCH_VIDEO_ON_MOBILE")
HEARTBEAT_TASKS = ("PLAY_ON_DESKTOP", "STREAM_ON_DESKTOP")


def complete(api: DiscordAPI, quest: dict) -> bool:
    task = get_task_type(quest)
    if task in VIDEO_TASKS:
        return video.complete(api, quest)
    if task in HEARTBEAT_TASKS:
        return heartbeat.complete(api, quest)
    if task == "PLAY_ACTIVITY":
        return heartbeat.complete(api, quest, stream_key="call:0:1")
    log(f"\"{get_quest_name(quest)}\" – unsupported task, skipping", "warn")
    return False
