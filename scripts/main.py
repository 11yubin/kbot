import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import check_schedule
import lineup_polling
import bot_commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


def main() -> None:
    bot_commands.start()

    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    scheduler.add_job(
        check_schedule.run,
        CronTrigger(hour=10, minute=0, timezone="Asia/Seoul"),
        id="check_schedule",
        name="KBO 일정 확인",
        misfire_grace_time=300,
    )
    scheduler.add_job(
        lineup_polling.run,
        IntervalTrigger(minutes=5),
        id="lineup_polling",
        name="라인업 폴링",
        misfire_grace_time=60,
    )

    log.info("스케줄러 시작 (check_schedule: 매일 10:00 KST, lineup_polling: 5분 간격)")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("스케줄러 종료")


if __name__ == "__main__":
    main()
