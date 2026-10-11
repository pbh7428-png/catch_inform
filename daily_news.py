"""보유 종목의 최근 24시간 주요 이슈를 모아 HTML로 저장하고 Gmail로 보낸다.

사용법:
    py daily_news.py            수집 → 번역 → 파일 저장 → 메일 발송
    py daily_news.py --dry-run  메일을 보내지 않고 파일만 만든다
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import issue_cluster
import news_fetch
import render
import send_mail
import translate

ROOT = Path(__file__).resolve().parent
# 번역 요청에 넣는 이슈당 제목 수. 대표 제목이 항상 첫 번째다.
MAX_TITLES_PER_ISSUE = 8


def load_stocks(path: Path) -> list:
    stocks = json.loads(path.read_text(encoding="utf-8"))
    for stock in stocks:
        if not stock.get("ticker"):
            raise ValueError(f"{path.name}: ticker가 없는 항목이 있습니다: {stock}")
    return stocks


def collect(stock: dict, now: datetime) -> dict:
    """한 종목의 결과. 실패는 이 종목에만 남기고 다른 종목 처리를 막지 않는다."""
    try:
        articles, skipped = news_fetch.fetch(stock)
    except news_fetch.FetchError as error:
        return {"stock": stock, "status": "failed", "error": str(error), "issues": [], "skipped": 0}

    recent = news_fetch.filter_recent(articles, now)
    relevant = [article for article in recent if issue_cluster.is_relevant(article.title, stock)]
    issues = [
        {
            "representative": issue.representative,
            "titles": [issue.representative.title]
            + [a.title for a in issue.articles if a is not issue.representative],
            "source_count": issue.source_count,
            "article_count": len(issue.articles),
            "translation": None,
        }
        for issue in issue_cluster.top_issues(relevant, news_fetch.search_terms(stock))
    ]
    return {"stock": stock, "status": "ok", "issues": issues, "skipped": skipped}


def add_translations(results: list) -> None:
    issues = [issue for result in results for issue in result["issues"]]
    requests = [
        {"id": index, "titles": issue["titles"][:MAX_TITLES_PER_ISSUE]}
        for index, issue in enumerate(issues)
    ]
    translations = translate.translate(requests)
    for index, issue in enumerate(issues):
        issue["translation"] = translations.get(index)


def main() -> int:
    parser = argparse.ArgumentParser(description="보유 종목 데일리 뉴스")
    parser.add_argument("--dry-run", action="store_true", help="메일을 보내지 않고 HTML 파일만 만든다")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    now = datetime.now(timezone.utc)
    stocks = load_stocks(ROOT / "tickers.json")
    results = [collect(stock, now) for stock in stocks]
    add_translations(results)

    html = render.render(results, now)
    date = render.format_kst(now)[:10]
    output = ROOT / "output" / f"{date}.html"
    output.parent.mkdir(exist_ok=True)
    output.write_text(html, encoding="utf-8")

    for result in results:
        if result["status"] == "failed":
            summary = f"수집 실패 ({result['error']})"
        else:
            failed = sum(1 for issue in result["issues"] if not issue["translation"])
            summary = f"이슈 {len(result['issues'])}개" + (f", 번역 실패 {failed}개" if failed else "")
        print(f"{result['stock']['ticker']}: {summary}")
    print(f"저장: {output}")

    if args.dry_run:
        print("dry-run: 메일을 보내지 않았습니다.")
        return 0
    try:
        recipient = send_mail.send(send_mail.load_env(ROOT / ".env"), f"보유 종목 뉴스 {date}", html)
    except send_mail.MailError as error:
        print(f"메일 발송 실패: {error}")
        return 1
    print(f"메일 발송: {recipient}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
