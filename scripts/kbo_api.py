import requests
from datetime import datetime, timezone, timedelta
from teams import TEAMS

KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE = "https://api-gw.sports.naver.com"


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def get_today_team_game(team_code: str) -> dict | None:
    """오늘 특정 팀 경기 반환. 없으면 None."""
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
    team_info = next(
        (g for g in game_infos if g.get("homeTeamCode") == team_code or g.get("awayTeamCode") == team_code),
        None,
    )
    if not team_info:
        return None

    return {
        "team_game_id": team_info["gameId"],
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


def build_schedule_message(team_code: str, team_game: dict, all_games: list[dict]) -> str:
    team_info = TEAMS.get(team_code, {"name": team_code, "short": team_code, "emoji": "⚾"})
    is_home = team_game["homeTeamCode"] == team_code
    opponent = team_game["awayTeamName"] if is_home else team_game["homeTeamName"]
    stadium = team_game["stadium"]
    game_time = team_game["gameDateTime"][11:16]
    my_starter = (team_game["homeStarterName"] if is_home else team_game["awayStarterName"]) or "미정"
    opp_starter = (team_game["awayStarterName"] if is_home else team_game["homeStarterName"]) or "미정"

    now = datetime.now(KST)
    all_games_str = "\n".join(
        f"{g['awayTeamName']} {g.get('awayStarterName') or '미정'} vs "
        f"{g['homeTeamName']} {g.get('homeStarterName') or '미정'} / "
        f"{g['stadium']}, {g['gameDateTime'][11:16]}"
        for g in sorted(all_games, key=lambda g: g["gameDateTime"])
    )

    home_away = "🏠 홈경기" if is_home else "✈️ 원정경기"
    game_link = f"https://sports.naver.com/game/{team_game['gameId']}/record"
    short = team_info["short"]
    emoji = team_info["emoji"]

    return (
        f"⚾ 오늘 {short} 경기 있어요! 신한 SOL뱅크 경기예측 & 비더레전드 GOGO!\n\n"
        f"📅 {now.month}월 {now.day}일\n"
        f"⏰ {game_time}\n"
        f"🆚 {opponent}\n"
        f"🏟️ {stadium} ({home_away})\n"
        f"{emoji} {short} {my_starter} vs {opponent} {opp_starter}\n\n"
        f"📋 오늘 KBO 전체\n{all_games_str}\n\n"
        f"라인업 나오면 다시 알려드릴게요 👀\n"
        f"🔗 {game_link}"
    )
