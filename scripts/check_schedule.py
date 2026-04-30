import os
import requests
from datetime import datetime
import pytz

MY_TEAM_CODE = "HH"
MY_TEAM_NAME = "한화"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def check_kbo_schedule():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    today = now.strftime('%Y-%m-%d')

    # 1. 오늘 KBO 일정 (calendar API)
    try:
        resp = requests.get(
            "https://api-gw.sports.naver.com/schedule/calendar",
            params={
                "upperCategoryId": "kbaseball",
                "categoryIds": ",kbo,kbs,kbaseballetc,premier12,apbc",
                "date": today
            },
            headers=HEADERS
        )
        resp.raise_for_status()
        cal_data = resp.json()
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return

    today_data = next((d for d in cal_data['result']['dates'] if d['ymd'] == today), None)
    if not today_data:
        print("오늘 일정 없음")
        return

    # 팀코드가 있는 KBO 경기만
    kbo_games = [g for g in today_data['gameInfos'] if g['homeTeamCode'] and g['awayTeamCode']]
    if not kbo_games:
        print("오늘 KBO 경기 없음")
        return

    # 2. 각 경기 상세 정보
    game_details = []
    for g in kbo_games:
        try:
            r = requests.get(
                f"https://api-gw.sports.naver.com/schedule/games/{g['gameId']}",
                headers=HEADERS
            )
            r.raise_for_status()
            game_details.append(r.json()['result']['game'])
        except Exception as e:
            print(f"Error fetching game {g['gameId']}: {e}")

    if not game_details:
        return

    # 3. 한화 경기 찾기
    hw = next(
        (g for g in game_details if g['homeTeamCode'] == MY_TEAM_CODE or g['awayTeamCode'] == MY_TEAM_CODE),
        None
    )
    if not hw:
        print("오늘 한화 경기 없음")
        return

    # 경기 취소
    if hw['cancel']:
        send_telegram("⚾ 오늘 한화 경기가 취소되었습니다 😢")
        return

    is_home = hw['homeTeamCode'] == MY_TEAM_CODE
    opponent  = hw['awayTeamName']  if is_home else hw['homeTeamName']
    stadium   = hw['stadium']
    game_time = hw['gameDateTime'][11:16]
    hw_starter  = hw['homeStarterName']  if is_home else hw['awayStarterName']
    opp_starter = hw['awayStarterName']  if is_home else hw['homeStarterName']
    hw_starter  = hw_starter  or '미정'
    opp_starter = opp_starter or '미정'

    # 4. 전체 경기 한줄 목록
    all_lines = []
    for g in sorted(game_details, key=lambda x: x['gameDateTime']):
        t  = g['gameDateTime'][11:16]
        hs = g['homeStarterName'] or '미정'
        as_ = g['awayStarterName'] or '미정'
        all_lines.append(f"{g['awayTeamName']} {as_} vs {g['homeTeamName']} {hs} / {g['stadium']}, {t}")

    game_link = f"https://sports.naver.com/game/{hw['gameId']}/record"

    message = (
        f"⚾ 오늘 한화 경기 있어요! 신한 SOL뱅크 경기예측 & 비더레전드 GOGO!\n\n"
        f"📅 {now.month}월 {now.day}일\n"
        f"⏰ {game_time}\n"
        f"🆚 {opponent}\n"
        f"🏟️ {stadium} ({'🏠 홈' if is_home else '✈️ 원정'})\n"
        f"⚾ 한화 {hw_starter} vs {opponent} {opp_starter}\n\n"
        f"📋 오늘 KBO 전체\n"
        + "\n".join(all_lines) +
        f"\n\n라인업 나오면 다시 알려드릴게요 👀\n🔗 {game_link}"
    )
    send_telegram(message)


def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = "8282954323"
    if not token:
        print("Telegram token missing.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text})
    if res.status_code == 200:
        print("Telegram message sent successfully.")
    else:
        print(f"Failed to send Telegram message: {res.text}")


if __name__ == "__main__":
    check_kbo_schedule()
