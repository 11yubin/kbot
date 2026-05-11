import requests
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE = "https://api-gw.sports.naver.com"
HH = "HH"


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def get_today_hanhwa_game() -> dict | None:
    """오늘 한화(HH) 경기 반환. 없으면 None."""
    today = _today_kst()
    resp = requests.get(
        f"{BASE}/schedule/calendar",
        params={
            "upperCategoryId": "kbaseball",
            "categoryIds": ",kbo,kbs,kbaseballetc,premier12,apbc",
            "date": today,
        },
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()

    dates = resp.json().get("result", {}).get("dates", [])
    today_data = next((d for d in dates if d["ymd"] == today), None)
    if not today_data:
        return None

    game_infos = [
        g for g in today_data.get("gameInfos", [])
        if g.get("homeTeamCode") and g.get("awayTeamCode")
    ]
    hh_info = next(
        (g for g in game_infos if g.get("homeTeamCode") == HH or g.get("awayTeamCode") == HH),
        None,
    )
    if not hh_info:
        return None

    return {
        "hh_game_id": hh_info["gameId"],
        "all_game_ids": [g["gameId"] for g in game_infos],
    }


def get_game_detail(game_id: str) -> dict:
    resp = requests.get(
        f"{BASE}/schedule/games/{game_id}",
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["result"]["game"]


def build_schedule_message(hh_game: dict, all_games: list[dict]) -> str:
    is_home = hh_game["homeTeamCode"] == HH
    opponent = hh_game["awayTeamName"] if is_home else hh_game["homeTeamName"]
    stadium = hh_game["stadium"]
    game_time = hh_game["gameDateTime"][11:16]
    hw_starter = (hh_game["homeStarterName"] if is_home else hh_game["awayStarterName"]) or "미정"
    opp_starter = (hh_game["awayStarterName"] if is_home else hh_game["homeStarterName"]) or "미정"

    now = datetime.now(KST)
    all_games_str = "\n".join(
        f"{g['awayTeamName']} {g.get('awayStarterName') or '미정'} vs "
        f"{g['homeTeamName']} {g.get('homeStarterName') or '미정'} / "
        f"{g['stadium']}, {g['gameDateTime'][11:16]}"
        for g in sorted(all_games, key=lambda g: g["gameDateTime"])
    )

    home_away = "🏠 홈경기" if is_home else "✈️ 원정경기"
    game_link = f"https://sports.naver.com/game/{hh_game['gameId']}/record"

    return (
        f"⚾ 오늘 한화 경기 있어요! 신한 SOL뱅크 경기예측 & 비더레전드 GOGO!\n\n"
        f"📅 {now.month}월 {now.day}일\n"
        f"⏰ {game_time}\n"
        f"🆚 {opponent}\n"
        f"🏟️ {stadium} ({home_away})\n"
        f"⚾ 한화 {hw_starter} vs {opponent} {opp_starter}\n\n"
        f"📋 오늘 KBO 전체\n{all_games_str}\n\n"
        f"라인업 나오면 다시 알려드릴게요 👀\n"
        f"🔗 {game_link}"
    )
