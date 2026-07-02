"""
Persistent state — remembers which disclosures we've already acted on.

A long-running daemon re-reads the same Quiver feed over and over, so without
this it would try to buy the same signal every cycle. We store a small set of
"signal keys" in a JSON file on disk.
"""
from __future__ import annotations

import json
import os
from threading import Lock

import config

_lock = Lock()


def _load() -> set[str]:
    if not os.path.exists(config.STATE_FILE):
        return set()
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f).get("acted", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save(keys: set[str]) -> None:
    tmp = config.STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"acted": sorted(keys)}, f, indent=2)
    os.replace(tmp, config.STATE_FILE)  # atomic write


def already_acted(key: str) -> bool:
    with _lock:
        return key in _load()


def mark_acted(key: str) -> None:
    with _lock:
        keys = _load()
        keys.add(key)
        _save(keys)
