import json
import os
from openai import OpenAI

_client: OpenAI | None = None

_SYSTEM_PROMPT_TEMPLATE = (
    "Extract the starting lineup from the Korean baseball article below.\n\n"
    "Rules:\n"
    "- Output JSON only. No other text. Start your response with {{ and end with }}.\n"
    "- IMPORTANT: Extract ONLY {team_name} lineup. If the article is about another team's lineup, "
    'return {{"found": false, "reason": "라인업없음"}}.\n'
    "- IMPORTANT: Check whether the article is about TODAY's game (date provided by user). "
    "If the article is about a different date's game or a past game recap, "
    'return {{"found": false, "reason": "날짜불일치"}}.\n'
    '- If lineup exists and date matches: found=true, reason="정상"\n'
    '- If game cancelled: found=false, reason="경기취소"\n'
    '- If no lineup: found=false, reason="라인업없음"\n\n'
    "Output format:\n"
    '{{"found": true, "reason": "정상", "pitcher": "이름", '
    '"lineup": [{{"order": 1, "position": "포지션", "name": "이름"}}, ...]}}'
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
    return _client


def parse_lineup(article_text: str, today: str, team_name: str = "해당 팀") -> dict:
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(team_name=team_name)
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"오늘 날짜: {today}\n\n기사:\n{article_text}"},
        ],
    )
    return json.loads(response.choices[0].message.content)
