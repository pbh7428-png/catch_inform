"""같은 이슈를 다룬 기사를 묶고 보도한 언론사 수로 순위를 매긴다."""

import re
from dataclasses import dataclass

# 제목 토큰의 자카드 유사도가 이 값 이상이면 같은 이슈로 본다.
# 2026-10-11 NVDA·SPY·QQQ 실제 RSS로 0.2/0.3/0.4를 비교해 정했다.
SIMILARITY_THRESHOLD = 0.3
TOP_N = 2

STOPWORDS = frozenset(
    """a an and are as at be by for from has have how in into is it its new of on or
    over says say that the this to up was what when where why will with after amid
    stock stocks share shares inc corp company""".split()
)

# 기사가 아닌 시세·옵션·공시 목록 페이지의 제목.
NOISE_PATTERN = re.compile(
    r"stock price, news|stock price today|quote (&|and) history|interactive stock chart|^form \d"
    r"|[A-Z]{1,5}\d{6}[CP]\d{8}",  # 옵션 계약 기호(예: QQQ270319C00695000)
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Issue:
    articles: tuple
    representative: object  # 묶음 안에서 다른 제목들과 가장 비슷한 기사
    source_count: int  # 서로 다른 언론사 수(단위: 곳)

    @property
    def latest(self):
        return max(article.published for article in self.articles)


def contains_phrase(title: str, phrase: str, ignore_case: bool = True) -> bool:
    """문구가 다른 단어의 일부로 걸리지 않게 앞뒤 경계를 두고 찾는다."""
    pattern = rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])"
    return re.search(pattern, title, re.IGNORECASE if ignore_case else 0) is not None


def is_relevant(title: str, stock: dict) -> bool:
    """제목에 티커(대소문자 구분)나 keywords 문구가 있고 exclude 문구가 없어야 한다."""
    if NOISE_PATTERN.search(title):
        return False
    if any(contains_phrase(title, phrase) for phrase in stock.get("exclude", [])):
        return False
    if contains_phrase(title, stock["ticker"], ignore_case=False):
        return True
    return any(contains_phrase(title, keyword) for keyword in stock.get("keywords", []))


def tokenize(title: str, ignore: frozenset = frozenset()) -> frozenset:
    tokens = set()
    for word in re.findall(r"[a-z0-9&]+", title.lower().replace("'s", "")):
        if len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        if len(word) > 1 and word not in STOPWORDS and word not in ignore:
            tokens.add(word)
    return frozenset(tokens)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def cluster(articles: list, ignore_terms: list = ()) -> list:
    """유사한 제목끼리 이어 묶는다. 모든 기사에 공통인 종목 문구는 유사도에서 뺀다.

    이어 묶기라서 A-B, B-C만 비슷해도 A와 C가 한 묶음이 되고, 주변 기사 한두 건이
    딸려 와 언론사 수가 조금 늘 수 있다. 묶음 전체의 평균 유사도로 합치는 방식은
    2026-10-11 NVDA 자료에서 같은 이슈를 3개로 쪼개 상위 2개를 한 이슈가 차지해 쓰지 않았다.
    """
    ignore = frozenset().union(*(tokenize(term) for term in ignore_terms))
    tokens = [tokenize(article.title, ignore) for article in articles]
    similarity = [[jaccard(a, b) for b in tokens] for a in tokens]

    parent = list(range(len(articles)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(articles)):
        for j in range(i + 1, len(articles)):
            if similarity[i][j] >= SIMILARITY_THRESHOLD:
                parent[find(j)] = find(i)

    groups = {}
    for index in range(len(articles)):
        groups.setdefault(find(index), []).append(index)

    issues = []
    for members in groups.values():
        # 대표 기사: 묶음의 다른 제목들과 유사도 합이 가장 큰 기사. 동점이면 먼저 발행된 기사.
        def centrality(i):
            total = sum(jaccard(tokens[i], tokens[j]) for j in members if j != i)
            return (-total, articles[i].published, articles[i].title, articles[i].source)

        group = tuple(articles[i] for i in members)
        issues.append(
            Issue(
                articles=group,
                representative=articles[min(members, key=centrality)],
                source_count=len({article.source.casefold() for article in group}),
            )
        )
    return issues


def top_issues(articles: list, ignore_terms: list = (), n: int = TOP_N) -> list:
    """언론사 수가 많은 순. 동점이면 최신 기사가 있는 묶음, 그다음 대표 제목 순."""
    issues = cluster(articles, ignore_terms)
    issues.sort(key=lambda issue: issue.representative.title)
    issues.sort(key=lambda issue: issue.latest, reverse=True)
    issues.sort(key=lambda issue: issue.source_count, reverse=True)
    return issues[:n]
