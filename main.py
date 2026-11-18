#!/usr/bin/env python3
"""Entry point. Run: python main.py [token]"""
import os
import sys

import config
from quest_bot import agent as agent_mod
from quest_bot import control
from quest_bot.api import DiscordAPI
from quest_bot.logger import Colors, log
from quest_bot.runner import QuestRunner

BANNER = f"""
{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════╗
║          Discord Quest Auto-Completer        ║
║   Auto scan · Auto accept · Auto complete    ║
╚══════════════════════════════════════════════╝{Colors.RESET}
"""


def load_token() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1].strip()
    env = os.environ.get(config.TOKEN_ENV, "").strip()
    if env:
        log(f"Read token from environment variable {config.TOKEN_ENV}", "info")
        return env
    if os.path.exists(config.TOKEN_FILE):
        with open(config.TOKEN_FILE, "r") as f:
            log(f"Read token from file {config.TOKEN_FILE}", "info")
            return f.read().strip()
    return input(f"{Colors.BOLD}Enter Discord Token: {Colors.RESET}").strip()


def main() -> None:
    print(BANNER)
    token = load_token()
    if not token:
        log("Token is empty – exiting.", "error")
        sys.exit(1)

    agent = agent_mod.ensure_agent()
    api = DiscordAPI(token, agent)
    if not api.validate_token():
        sys.exit(1)

    try:
        QuestRunner(api).run()
    except KeyboardInterrupt:
        control.stop_event.set()
        print()
        log("Stopped.", "info")


if __name__ == "__main__":
    main()
