import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from ticker_lookup import find_ticker, main


class TickerLookupTests(unittest.TestCase):
    def test_supported_names_return_tickers(self):
        self.assertEqual(find_ticker("S&P500"), "SPY")
        self.assertEqual(find_ticker("나스닥"), "QQQ")

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(find_ticker("  S&P500\t"), "SPY")
        self.assertEqual(find_ticker("\t나스닥  "), "QQQ")

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(find_ticker("s&p500"), "SPY")
        self.assertEqual(find_ticker("S&p500"), "SPY")

    def test_unknown_or_blank_name_has_no_ticker(self):
        self.assertIsNone(find_ticker("NASDAQ"))
        self.assertIsNone(find_ticker(""))
        self.assertIsNone(find_ticker("   "))

    def test_main_prints_not_found_for_unknown_and_blank_input(self):
        for name in ("NASDAQ", ""):
            with self.subTest(name=name):
                output = StringIO()
                with patch("builtins.input", return_value=name):
                    with patch("sys.stdin", StringIO()):
                        with redirect_stdout(output):
                            main()
                self.assertTrue(output.getvalue().endswith("종목을 찾을 수 없습니다.\n"))

    def test_main_prints_ticker_for_supported_name(self):
        for name, ticker in (("S&P500", "SPY"), ("나스닥", "QQQ")):
            with self.subTest(name=name):
                output = StringIO()
                with patch("builtins.input", return_value=name):
                    with patch("sys.stdin", StringIO()):
                        with redirect_stdout(output):
                            main()
                self.assertEqual(output.getvalue(), ticker + "\n")

    def test_main_treats_end_of_input_as_blank(self):
        output = StringIO()
        with patch("builtins.input", side_effect=EOFError):
            with patch("sys.stdin", StringIO()):
                with redirect_stdout(output):
                    main()
        self.assertEqual(output.getvalue(), "종목을 찾을 수 없습니다.\n")


if __name__ == "__main__":
    unittest.main()
