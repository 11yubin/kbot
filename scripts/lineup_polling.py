import logging
from datetime import datetime, timezone, timedelta
import kbo_api
import naver_news
import lineup_parser
import telegram
import state

log = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def _should_poll(game_time: str) -> bool:
    now = datetime.now(KST)
    hour, minute = map(int, game_time.split(":"))
    game_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    # 경기 3시간 전 ~ 경기 시작 1시간 후 사이에만 폴링
    return game_dt - timedelta(hours=3) <= now < game_dt + timedelta(hours=1)


def _load_or_fetch_state() -> dict:
    """state가 없으면 KBO API를 직접 조회해 복원."""
    s = state.load()
    if s:
        return s

    result = kbo_api.get_today_hanhwa_game()
    if not result:
        return {}

    all_games = [kbo_api.get_game_detail(gid) for gid in result["all_game_ids"]]
    hh_game = next(
        (g for g in all_games if g.get("homeTeamCode") == "HH" or g.get("awayTeamCode") == "HH"),
        None,
    )
    if not hh_game or hh_game.get("cancel"):
        return {}

    s = {
        "has_game": True,
        "cancelled": False,
        "game_time": hh_game["gameDateTime"][11:16],
        "game_id": hh_game["gameId"],
        "lineup_sent": False,
        "cancel_sent": False,
    }
    state.save(s)
    return s


def run() -> None:
    s = _load_or_fetch_state()

    if not s.get("has_game") or s.get("cancelled") or s.get("lineup_sent"):
        return

    game_time = s.get("game_time", "")
    if not game_time or not _should_poll(game_time):
        return

    log.info("라인업 폴링 실행 (game_time=%s)", game_time)

    article = naver_news.search_lineup_article()
    if not article:
        log.info("라인업 기사 없음, 5분 후 재시도")
        return

    article_text = naver_news.fetch_article_text(article["link"])
    result = lineup_parser.parse_lineup(article_text)

    if result.get("found") and result.get("reason") == "정상":
        pitcher = result["pitcher"]
        lineup_str = "\n".join(
            f"{p['order']}번 {p['position']}: {p['name']}"
            for p in result["lineup"]
        )
        telegram.send(
            f"⚾ 한화 라인업 나왔다! 🦅\n\n"
            f"📝 선발투수: {pitcher}\n\n"
            f"📋 타순\n{lineup_str}\n\n"
            f"🔗 기사 링크: {article['link']}"
        )
        s["lineup_sent"] = True
        state.save(s)
        log.info("라인업 발송 완료")

    elif result.get("reason") == "경기취소" and not s.get("cancel_sent"):
        telegram.send("⚾ 오늘 한화 경기가 취소되었습니다 😢")
        s.update({"cancel_sent": True, "cancelled": True})
        state.save(s)
        log.info("경기 취소 알림 발송")
