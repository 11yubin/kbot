import logging
from datetime import datetime, timezone, timedelta
import kbo_api
import naver_news
import lineup_parser
import telegram
import state
import user_prefs
from teams import TEAMS

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def _should_poll(game_time: str) -> bool:
    now = datetime.now(KST)
    hour, minute = map(int, game_time.split(":"))
    game_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return game_dt - timedelta(hours=3) <= now < game_dt + timedelta(hours=1)


def _load_or_fetch_state(team_code: str) -> dict:
    s = state.load(team_code)
    if s:
        return s

    result = kbo_api.get_today_team_game(team_code)
    if not result:
        return {}

    all_games = [kbo_api.get_game_detail(gid) for gid in result["all_game_ids"]]
    team_game = next(
        (g for g in all_games if g.get("homeTeamCode") == team_code or g.get("awayTeamCode") == team_code),
        None,
    )
    if not team_game or team_game.get("cancel"):
        return {}

    s = {
        "has_game": True,
        "cancelled": False,
        "game_time": team_game["gameDateTime"][11:16],
        "game_id": team_game["gameId"],
        "lineup_sent": False,
        "cancel_sent": False,
    }
    state.save(team_code, s)
    return s


def _poll_team(team_code: str) -> None:
    users = user_prefs.get_users_for_team(team_code)
    if not users:
        return

    s = _load_or_fetch_state(team_code)
    if not s.get("has_game") or s.get("cancelled") or s.get("lineup_sent"):
        return

    game_time = s.get("game_time", "")
    if not game_time or not _should_poll(game_time):
        return

    log.info("%s 라인업 폴링 실행 (game_time=%s)", team_code, game_time)
    team_info = TEAMS.get(team_code, {"name": team_code, "short": team_code, "emoji": "⚾"})

    article = naver_news.search_lineup_article(team_info["short"])
    if not article:
        log.info("%s 라인업 기사 없음, 5분 후 재시도", team_code)
        return

    today = datetime.now(KST).strftime("%Y-%m-%d")
    article_text = naver_news.fetch_article_text(article["link"])
    result = lineup_parser.parse_lineup(article_text, today, team_info["name"])
    log.info("%s GPT 파싱 결과: found=%s, reason=%s", team_code, result.get("found"), result.get("reason"))

    if result.get("found") and result.get("reason") == "정상":
        pitcher = result["pitcher"]
        lineup_str = "\n".join(
            f"{p['order']}번 {p['position']}: {p['name']}"
            for p in result["lineup"]
        )
        text = (
            f"⚾ {team_info['short']} 라인업 나왔다! {team_info['emoji']}\n\n"
            f"📝 선발투수: {pitcher}\n\n"
            f"📋 타순\n{lineup_str}\n\n"
            f"🔗 기사 링크: {article['link']}"
        )
        for chat_id in users:
            telegram.send(text, chat_id)
        s["lineup_sent"] = True
        state.save(team_code, s)
        log.info("%s 라인업 발송 완료 (users=%d)", team_code, len(users))

    elif result.get("reason") == "경기취소" and not s.get("cancel_sent"):
        team_name = team_info["name"]
        for chat_id in users:
            telegram.send(f"⚾ 오늘 {team_name} 경기가 취소되었습니다 😢", chat_id)
        s.update({"cancel_sent": True, "cancelled": True})
        state.save(team_code, s)
        log.info("%s 경기 취소 알림 발송", team_code)


def run() -> None:
    active_teams = user_prefs.get_all_active_teams()
    for team_code in active_teams:
        try:
            _poll_team(team_code)
        except Exception as e:
            log.error("%s 라인업 폴링 오류: %s", team_code, e)
