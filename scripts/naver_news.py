import os
import re
import requests

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def search_lineup_article() -> dict | None:
    """한화 라인업 기사를 검색해 발견 시 {"link": ...} 반환, 없으면 None."""
    resp = requests.get(
        "https://openapi.naver.com/v1/search/news.json",
        params={"query": "한화 이글스 라인업", "display": 10, "sort": "date"},
        headers={
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        },
        timeout=10,
    )
    resp.raise_for_status()

    for item in resp.json().get("items", []):
        title = item.get("title", "")
        desc = item.get("description", "")
        link = item.get("link", "")
        if "kbaseball" in link and "한화" in title and (
            "라인업" in title or "라인업" in desc
        ):
            return {"link": link}
    return None


def fetch_article_text(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    resp.raise_for_status()

    text = resp.text
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"const\s+\w+[^;]*;", "", text)
    text = re.sub(r"//.*", "", text)
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#x27;", "'")
    )
    text = re.sub(r"&#[0-9]+;", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    body_idx = text.find("본문 바로가기")
    if body_idx != -1:
        text = text[body_idx:]
    close_idx = text.find('닫기"')
    if close_idx != -1:
        text = text[close_idx + len('닫기"'):]

    start_match = re.search(r"\[[^\]]{2,40}기자\]", text)
    end_keyword = "현장에서 작성된 기사입니다"
    start = start_match.start() if start_match else 0
    end = text.find(end_keyword)

    return text[start: end + len(end_keyword)] if end != -1 else text[start:]
