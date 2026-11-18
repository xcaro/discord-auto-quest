"""
Central configuration. Edit only this file; no need to touch the logic code.
"""

# ── Discord API ───────────────────────────────────────────────────────────────
API_BASE = "https://discord.com/api/v9"

# ── Token ─────────────────────────────────────────────────────────────────────
# Priority order: command-line argument > environment variable > file > manual input
TOKEN_ENV = "DISCORD_TOKEN"   # NAME of the environment variable holding the token (not the token itself!)
TOKEN_FILE = ".token"         # file containing the token, path relative to the directory the command is run from

# ── Quest running ─────────────────────────────────────────────────────────────
HEARTBEAT_INTERVAL = 20       # seconds between heartbeats (game/stream quests)
AUTO_ACCEPT = True            # automatically accept (enroll in) matching quests
ENROLL_DELAY = 3              # seconds to rest between enrolls
QUEST_COOLDOWN = (30, 90)     # (min, max) random seconds to rest between 2 quests; (0, 0) = disabled
MAX_CONSECUTIVE_ERRORS = 5    # max consecutive errors before skipping that quest

# ── Filter by reward ──────────────────────────────────────────────────────────
REWARD_ORBS = 4               # Orbs
REWARD_DECORATION = 3         # Avatar Decoration
REWARD_CODE = 1               # Redeemable out-of-game code (CoD, HSR...)

# Only do quests that have at least 1 reward of these types
ALLOWED_REWARD_TYPES = {REWARD_ORBS, REWARD_DECORATION}

MIN_ORBS = 0                  # skip Orbs quests with fewer orbs than this value (e.g. 700)

# ── Warnings / time checks ────────────────────────────────────────────────────
WARN_UNCLAIMED = True         # list quests that are done but whose reward is not yet claimed
SKIP_IF_CANNOT_FINISH = True  # skip quests that cannot be finished before they expire
EXPIRY_SAFETY_MARGIN = 60     # safety-margin seconds subtracted from the time left before expiry

# ── Quest list display ────────────────────────────────────────────────────────
SHOW_SKIP_REASON = True       # print the reason a quest is skipped (unsupported task, expired...)
SHOW_COMPLETED = False        # also show completed quests
SHOW_EXPIRED = False          # also show expired quests

# ── Filter by task type ───────────────────────────────────────────────────────
# Order in the list = priority order when a quest has several tasks (join_operator "or")
ENABLED_TASKS = [
    "WATCH_VIDEO",
    "WATCH_VIDEO_ON_MOBILE",
    "PLAY_ON_DESKTOP",
    "STREAM_ON_DESKTOP",
    "PLAY_ACTIVITY",
]

# ── Processing order ──────────────────────────────────────────────────────────
# "remaining_time": quest with the least time left to do first
# "orbs":           quest with the most orbs first
# "expiry":         quest expiring soonest first
SORT_BY = "expiry"

# ── Video (multi-threaded) ────────────────────────────────────────────────────
VIDEO_MAX_THREADS = 3         # max number of video quests running in parallel (1 = sequential)
VIDEO_START_JITTER = (1, 5)   # (min, max) random delay in seconds before each thread starts
VIDEO_SPEED = 7               # seconds of "watching" sent per request
VIDEO_MAX_FUTURE = 10         # how many seconds ahead of real time is allowed at most
VIDEO_INTERVAL = 1            # seconds to rest between video requests

# ── Log ───────────────────────────────────────────────────────────────────────
# LOG_LEVEL: lowest level that gets printed. Each level also includes the levels below it.
#
#   "DEBUG"    Diagnostics: every HTTP request (method, path, status, size, time,
#              thread name), hidden/excluded quests with reasons, number of excluded quests.
#   "PROGRESS" Progress of each quest (e.g. 84/900s), at most 1 line per PROGRESS_LOG_INTERVAL seconds.
#   "INFO"     Default. Banner, quest table + skip reasons, quest start/completion,
#              summary, agent updates.
#   "WARNING"  Warnings only: rate limit, unclaimed quests, single API call errors...
#   "ERROR"    Serious errors only: wrong token, quest dropped after consecutive errors, 401...
LOG_LEVEL = "INFO"
PROGRESS_LOG_INTERVAL = 10    # minimum seconds between 2 progress lines of the same quest

# ── Agent (client emulation) ──────────────────────────────────────────────────
# Client parameters (build number, version...) live in AGENT_FILE and are auto-updated.
AGENT_FILE = "agent.json"
AUTO_UPDATE_AGENT = True      # automatically fetch the latest version; to lock a field, add it to "pinned" in agent.json
AGENT_MAX_AGE_HOURS = 24      # how long before checking again
LOCALE = "en-US"
TIMEZONE = "Asia/Ho_Chi_Minh"
