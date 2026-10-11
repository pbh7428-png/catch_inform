"""Google 뉴스 RSS에서 종목별 최근 기사를 수집한다."""

import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

RSS_URL = "https://news.google.com/rss/search"
TIMEOUT_SECONDS = 15
WINDOW_HOURS = 24


class FetchError(Exception):
    """RSS를 받지 못했거나 RSS로 읽을 수 없을 때."""


@dataclass(frozen=True)
class Article:
    title: str
    source: str
    link: str
    published: datetime


def search_terms(stock: dict) -> list:
    """검색과 관련성 판정에 함께 쓰는 문구. 티커와 설정 파일의 keywords."""
    return [stock["ticker"]] + list(stock.get("keywords", []))


def build_url(stock: dict) -> str:
    query = " OR ".join(f'"{term}"' for term in search_terms(stock))
    params = {"q": f"{query} when:1d", "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return f"{RSS_URL}?{urllib.parse.urlencode(params)}"


def strip_source_suffix(title: str, source: str) -> str:
    """Google 뉴스가 제목 끝에 붙이는 ' - 언론사'를 뗀다."""
    suffix = f" - {source}"
    if source and title.casefold().endswith(suffix.casefold()):
        return title[: -len(suffix)].strip()
    return title


def parse_rss(xml_bytes: bytes) -> tuple:
    """(기사 목록, 읽지 못한 항목 수)를 돌려준다.

    제목·언론사·발행 시각 중 하나라도 없는 항목은 지어내지 않고 건너뛰며 그 수를 센다.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise FetchError(f"RSS 형식 오류: {error}") from error
    if root.tag != "rss":
        raise FetchError(f"RSS가 아닌 응답: <{root.tag}>")

    articles = []
    skipped = 0
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        source = (item.findtext("source") or "").strip()
        link = (item.findtext("link") or "").strip()
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = None
        if not (title and source and link) or published is None or published.tzinfo is None:
            skipped += 1
            continue
        articles.append(Article(strip_source_suffix(title, source), source, link, published))
    return articles, skipped


def filter_recent(articles: list, now: datetime, hours: int = WINDOW_HOURS) -> list:
    start = now - timedelta(hours=hours)
    return [article for article in articles if start <= article.published <= now]


def fetch(stock: dict) -> tuple:
    """한 종목의 RSS를 받아 (기사 목록, 읽지 못한 항목 수)를 돌려준다."""
    request = urllib.request.Request(build_url(stock), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise FetchError(f"요청 실패: {error}") from error
    return parse_rss(body)
