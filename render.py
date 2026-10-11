"""종목별 결과를 메일용 HTML로 만든다. 메일 앱에서 깨지지 않게 인라인 스타일만 쓴다."""

from datetime import timedelta, timezone
from html import escape

KST = timezone(timedelta(hours=9))


def format_kst(moment) -> str:
    return moment.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def render_issue(issue: dict) -> str:
    article = issue["representative"]
    if issue["translation"]:
        heading = escape(issue["translation"]["title_ko"])
        detail = (
            f'<div style="margin:6px 0;color:#333;">{escape(issue["translation"]["summary_ko"])}</div>'
            f'<div style="font-size:13px;color:#777;">원제: {escape(article.title)}</div>'
        )
    else:
        heading = escape(article.title)
        detail = '<div style="margin:6px 0;font-size:13px;color:#b00020;">번역 실패 — 영어 원문 제목입니다.</div>'
    return (
        '<div style="margin:12px 0;padding:12px;border:1px solid #ddd;border-radius:8px;">'
        f'<div style="font-size:13px;color:#555;">{issue["source_count"]}곳 보도 · 기사 {issue["article_count"]}건</div>'
        f'<div style="font-size:16px;font-weight:bold;margin-top:4px;">{heading}</div>'
        f"{detail}"
        f'<div style="margin-top:6px;font-size:13px;"><a href="{escape(article.link, quote=True)}">'
        f"원문 보기 ({escape(article.source)}, {format_kst(article.published)})</a></div>"
        "</div>"
    )


def render_stock(result: dict) -> str:
    stock = result["stock"]
    parts = [
        f'<h2 style="font-size:18px;margin:24px 0 4px;">{escape(stock["ticker"])} '
        f'<span style="font-weight:normal;color:#777;font-size:14px;">{escape(stock.get("name", ""))}</span></h2>'
    ]
    if result["status"] == "failed":
        parts.append(f'<div style="color:#b00020;">수집 실패: {escape(result["error"])}</div>')
    elif not result["issues"]:
        parts.append('<div style="color:#777;">최근 24시간 뉴스 없음</div>')
    else:
        parts.extend(render_issue(issue) for issue in result["issues"])
    if result.get("skipped"):
        parts.append(
            f'<div style="font-size:13px;color:#b00020;">일부 수집 실패: 읽지 못한 항목 {result["skipped"]}건은 집계에서 빠졌습니다.</div>'
        )
    return "".join(parts)


def render(results: list, now) -> str:
    start = now - timedelta(hours=24)
    body = "".join(render_stock(result) for result in results)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>보유 종목 뉴스 {format_kst(now)[:10]}</title></head>"
        '<body style="margin:0;padding:16px;font-family:sans-serif;font-size:15px;line-height:1.5;color:#111;">'
        '<div style="max-width:600px;margin:0 auto;">'
        f'<h1 style="font-size:20px;margin:0;">보유 종목 뉴스 {format_kst(now)[:10]}</h1>'
        f"{body}"
        '<div style="margin-top:28px;padding-top:12px;border-top:1px solid #ddd;font-size:12px;color:#777;">'
        f"수집 시각: {format_kst(now)} KST<br>"
        f"대상 기간: {format_kst(start)} ~ {format_kst(now)} KST (최근 24시간)<br>"
        "출처: Google 뉴스 RSS<br>"
        "'N곳 보도'는 같은 이슈를 실은 서로 다른 언론사 수이며 조회수가 아닙니다.<br>"
        "번역과 요약은 AI가 기사 제목만 근거로 작성했습니다. 본문은 원문에서 확인하세요."
        "</div></div></body></html>"
    )
