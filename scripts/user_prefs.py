import json
import os
import threading

PREFS_FILE = os.getenv("PREFS_FILE", "/data/user_prefs.json")
_lock = threading.Lock()


def _load_raw() -> dict:
    try:
        with open(PREFS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_raw(prefs: dict) -> None:
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)


def get_team(chat_id: str) -> str | None:
    return _load_raw().get(str(chat_id))


def set_team(chat_id: str, team_code: str) -> None:
    with _lock:
        prefs = _load_raw()
        prefs[str(chat_id)] = team_code
        _save_raw(prefs)


def get_users_for_team(team_code: str) -> list[str]:
    return [cid for cid, tc in _load_raw().items() if tc == team_code]


def get_all_active_teams() -> set[str]:
    return set(_load_raw().values())
