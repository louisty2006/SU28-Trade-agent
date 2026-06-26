"""Stock universe loaders for the long-term screener."""

from __future__ import annotations

from pathlib import Path

# Minimal fallback when network fetch is unavailable (tests / offline).
_FALLBACK_SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BRK-B", "JPM", "V", "UNH",
    "XOM", "JNJ", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP", "KO",
]

_FALLBACK_NASDAQ100 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "NFLX",
]


def _read_ticker_file(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


# Wikipedia returns HTTP 403 to the default urllib user-agent that pandas uses,
# so every constituent fetch must go through a browser-like UA. Read the page
# ourselves and hand the HTML to read_html.
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def _read_wiki_tables(url: str, match: str):
    import io

    import pandas as pd
    import requests

    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=20)
    resp.raise_for_status()
    return pd.read_html(io.StringIO(resp.text), match=match)


def load_universe(name: str, universe_file: str | Path | None = None) -> list[str]:
    """Load ticker list by universe name or custom file path.

    Supported names:
      sp500, nasdaq100        — large caps (cleanest lists)
      sp400                   — S&P MidCap 400
      sp600                   — S&P SmallCap 600 (smaller, more "hidden gem" room)
      all_us / us             — every common stock listed on NASDAQ/NYSE/AMEX
                                (~6000+, slow; pair with max_tickers in the runner)
    """
    if universe_file:
        return _read_ticker_file(Path(universe_file))

    key = (name or "sp500").lower().replace("-", "").replace("_", "").replace("&", "")
    if key in ("sp500", "sp500", "spx"):
        return _fetch_sp500_constituents()
    if key in ("nasdaq100", "ndx", "qqq"):
        return _fetch_nasdaq100_constituents()
    if key in ("sp400", "midcap", "mid"):
        return _fetch_wikipedia_constituents(
            "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies", _FALLBACK_SP500
        )
    if key in ("sp600", "smallcap", "small"):
        return _fetch_wikipedia_constituents(
            "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies", _FALLBACK_SP500
        )
    if key in ("allus", "us", "all", "alllisted"):
        return _fetch_all_us_listed()
    raise ValueError(
        f"Unknown universe {name!r}; use sp500, nasdaq100, sp400, sp600, all_us, "
        "or --universe-file"
    )


def _fetch_sp500_constituents() -> list[str]:
    try:
        tables = _read_wiki_tables(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol"
        )
        if tables:
            symbols = tables[0]["Symbol"].astype(str).str.replace(".", "-", regex=False)
            return sorted(symbols.tolist())
    except Exception:
        pass
    return list(_FALLBACK_SP500)


def _fetch_nasdaq100_constituents() -> list[str]:
    try:
        tables = _read_wiki_tables("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker")
        for table in tables:
            if "Ticker" in table.columns:
                return sorted(table["Ticker"].astype(str).str.strip().tolist())
    except Exception:
        pass
    return list(_FALLBACK_NASDAQ100)


def _fetch_wikipedia_constituents(url: str, fallback: list[str]) -> list[str]:
    """Generic Wikipedia constituent-table fetch matching a Symbol/Ticker column."""
    try:
        tables = _read_wiki_tables(url, "Symbol")
        for table in tables:
            for col in ("Symbol", "Ticker", "Ticker symbol"):
                if col in table.columns:
                    symbols = (
                        table[col]
                        .astype(str)
                        .str.strip()
                        .str.replace(".", "-", regex=False)
                    )
                    return sorted(s for s in symbols.tolist() if s and s != "nan")
    except Exception:
        pass
    return list(fallback)


def _fetch_all_us_listed() -> list[str]:
    """All common stocks on NASDAQ + NYSE/AMEX via the NASDAQ Trader symbol directory.

    Filters out ETFs and test issues so the list stays equities-only. This is the
    broadest free source (~6000+ symbols) and is where smaller, less-covered names
    live. Falls back to the S&P 500 list if the directory is unreachable.
    """
    try:
        import pandas as pd

        frames = []
        # NASDAQ-listed: Symbol|Security Name|...|Test Issue|...|ETF|...
        nas = pd.read_csv(
            "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", sep="|"
        )
        nas = nas[(nas.get("Test Issue") == "N") & (nas.get("ETF") != "Y")]
        frames.append(nas.rename(columns={"Symbol": "sym"})[["sym"]])

        # Other (NYSE/AMEX): ACT Symbol|...|ETF|...|Test Issue|...
        other = pd.read_csv(
            "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", sep="|"
        )
        other = other[(other.get("Test Issue") == "N") & (other.get("ETF") != "Y")]
        frames.append(other.rename(columns={"ACT Symbol": "sym"})[["sym"]])

        syms = pd.concat(frames)["sym"].astype(str).str.strip()
        # Drop directory footer rows and non-common share classes (warrants/units).
        syms = syms[~syms.str.contains(r"[\.\$]", regex=True, na=False)]
        syms = syms[syms.str.match(r"^[A-Z]{1,5}$", na=False)]
        return sorted(set(syms.tolist()))
    except Exception:
        pass
    return list(_FALLBACK_SP500)
