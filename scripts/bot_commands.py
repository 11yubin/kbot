import logging
import time
import threading
import telegram
import user_prefs
from teams import TEAMS

log = logging.getLogger(__name__)

TEAM_KEYBOARD = [
    [
        {"text": f"{TEAMS['HT']['emoji']} KIA",  "callback_data": "team:HT"},
        {"text": f"{TEAMS['LG']['emoji']} LG",   "callback_data": "team:LG"},
        {"text": f"{TEAMS['OB']['emoji']} 두산", "callback_data": "team:OB"},
    ],
    [
        {"text": f"{TEAMS['SK']['emoji']} SSG",  "callback_data": "team:SK"},
        {"text": f"{TEAMS['SS']['emoji']} 삼성", "callback_data": "team:SS"},
        {"text": f"{TEAMS['NC']['emoji']} NC",   "callback_data": "team:NC"},
    ],
    [
        {"text": f"{TEAMS['KT']['emoji']} KT",   "callback_data": "team:KT"},
        {"text": f"{TEAMS['LT']['emoji']} 롯데", "callback_data": "team:LT"},
        {"text": f"{TEAMS['WO']['emoji']} 키움", "callback_data": "team:WO"},
    ],
    [
        {"text": f"{TEAMS['HH']['emoji']} 한화", "callback_data": "team:HH"},
    ],
]

_WELCOME = (
    "👋 KBO 알림봇입니다!\n\n"
    "/myteam 으로 응원 팀을 설정하면\n"
    "경기 당일 오전 10시에 일정을, 라인업이 나오면 바로 알려드릴게요 ⚾"
)


def _handle_update(update: dict) -> None:
    msg = update.get("message")
    cb = update.get("callback_query")

    if msg:
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")

        if text.startswith("/start"):
            current = user_prefs.get_team(chat_id)
            if current and current in TEAMS:
                team = TEAMS[current]
                telegram.send(
                    f"{_WELCOME}\n\n현재 설정된 팀: {team['emoji']} {team['name']}",
                    chat_id,
                )
            else:
                telegram.send(_WELCOME, chat_id)

        elif text.startswith("/myteam"):
            telegram.send_with_keyboard(chat_id, "응원하는 팀을 선택하세요 👇", TEAM_KEYBOARD)

    elif cb:
        chat_id = str(cb["from"]["id"])
        cb_id = cb["id"]
        data = cb.get("data", "")

        if data.startswith("team:"):
            team_code = data.split(":", 1)[1]
            if team_code in TEAMS:
                user_prefs.set_team(chat_id, team_code)
                team = TEAMS[team_code]
                telegram.answer_callback_query(cb_id, f"{team['name']} 설정 완료!")
                telegram.send(
                    f"✅ {team['emoji']} {team['name']}(으)로 설정됐어요!\n"
                    "경기 당일 오전 10시에 알림이 가요 ⚾",
                    chat_id,
                )
                log.info("팀 설정: chat_id=%s, team=%s", chat_id, team_code)


def _poll_loop() -> None:
    offset = 0
    log.info("Telegram 커맨드 폴링 시작")
    while True:
        try:
            updates = telegram.get_updates(offset)
            for update in updates:
                try:
                    _handle_update(update)
                except Exception as e:
                    log.error("업데이트 처리 오류: %s", e)
                offset = update["update_id"] + 1
        except Exception as e:
            log.error("폴링 오류: %s", e)
            time.sleep(5)


def start() -> None:
    t = threading.Thread(target=_poll_loop, daemon=True, name="bot-commands")
    t.start()
