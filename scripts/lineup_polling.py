import os
import requests
import re
from datetime import datetime
import pytz

def poll_lineup():
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.now(tz)
    today_str = now.strftime('%Y-%m-%d')

    # 중복 전송 방지: 당일 라인업 또는 취소 알림이 이미 전송된 경우 종료
    lineup_flag = f'/tmp/kbo_lineup_sent_{today_str}.flag'
    cancel_flag = f'/tmp/kbo_cancel_sent_{today_str}.flag'
    if os.path.exists(lineup_flag) or os.path.exists(cancel_flag):
        print("Already handled today.")
        return

    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Naver API credentials missing.")
        return

    search_url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {"query": "한화 이글스 라인업", "display": 15, "sort": "date"}

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        items = response.json().get('items', [])
    except Exception as e:
        print(f"Error searching Naver News: {e}")
        return

    lineup_article = None
    nine_am = now.replace(hour=9, minute=0, second=0, microsecond=0)

    for item in items:
        try:
            pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S +0900').replace(tzinfo=tz)
        except:
            continue

        if pub_date < nine_am or pub_date.date() != now.date():
            continue

        title = re.sub(r'<[^>]*>', '', item['title'])
        desc = re.sub(r'<[^>]*>', '', item['description'])

        # 한화 기사인지 title로 먼저 확인 (다른 팀 라인업에 한화가 언급된 기사 제외)
        if '한화' not in title:
            continue

        if "선발 라인업" in desc and any(p in desc for p in ["중견수", "우익수", "좌익수", "포수", "유격수", "1루수"]):
            if 'kbaseball' in item['link'] or 'kbaseball' in item['originallink']:
                lineup_article = item
                break

    if not lineup_article:
        print("No lineup article found yet.")
        return

    try:
        article_res = requests.get(lineup_article['link'])
        article_res.encoding = 'utf-8'
        html = article_res.text
        text = re.sub(r'<[^>]*>', ' ', html).replace('&nbsp;', ' ').replace('&amp;', '&')
        text = re.sub(r'\s+', ' ', text).strip()
    except Exception as e:
        print(f"Error fetching article content: {e}")
        return

    # 경기 취소 감지
    cancel_keywords = ['경기 취소', '우천취소', '우천 취소', '취소가 결정', '취소됐다', '취소되었다']
    if any(kw in text for kw in cancel_keywords):
        send_telegram("⚾ 오늘 한화 경기가 취소되었습니다 😢")
        open(cancel_flag, 'w').close()
        return

    positions = ['중견수', '우익수', '좌익수', '지명타자', '1루수', '2루수', '3루수', '포수', '유격수']
    pos_pattern = '|'.join([re.escape(p) for p in positions])
    player_pattern = rf'([가-힣A-Za-z]+)\(({pos_pattern})\)'

    match = re.search(rf'한화[는이가]?\s*({player_pattern}.*?)\s*순으로', text)

    if not match:
        print("Failed to match lineup pattern in article text.")
        return

    full_match_text = match.group(0)
    players = re.findall(player_pattern, full_match_text)

    if len(players) < 8:
        print(f"Insufficient players parsed: {len(players)}")
        return

    pitcher_match = re.search(r'선발투수\s*(?:로\s*)?([가-힣]+?)(?:가|이)?\s*(?:등판|역투)', text)
    pitcher = pitcher_match.group(1) if pitcher_match else '미확인'

    lineup_formatted = "\n".join([f"{i+1}번 {p[1]}: {p[0]}" for i, p in enumerate(players)])

    message = (
        f"⚾ 한화 라인업 나왔다! 🦅\n\n"
        f"📝 \n선발투수: {pitcher}\n\n"
        f"{lineup_formatted}\n\n"
        f"🔗 {lineup_article['link']}"
    )

    send_telegram(message)
    open(lineup_flag, 'w').close()

def send_telegram(text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = "8282954323"
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    poll_lineup()
