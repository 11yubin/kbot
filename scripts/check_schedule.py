import logging
import kbo_api
import telegram
import state
import user_prefs
from teams import TEAMS

log = logging.getLogger(__name__)


def _check_team(team_code: str) -> None:
    users = user_prefs.get_users_for_team(team_code)
    if not users:
        return

    result = kbo_api.get_today_team_game(team_code)
    if not result:
        log.info("오늘 %s 경기 없음", team_code)
        state.save(team_code, {"has_game": False})
        return

    all_games = [kbo_api.get_game_detail(gid) for gid in result["all_game_ids"]]
    team_game = next(
        g for g in all_games
        if g.get("homeTeamCode") == team_code or g.get("awayTeamCode") == team_code
    )

    if team_game.get("cancel"):
        log.info("%s 경기 취소 확인", team_code)
        team_name = TEAMS.get(team_code, {}).get("name", team_code)
        for chat_id in users:
            telegram.send(f"⚾ 오늘 {team_name} 경기가 취소되었습니다 😢", chat_id)
        state.save(team_code, {"has_game": True, "cancelled": True, "cancel_sent": True})
        return

    text = kbo_api.build_schedule_message(team_code, team_game, all_games)
    for chat_id in users:
        telegram.send(text, chat_id)

    state.save(team_code, {
        "has_game": True,
        "cancelled": False,
        "game_time": team_game["gameDateTime"][11:16],
        "game_id": team_game["gameId"],
        "lineup_sent": False,
        "cancel_sent": False,
    })
    log.info("%s 일정 알림 발송 완료 (users=%d)", team_code, len(users))


def run() -> None:
    log.info("일정 확인 시작")
    active_teams = user_prefs.get_all_active_teams()
    if not active_teams:
        log.info("등록된 사용자 없음")
        return
    for team_code in active_teams:
        try:
            _check_team(team_code)
        except Exception as e:
            log.error("%s 일정 확인 오류: %s", team_code, e)
