import json
import os
from openai import OpenAI

_client: OpenAI | None = None

SYSTEM_PROMPT = (
    "Extract the starting lineup from the Korean baseball article below.\n\n"
    "Rules:\n"
    "- Output JSON only. No other text. Start your response with { and end with }.\n"
    "- IMPORTANT: Extract ONLY 한화 이글스 lineup. If the article is about another team's lineup, "
    'return {"found": false, "reason": "라인업없음"}.\n'
    '- If lineup exists: found=true, reason="정상"\n'
    '- If game cancelled: found=false, reason="경기취소"\n'
    '- If no lineup: found=false, reason="라인업없음"\n\n'
    "Output format:\n"
    '{"found": true, "reason": "정상", "pitcher": "이름", '
    '"lineup": [{"order": 1, "position": "포지션", "name": "이름"}, ...]}'
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
    return _client


def parse_lineup(article_text: str) -> dict:
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": article_text},
        ],
    )
    return json.loads(response.choices[0].message.content)
