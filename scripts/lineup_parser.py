import json
import os
from openai import OpenAI

_client: OpenAI | None = None

_SYSTEM_PROMPT_TEMPLATE = (
    "Extract the starting lineup from the Korean baseball article below.\n\n"
    "IMPORTANT - what counts as a lineup article:\n"
    "- Only an OFFICIAL starting lineup announcement counts: a same-day article that states the "
    "confirmed starting pitcher AND the full 9-batter batting order with each batter's defensive "
    "position (e.g. 1루수, 우익수), usually published shortly before first pitch.\n"
    "- Columns, commentary, expert-opinion pieces, stat recaps, first-half/season reviews, or any "
    "article that merely mentions a few hitters' names in sequence while discussing team strength "
    "is NOT a lineup announcement, even if it names the team and lists hitters in batting order. "
    'If so, return {{"found": false, "reason": "라인업없음"}}.\n'
    "- The article must state a defensive position for every batter and a named starting pitcher. "
    'If the starting pitcher or any position is not explicitly stated, return {{"found": false, "reason": "라인업없음"}} '
    "— never invent or guess a name or position.\n\n"
    "Other rules:\n"
    "- Output JSON only. No other text. Start your response with {{ and end with }}.\n"
    "- IMPORTANT: Extract ONLY {team_name} lineup. If the article is about another team's lineup, "
    'return {{"found": false, "reason": "라인업없음"}}.\n'
    "- IMPORTANT: Check whether the article is about TODAY's game (date provided by user). "
    "If the article is about a different date's game or a past game recap, "
    'return {{"found": false, "reason": "날짜불일치"}}.\n'
    '- If a full 9-batter lineup with positions and pitcher exists and date matches: found=true, reason="정상"\n'
    '- If game cancelled: found=false, reason="경기취소"\n'
    '- If no qualifying lineup: found=false, reason="라인업없음"\n\n'
    "Output format (the bracketed parts below are placeholders to fill in, never copy them literally):\n"
    '{{"found": true, "reason": "정상", "pitcher": "<투수 실명>", '
    '"lineup": [{{"order": 1, "position": "<수비 포지션>", "name": "<선수 실명>"}}, ...exactly 9 entries...]}}'
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
    return _client


_PLACEHOLDER_VALUES = {"이름", "포지션", "선수 실명", "투수 실명", "수비 포지션"}


def _is_placeholder(value: str) -> bool:
    return not value or not value.strip() or value.strip() in _PLACEHOLDER_VALUES


def _validate(result: dict) -> bool:
    """GPT가 placeholder를 그대로 베끼거나 라인업을 불완전하게 뽑아내는 경우를 걸러낸다."""
    pitcher = result.get("pitcher", "")
    lineup = result.get("lineup", [])
    if _is_placeholder(pitcher):
        return False
    if len(lineup) != 9:
        return False
    for entry in lineup:
        if _is_placeholder(entry.get("position", "")) or _is_placeholder(entry.get("name", "")):
            return False
    return True


def parse_lineup(article_text: str, today: str, team_name: str = "해당 팀") -> dict:
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(team_name=team_name)
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"오늘 날짜: {today}\n\n기사:\n{article_text}"},
        ],
    )
    result = json.loads(response.choices[0].message.content)

    if result.get("found") and result.get("reason") == "정상" and not _validate(result):
        return {"found": False, "reason": "라인업없음"}

    return result
