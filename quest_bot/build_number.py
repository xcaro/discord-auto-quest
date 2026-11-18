"""Scrape the latest client_build_number from the Discord web app."""
import re
from typing import Optional

import requests

from .logger import Colors, log

_SCRAPE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def fetch_latest_build_number() -> Optional[int]:
    """Return the build number, or None if it could not be fetched."""
    try:
        headers = {"User-Agent": _SCRAPE_UA}
        r = requests.get("https://discord.com/app", headers=headers, timeout=15)
        if r.status_code != 200:
            log(f"Could not fetch the Discord page ({r.status_code})", "warn")
            return None

        scripts = re.findall(r"/assets/([a-f0-9]+)\.js", r.text)
        if not scripts:
            alt = re.findall(r'src="(/assets/[^"]+\.js)"', r.text)
            scripts = [s.split("/")[-1].replace(".js", "") for s in alt]
        if not scripts:
            log("No JS assets found", "warn")
            return None

        for asset_hash in scripts[-5:]:
            try:
                ar = requests.get(f"https://discord.com/assets/{asset_hash}.js",
                                  headers=headers, timeout=15)
                m = re.search(r'buildNumber["\s:]+["\s]*(\d{5,7})', ar.text)
                if m:
                    return int(m.group(1))
            except Exception:
                continue
        log("Build number not found in JS", "warn")
    except Exception as e:
        log(f"Error fetching build number: {e}", "warn")
    return None
