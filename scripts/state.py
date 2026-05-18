import json
import os
from datetime import datetime, timezone, timedelta

STATE_FILE = os.getenv("STATE_FILE", "/data/state.json")
KST = timezone(timedelta(hours=9))


def _today() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _load_all() -> dict:
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
        if data.get("date") != _today():
            return {}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all(data: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"date": _today(), **data}, f, ensure_ascii=False)


def load(team_code: str) -> dict:
    return _load_all().get(team_code, {})


def save(team_code: str, data: dict) -> None:
    all_data = _load_all()
    all_data[team_code] = data
    _save_all(all_data)
