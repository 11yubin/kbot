import os
import requests
import json
import re
from datetime import datetime
import pytz

def check_kbo_schedule():
    # Set timezone to KST
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    year = now.year
    month = now.month
    day = now.day
    
    url = "https://www.koreabaseball.com/ws/Schedule.asmx/GetMonthSchedule"
    params = {
        "leId": "1",
        "srIdList": "0,1,3,4,5,7,9,6",
        "seasonId": year,
        "gameMonth": f"{month:02d}"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.koreabaseball.com/ws/Schedule.asmx/"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        raw_data = response.json()
        if 'data' not in raw_data:
            print("No 'data' field in response")
            return
            
        rows = json.loads(raw_data['data'])['rows']
        
        my_team = "한화"
        today_game = None
        
        # Parse schedule to find today's game for my_team
        for week in rows:
            for game in week.get('row', []):
                text = game.get('Text', '')
                # Look for today's date in the HTML snippet
                if f'<li class="dayNum">{day}</li>' in text:
                    if my_team in text:
                        today_game = game
                        break
            if today_game: break
            
        if not today_game:
            print(f"오늘({day}일) {my_team} 경기가 없습니다.")
            return

        text = today_game['Text']
        cls = today_game.get('Class', '')

        # Handle finished games (endGame) or scheduled games
        if cls == 'endGame':
            print("이미 종료된 경기입니다.")
            return
            
        # Extract opponent and stadium for scheduled games
        # Example format: <li>한화 : NC [창원]</li>
        home_away_match = re.search(rf'<li>(.*?) : (.*?) \[(.*?)\]</li>', text)
        if home_away_match:
            team1, team2, stadium = home_away_match.groups()
            is_home = (team1 == my_team)
            opponent = team2 if is_home else team1
            
            message = (
                f"⚾ 오늘 {my_team} 경기 있어요! 신한 SOL뱅크 경기예측 & 비더레전드 GOGO!\n\n"
                f"📅 {day}일\n"
                f"🆚 상대: {opponent}\n"
                f"🏟️ 구장: {stadium} ({'🏠 홈경기' if is_home else '✈️ 원정경기'})\n\n"
                "라인업 나오면 다시 알려드릴게요 👀"
            )
            send_telegram(message)
        else:
            print("경기 정보를 파싱할 수 없습니다.")
            
    except Exception as e:
        print(f"Error checking schedule: {e}")

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_BOT_CHAT_ID")
    if not token or not chat_id:
        print("Telegram configuration missing.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print("Telegram message sent successfully.")
    else:
        print(f"Failed to send Telegram message: {res.text}")

if __name__ == "__main__":
    check_kbo_schedule()
