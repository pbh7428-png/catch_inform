"""Convert a supported index name to its ETF ticker."""

import sys
from typing import Optional


TICKERS = {
    "S&P500": "SPY",
    "나스닥": "QQQ",
}


def find_ticker(name: str) -> Optional[str]:
    """Return the ticker for a supported name, ignoring surrounding spaces."""
    return TICKERS.get(name.strip().upper())


def main() -> None:
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    # Keep Python's configured locale encoding for redirected streams and their shell pipelines.
    if sys.stdin.isatty() and hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")
    if sys.stdout.isatty() and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    prompt = "종목명을 입력하세요 (S&P500 또는 나스닥): " if interactive else ""
    try:
        name = input(prompt)
    except EOFError:
        name = ""

    ticker = find_ticker(name)
    if ticker is None:
        print("종목을 찾을 수 없습니다.")
        return

    print(ticker)


if __name__ == "__main__":
    main()
