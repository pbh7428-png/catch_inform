# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 현재 상태

보유 미국 주식 종목의 최근 24시간 뉴스에서 많이 보도된 이슈 2개씩을 골라 한국어 메일로 보내는 로컬 스크립트다. 요구사항과 설계는 `docs/planning.md`에 있다. Python 표준 라이브러리만 쓰며 설치할 것이 없다.

```powershell
py daily_news.py --dry-run   # 수집·번역 후 output/YYYY-MM-DD.html만 만든다
py daily_news.py             # 위에 더해 Gmail로 보낸다(.env 필요, .env.example 참고)
py -m unittest               # 네트워크 없이 도는 테스트
```

데이터 흐름: `tickers.json` → `news_fetch.py`(Google 뉴스 RSS, 24시간 필터) → `issue_cluster.py`(관련성 판정, 제목 유사도로 묶기, 언론사 수로 순위) → `translate.py`(`claude -p`로 번역·요약) → `render.py`(HTML) → `send_mail.py`(Gmail SMTP). `daily_news.py`가 이 순서를 잇는다.

`ticker_lookup.py`와 그 테스트는 리뷰 스킬을 시험하던 예제이며 위 흐름과 무관하다.

## 시작할 때

개발은 Claude Code가 맡고 GPT(Codex CLI)가 검토한다. 사용자 전역 스킬(`~/.claude/skills/`) 세 개를 쓴다.

- `dev-kickoff`: 새 프로젝트나 주요 기능을 시작할 때 문제 정의와 PRD/TRD를 정리한다.
- `plan-review-gpt`: 완성한 계획 문서를 GPT에게 검토받는다.
- `code-review-gpt`: 구현과 첫 테스트 뒤 코드 변경을 GPT에게 리뷰받는다.

검토 결과는 `docs/reviews/`에 저장된다. `.agents/skills/`와 `tools/claude_plan_review.ps1`은 Codex가 개발하고 Claude가 검토하던 예전 구성이며 Claude Code에서는 쓰지 않는다.

새 개발은 `dev-kickoff`의 절차를 따른다. 구현 전에 다음을 먼저 정리한다.

- 문제 정의 → 데이터·API·권한 가능성 확인 → 간단한 PRD/TRD 순서로 진행한다. 작은 규모면 `docs/planning.md` 하나에 합친다.
- 내용을 확정 / 가정 / 미정으로 구분하고, 목적·범위·핵심 구조가 달라지는 질문만 1~3개로 묶어 묻는다.
- 로컬 실행인지 온라인 배포인지, 설치와 네트워크가 필요한지 먼저 확인한다. 같은 상위 폴더의 다른 프로젝트(`gpt-ax-value`)의 선택을 그대로 적용하지 않는다.
- 데이터 출처는 존재하는지와 실제로 쓸 수 있는지(이용 약관, 호출 한도, 인증, 지연 시세 여부)를 구분해 확인한다. 확인하지 않은 내용은 가정으로 표시한다.
- 가격·지표·수익률처럼 숫자를 보여줄 때는 의미, 단위, 계산식, 기준 시점을 구현 전에 정한다.
- 수집에 실패했거나 자료가 없는 종목·항목은 0으로 채우거나 다른 값으로 대체하지 않고 누락으로 표시한다.

## 검증

- 게이트 명령은 `py -m unittest`다. 코드를 바꾸면 리뷰로 넘기기 전에 실행한다. 이 PC에서 `python`은 Microsoft Store 연결 스텁이라 실행되지 않으므로 `py` 런처를 쓴다.
- 같은 실패를 고치는 재시도는 6회까지 한다. 넘으면 멈추고 시도한 내용과 오류를 보고한다.
- 테스트 통과는 필요조건이다. 수집한 값이 맞는지는 종목 몇 개를 골라 출처 화면의 값과 직접 대조해 확인한다. GPT 리뷰는 diff만 보므로 값의 정확성을 판정하지 못한다.

## 작업 환경

- Windows 11, 기본 셸은 PowerShell이다.
- 문서, 주석, UI 문구는 한국어로 쓴다.

## 용어

이 프로젝트에서 쓰는 말과 뜻을 적는다. 새 용어를 정하면 여기에 더한다.

- 티커: 거래소에서 종목을 식별하는 기호(예: `SPY`).

## 자료 위치

- 수집 출처: Google 뉴스 RSS 검색(`news.google.com/rss/search`, 키 없음). 제목·언론사·링크·발행 시각만 온다. 조회수와 본문은 없다.
- 종목 목록: `tickers.json`(git 제외). 사용자가 직접 고친다. 원격 저장소가 공개라서 보유 종목은 올리지 않고, 형식 예시만 `tickers.example.json`으로 올린다. 문서와 커밋 메시지에도 보유 종목을 적지 않는다.
- 결과: `output/YYYY-MM-DD.html`(KST 날짜, git 제외). RSS 원자료는 저장하지 않는다.
- 비밀 값: `.env`(git 제외). 값을 출력하거나 로그에 남기지 않는다.

## 결정 기록

날짜, 결정, 이유를 한 줄씩 적는다. 리뷰에서 반려한 선택지와 새로 생긴 규칙도 여기에 남긴다.

- 2026-10-10: 개발은 Claude Code, 검토는 GPT(Codex CLI)가 맡는다. 작업한 모델이 자기 결과를 채점하지 않게 하기 위해서다.
- 2026-10-11: 뉴스 선정은 조회수가 아니라 같은 이슈를 실은 서로 다른 언론사 수로 한다. 조회수를 주는 출처가 없어서다. 화면에는 "N곳 보도"로 적는다.
- 2026-10-11: 전달은 Gmail 발송이다. GitHub Pages(보유 종목 공개), 텔레그램, Tailscale은 사용자가 택하지 않았다.
- 2026-10-11: 번역은 `claude -p --model haiku`로 한다(구독 사용, API 키 없음). API 키 방식으로 바꾸려면 비용이 생기므로 먼저 묻는다.
- 2026-10-11: 제목 유사도 임계값 0.3. 바꿀 때는 NVDA·SPY·QQQ 실제 RSS로 묶음 결과를 다시 확인한다.
- 2026-10-11: 이슈 묶기는 이어 묶기(단일 연결)를 유지한다. 평균 연결과 주변 기사 떼어내기는 실제 자료에서 더 나빴다(근거는 `docs/planning.md` 핵심 규칙).
- 2026-10-11: `tickers.json`의 `keywords`에 `Apple` 같은 일반 단어를 넣지 않는다. 무관한 기사가 상위에 오른다.
- 2026-10-11: 실행 위치는 이 PC다. GitHub Actions는 번역에 API 키와 비용이 들어 당분간 쓰지 않는다.
- 2026-10-11: Windows 작업 스케줄러 작업 "보유종목 데일리 뉴스"가 매일 08:00(KST)에 `run_daily.cmd`를 실행한다. 실행 기록은 `output/run.log`에 쌓인다. 사용자가 로그인해 있을 때만 돌며, 놓친 실행은 PC가 켜지면 바로 돈다.
- 2026-10-11: 비밀 값은 `.env`에만 둔다. `.env.example`은 git에 올라가는 파일이므로 값을 넣지 않는다.
- 2026-10-11: Yahoo Finance RSS는 종목당 19건뿐이고 무관한 기사가 섞여 쓰지 않는다.

## 미검증 가정

아직 확인하지 못한 내용이다. 여기 있는 것은 사실처럼 쓰지 않고, 확인하면 위 칸으로 옮기거나 지운다.

- Google 뉴스 RSS의 자동 수집 허용 범위와 호출 한도는 Google의 1차 문서로 확인하지 못했다. 개인용·하루 1회로만 쓰고 결과를 공개하거나 재배포하지 않는다.
