"""네트워크 없이 수집 파싱, 이슈 묶기, 번역 응답 처리, 화면 문구를 검증한다."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import daily_news
import issue_cluster
import news_fetch
import render
import send_mail
import translate
from news_fetch import Article

NOW = datetime(2026, 10, 11, 3, 0, tzinfo=timezone.utc)
NVDA = {"ticker": "NVDA", "name": "엔비디아", "keywords": ["Nvidia"]}


def rss(*items: str) -> bytes:
    return f'<rss version="2.0"><channel><title>t</title>{"".join(items)}</channel></rss>'.encode("utf-8")


def item(title="Nvidia rises - Reuters", source="Reuters", date="Sat, 10 Oct 2026 19:33:00 GMT") -> str:
    source_tag = f'<source url="https://example.com">{source}</source>' if source else ""
    date_tag = f"<pubDate>{date}</pubDate>" if date else ""
    return f"<item><title>{title}</title><link>https://example.com/a</link>{date_tag}{source_tag}</item>"


def article(title: str, source: str, hours_ago: float = 1) -> Article:
    return Article(title, source, f"https://example.com/{source}", NOW - timedelta(hours=hours_ago))


class ParseRssTest(unittest.TestCase):
    def test_제목_끝의_언론사를_뗀다(self):
        articles, skipped = news_fetch.parse_rss(rss(item()))
        self.assertEqual((articles[0].title, articles[0].source, skipped), ("Nvidia rises", "Reuters", 0))

    def test_언론사_대소문자가_달라도_뗀다(self):
        articles, _ = news_fetch.parse_rss(rss(item("Nvidia rises - CHOSUNBIZ", "Chosunbiz")))
        self.assertEqual(articles[0].title, "Nvidia rises")

    def test_필수_값이_없는_항목은_건너뛰고_센다(self):
        articles, skipped = news_fetch.parse_rss(rss(item(), item(source=""), item(date=""), item(date="어제")))
        self.assertEqual((len(articles), skipped), (1, 3))

    def test_RSS가_아니면_수집_실패(self):
        for body in (b"<html><body>blocked</body></html>", b"not xml"):
            with self.assertRaises(news_fetch.FetchError):
                news_fetch.parse_rss(body)

    def test_24시간_밖의_기사는_뺀다(self):
        articles = [article("a", "A", 1), article("b", "B", 23.9), article("c", "C", 24.1), article("d", "D", -1)]
        self.assertEqual([a.title for a in news_fetch.filter_recent(articles, NOW)], ["a", "b"])

    def test_검색어에_티커와_keywords가_들어간다(self):
        self.assertIn("q=%22NVDA%22+OR+%22Nvidia%22+when%3A1d", news_fetch.build_url(NVDA))


class RelevanceTest(unittest.TestCase):
    def test_티커는_대소문자를_구분하고_단어_경계를_본다(self):
        spy = {"ticker": "SPY", "keywords": ["S&P 500"], "exclude": ["I SPY"]}
        self.assertTrue(issue_cluster.is_relevant("SPY hits record high", spy))
        self.assertTrue(issue_cluster.is_relevant("s&p 500 closes higher", spy))
        self.assertFalse(issue_cluster.is_relevant("Russian spy arrested", spy))
        self.assertFalse(issue_cluster.is_relevant("SPYD dividend update", spy))
        self.assertFalse(issue_cluster.is_relevant("NCT WISH returns with I SPY", spy))

    def test_시세_페이지는_기사로_보지_않는다(self):
        self.assertFalse(issue_cluster.is_relevant("NVDA Oct 2026 call Stock Price, News, Quote & History", NVDA))
        self.assertFalse(issue_cluster.is_relevant("Graphique NVDA270319C00695000 | NVDA Mar 2027 call", NVDA))


class ClusterTest(unittest.TestCase):
    def setUp(self):
        self.articles = [
            article("Nvidia in talks to acquire start-up Reflection AI", "Financial Times", 9),
            article("Nvidia in talks to buy startup Reflection AI: FT", "Seeking Alpha", 8),
            article("Nvidia in talks to invest further in Reflection AI or buy it, FT reports", "Reuters", 7),
            article("Nvidia in talks to invest further in Reflection AI or buy it, FT reports", "reuters", 6),
            article("NVIDIA reportedly discontinuing RTX 5090 GPUs", "VideoCardz", 20),
            article("Nvidia reportedly ending the RTX 5090", "TechPowerUp", 5),
            article("Cerebras compared with Nvidia data center business", "Yahoo Finance", 2),
        ]

    def test_언론사_수가_많은_순으로_두_개(self):
        issues = issue_cluster.top_issues(self.articles, ["NVDA", "Nvidia"])
        self.assertEqual([(i.source_count, len(i.articles)) for i in issues], [(3, 4), (2, 2)])
        self.assertIn("Reflection", issues[0].representative.title)
        self.assertIn("RTX 5090", issues[1].representative.title)

    def test_같은_언론사의_중복_기사는_한_곳으로_센다(self):
        issues = issue_cluster.top_issues(self.articles[2:4], ["Nvidia"])
        self.assertEqual((issues[0].source_count, len(issues[0].articles)), (1, 2))

    def test_동점이면_최신_기사가_있는_묶음이_먼저(self):
        older = article("Apple unveils cheaper headset", "A", 10)
        newer = article("Tesla recalls vehicles over software", "B", 2)
        for order in ([older, newer], [newer, older]):
            self.assertEqual(issue_cluster.top_issues(order)[0].representative, newer)

    def test_종목_문구만_같으면_묶지_않는다(self):
        articles = [article("Nvidia earnings preview", "A"), article("Nvidia hiring freeze", "B")]
        self.assertEqual(len(issue_cluster.cluster(articles, ["Nvidia"])), 2)

    def test_기사가_없으면_빈_목록(self):
        self.assertEqual(issue_cluster.top_issues([]), [])


class TranslateTest(unittest.TestCase):
    def test_앞뒤_설명이_붙어도_JSON을_읽는다(self):
        text = '결과입니다.\n```json\n[{"id": 0, "title_ko": "제목", "summary_ko": "요약"}]\n```'
        self.assertEqual(translate.parse_response(text, [0]), {0: {"title_ko": "제목", "summary_ko": "요약"}})

    def test_빠지거나_빈_항목은_결과에_넣지_않는다(self):
        text = '[{"id": 0, "title_ko": "제목", "summary_ko": ""}, {"id": 9, "title_ko": "x", "summary_ko": "y"}]'
        self.assertEqual(translate.parse_response(text, [0, 1]), {})

    def test_형식이_틀리면_빈_결과(self):
        for text in ("", "죄송합니다", "[1, 2", '{"id": 0}'):
            self.assertEqual(translate.parse_response(text, [0]), {})

    def test_호출이_실패하면_빈_결과(self):
        with mock.patch("translate.subprocess.run", side_effect=FileNotFoundError("claude")):
            self.assertEqual(translate.translate([{"id": 0, "titles": ["a"]}]), {})


class RenderTest(unittest.TestCase):
    def issue(self, translation):
        return {
            "representative": article("Nvidia <b>beats</b>", "Reuters"),
            "source_count": 3,
            "article_count": 4,
            "translation": translation,
        }

    def test_상태별_문구(self):
        results = [
            {"stock": NVDA, "status": "ok", "skipped": 2, "issues": [
                self.issue({"title_ko": "엔비디아 실적 상회", "summary_ko": "요약문"}),
                self.issue(None),
            ]},
            {"stock": {"ticker": "SPY"}, "status": "ok", "skipped": 0, "issues": []},
            {"stock": {"ticker": "QQQ"}, "status": "failed", "error": "요청 실패", "issues": [], "skipped": 0},
        ]
        html = render.render(results, NOW)
        for text in (
            "3곳 보도", "엔비디아 실적 상회", "요약문", "번역 실패", "최근 24시간 뉴스 없음",
            "수집 실패: 요청 실패", "읽지 못한 항목 2건", "수집 시각: 2026-10-11 12:00 KST",
            "2026-10-10 12:00 ~ 2026-10-11 12:00", "Google 뉴스 RSS", "제목만 근거",
        ):
            self.assertIn(text, html)
        self.assertIn("Nvidia &lt;b&gt;beats&lt;/b&gt;", html)
        self.assertNotIn("<b>beats", html)


class CollectTest(unittest.TestCase):
    def test_수집_실패는_그_종목에만_남는다(self):
        with mock.patch("news_fetch.fetch", side_effect=news_fetch.FetchError("요청 실패")):
            result = daily_news.collect(NVDA, NOW)
        self.assertEqual((result["status"], result["issues"]), ("failed", []))

    def test_대표_제목이_번역_요청의_첫_번째다(self):
        articles = [article("Nvidia buys Reflection AI startup", "A"), article("Nvidia buys Reflection AI", "B")]
        with mock.patch("news_fetch.fetch", return_value=(articles, 1)):
            result = daily_news.collect(NVDA, NOW)
        issue = result["issues"][0]
        self.assertEqual(issue["titles"][0], issue["representative"].title)
        self.assertEqual((issue["source_count"], result["skipped"]), (2, 1))


class MainTest(unittest.TestCase):
    def run_main(self, *argv, env=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "tickers.json").write_text('[{"ticker": "NVDA", "keywords": ["Nvidia"]}]', encoding="utf-8")
        if env:
            (self.root / ".env").write_text(env, encoding="utf-8")
        articles = [article("Nvidia buys Reflection AI", "A")]
        with mock.patch("daily_news.ROOT", self.root), \
                mock.patch("sys.argv", ["daily_news.py", *argv]), \
                mock.patch("news_fetch.fetch", return_value=(articles, 0)), \
                mock.patch("translate.translate", return_value={}), \
                mock.patch("send_mail.smtplib.SMTP_SSL") as self.smtp, \
                mock.patch("builtins.print") as self.printed:
            return daily_news.main()

    def test_dry_run은_파일만_만들고_보내지_않는다(self):
        self.assertEqual(self.run_main("--dry-run"), 0)
        files = list((self.root / "output").glob("*.html"))
        self.assertEqual(len(files), 1)
        self.assertIn("번역 실패", files[0].read_text(encoding="utf-8"))
        self.smtp.assert_not_called()

    def test_설정이_없으면_종료_코드_1이고_파일은_남는다(self):
        self.assertEqual(self.run_main(), 1)
        self.assertEqual(len(list((self.root / "output").glob("*.html"))), 1)
        self.smtp.assert_not_called()

    def test_발송하면_로그인하고_비밀번호를_출력하지_않는다(self):
        code = self.run_main(env="GMAIL_ADDRESS=me@gmail.com\nGMAIL_APP_PASSWORD=abcd efgh\n")
        self.assertEqual(code, 0)
        smtp = self.smtp.return_value.__enter__.return_value
        smtp.login.assert_called_once_with("me@gmail.com", "abcdefgh")
        smtp.send_message.assert_called_once()
        self.assertNotIn("abcd", str(self.printed.call_args_list))


class MailTest(unittest.TestCase):
    def write_env(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / ".env"
        path.write_text(text, encoding="utf-8")
        return path

    def test_env를_읽고_받는_주소가_없으면_본인에게(self):
        env = send_mail.load_env(self.write_env("# 주석\nGMAIL_ADDRESS=me@gmail.com\nGMAIL_APP_PASSWORD='abcd efgh'\n"))
        message = send_mail.build_message(env, "제목", "<p>본문</p>")
        self.assertEqual((message["To"], env["GMAIL_APP_PASSWORD"]), ("me@gmail.com", "abcd efgh"))

    def test_값이_없으면_오류에_키_이름만_나온다(self):
        with self.assertRaises(send_mail.MailError) as context:
            send_mail.load_env(self.write_env("GMAIL_ADDRESS=me@gmail.com\nGMAIL_APP_PASSWORD=\n"))
        self.assertIn("GMAIL_APP_PASSWORD", str(context.exception))

    def test_파일이_없으면_안내(self):
        with self.assertRaises(send_mail.MailError):
            send_mail.load_env(Path("없는폴더") / ".env")


if __name__ == "__main__":
    unittest.main()
