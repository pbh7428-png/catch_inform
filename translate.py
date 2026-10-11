"""선정된 이슈의 제목을 Claude Code(`claude -p`)로 한국어 번역·요약한다.

기사 제목이 Anthropic으로 전송된다. 본문과 개인 정보는 보내지 않는다.
"""

import json
import subprocess
import tempfile

MODEL = "haiku"
TIMEOUT_SECONDS = 180

PROMPT = """아래는 미국 주식 뉴스 이슈 목록이다. 각 이슈의 titles는 같은 이슈를 다룬 영어 기사 제목들이고 첫 번째가 대표 제목이다.

이슈마다 다음 두 가지를 한국어로 써라.
- title_ko: 대표 제목(첫 번째)의 번역.
- summary_ko: titles에 적힌 내용만으로 쓴 한 문장 요약. 무슨 일이 있었는지를 바로 쓰고 "제목", "기사", "내용이다" 같은 말로 끝내지 마라. 제목에 없는 수치, 원인, 전망을 덧붙이지 마라. 제목들이 "보도", "협상 중"처럼 미확정으로 쓴 내용은 확정된 사실처럼 쓰지 마라.

설명 없이 JSON 배열만 출력하라. 형식: [{"id": 0, "title_ko": "...", "summary_ko": "..."}]

이슈 목록:
"""


def build_prompt(issues: list) -> str:
    """issues: [{"id": int, "titles": [str, ...]}]"""
    return PROMPT + json.dumps(issues, ensure_ascii=False, indent=1)


def parse_response(text: str, ids: list) -> dict:
    """{id: {"title_ko", "summary_ko"}}. 형식이 맞지 않거나 빠진 id는 결과에 넣지 않는다."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return {}
    try:
        rows = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}
    if not isinstance(rows, list):
        return {}

    result = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("id") not in ids:
            continue
        title, summary = row.get("title_ko"), row.get("summary_ko")
        if isinstance(title, str) and title.strip() and isinstance(summary, str) and summary.strip():
            result[row["id"]] = {"title_ko": title.strip(), "summary_ko": summary.strip()}
    return result


def translate(issues: list) -> dict:
    """번역 결과를 id별로 돌려준다. 실패한 이슈는 결과에 없다(호출부가 '번역 실패'로 표시)."""
    if not issues:
        return {}
    try:
        completed = subprocess.run(
            ["claude", "-p", "--model", MODEL],
            input=build_prompt(issues),
            capture_output=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
            cwd=tempfile.gettempdir(),  # 프로젝트의 CLAUDE.md가 번역 요청에 섞이지 않게 한다
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"번역 호출 실패: {error}")
        return {}
    if completed.returncode != 0:
        print(f"번역 호출 실패: 종료 코드 {completed.returncode}")
        return {}
    return parse_response(completed.stdout or "", [issue["id"] for issue in issues])
