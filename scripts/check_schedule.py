import logging
import kbo_api
import telegram
import state

log = logging.getLogger(__name__)


def run() -> None:
    log.info("일정 확인 시작")

    result = kbo_api.get_today_hanhwa_game()
    if not result:
        log.info("오늘 한화 경기 없음")
        state.save({"has_game": False})
        return

    all_games = [kbo_api.get_game_detail(gid) for gid in result["all_game_ids"]]
    hh_game = next(
        g for g in all_games
        if g.get("homeTeamCode") == "HH" or g.get("awayTeamCode") == "HH"
    )

    if hh_game.get("cancel"):
        log.info("경기 취소 확인")
        telegram.send("⚾ 오늘 한화 경기가 취소되었습니다 😢")
        state.save({"has_game": True, "cancelled": True, "cancel_sent": True})
        return

    text = kbo_api.build_schedule_message(hh_game, all_games)
    telegram.send(text)

    state.save({
        "has_game": True,
        "cancelled": False,
        "game_time": hh_game["gameDateTime"][11:16],
        "game_id": hh_game["gameId"],
        "lineup_sent": False,
        "cancel_sent": False,
    })
    log.info("일정 알림 발송 완료 (game_time=%s)", hh_game["gameDateTime"][11:16])
