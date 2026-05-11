import json
import os
from datetime import datetime, timezone, timedelta

STATE_FILE = os.getenv("STATE_FILE", "/data/state.json")
KST = timezone(timedelta(hours=9))


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def load() -> dict:
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        if data.get("date") != _today():
            return {}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"date": _today(), **data}, f, ensure_ascii=False)
