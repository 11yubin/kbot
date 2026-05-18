import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send(text: str, chat_id: str) -> None:
    requests.post(
        f"{_BASE}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    ).raise_for_status()


def send_with_keyboard(chat_id: str, text: str, keyboard: list) -> None:
    """keyboard: list of rows, each row is list of {"text": ..., "callback_data": ...}"""
    requests.post(
        f"{_BASE}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": {"inline_keyboard": keyboard},
        },
        timeout=10,
    ).raise_for_status()


def answer_callback_query(callback_query_id: str, text: str = "") -> None:
    requests.post(
        f"{_BASE}/answerCallbackQuery",
        json={"callback_query_id": callback_query_id, "text": text},
        timeout=10,
    )


def get_updates(offset: int = 0) -> list:
    resp = requests.get(
        f"{_BASE}/getUpdates",
        params={"offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]},
        timeout=35,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])
