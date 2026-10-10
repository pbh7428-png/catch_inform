# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 현재 상태

주식 종목 정보를 수집하는 프로젝트를 시작하려는 저장소다. 지금은 커밋이 없는 빈 git 저장소(`master` 브랜치)이며 코드, 기술 스택, 빌드·테스트 명령이 아직 정해지지 않았다.

스택과 구조가 정해지면 이 파일에 실행·테스트 명령과 데이터 흐름(수집 출처 → 저장 → 갱신)을 채운다.

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

## 작업 환경

- Windows 11, 기본 셸은 PowerShell이다.
- 문서, 주석, UI 문구는 한국어로 쓴다.
