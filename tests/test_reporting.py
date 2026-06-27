"""Report parity: the shared writer produces the report tree for the CLI and the
programmatic API alike (#1037)."""

from types import SimpleNamespace

import pytest

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.reporting import write_report_tree


@pytest.fixture(autouse=True)
def _reset_config():
    import copy

    import tradingagents.default_config as default_config
    from tradingagents.dataflows import config as cfg_mod

    cfg_mod._config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    yield
    cfg_mod._config = copy.deepcopy(default_config.DEFAULT_CONFIG)


def _state():
    return {
        "market_report": "MKT",
        "news_report": "NEWS",
        "investment_debate_state": {"judge_decision": "RM PLAN"},
        "trader_investment_plan": "TRADE",
        "risk_debate_state": {"judge_decision": "PM DECISION"},
    }


@pytest.mark.unit
def test_write_report_tree_creates_files(tmp_path):
    out = write_report_tree(_state(), "AAPL", tmp_path)
    assert out.name == "complete_report.md"
    assert (tmp_path / "1_analysts" / "market.md").read_text() == "MKT"
    assert (tmp_path / "1_analysts" / "news.md").read_text() == "NEWS"
    assert (tmp_path / "2_research" / "manager.md").read_text() == "RM PLAN"
    assert (tmp_path / "3_trading" / "trader.md").read_text() == "TRADE"
    assert (tmp_path / "5_portfolio" / "decision.md").read_text() == "PM DECISION"
    complete = out.read_text()
    assert "Trading Analysis Report: AAPL" in complete
    assert "MKT" in complete and "PM DECISION" in complete


@pytest.mark.unit
def test_save_reports_explicit_path(tmp_path):
    # Unbound: with an explicit save_path, the method doesn't touch self/config.
    out = TradingAgentsGraph.save_reports(None, _state(), "AAPL", save_path=tmp_path)
    assert (tmp_path / "complete_report.md").exists()
    assert out == tmp_path / "complete_report.md"


@pytest.mark.unit
def test_write_investment_memo_long_term(tmp_path, monkeypatch):
    from tradingagents.dataflows import config as cfg_mod
    from tradingagents.dataflows import fundamental_analytics

    cfg_mod.set_config({"investment_mode": "long_term", "investment_horizon": "3y"})
    monkeypatch.setattr(fundamental_analytics, "fetch_ticker_info", lambda _ticker: {})
    state = {
        **_state(),
        "fundamentals_report": "FUND",
        "risk_debate_state": {"judge_decision": "PM LONG TERM"},
    }
    out = write_report_tree(state, "AAPL", tmp_path)
    assert out.exists()
    memo = tmp_path / "investment_memo.md"
    assert memo.exists()
    text = memo.read_text()
    assert "Investment Memo" in text
    assert "PM LONG TERM" in text


@pytest.mark.unit
def test_long_term_report_starts_with_company_overview(tmp_path, monkeypatch):
    from tradingagents.dataflows import config as cfg_mod
    from tradingagents.dataflows import fundamental_analytics

    cfg_mod.set_config({"investment_mode": "long_term", "investment_horizon": "6m"})
    monkeypatch.setattr(
        fundamental_analytics,
        "fetch_ticker_info",
        lambda _ticker: {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3_000_000_000_000,
            "longBusinessSummary": "Apple designs and sells consumer technology products.",
        },
    )

    out = write_report_tree(_state(), "AAPL", tmp_path)
    complete = out.read_text()
    memo = (tmp_path / "investment_memo.md").read_text()

    assert "## Company & Industry Overview" in complete
    assert complete.index("## Company & Industry Overview") < complete.index(
        "## I. Analyst Team Reports"
    )
    assert "Apple designs and sells consumer technology products." in complete
    assert memo.index("## Company & Industry Overview") < memo.index(
        "## Executive Summary"
    )


@pytest.mark.unit
def test_long_term_report_lists_holding_and_prices(tmp_path, monkeypatch):
    from tradingagents.dataflows import config as cfg_mod
    from tradingagents.dataflows import fundamental_analytics

    cfg_mod.set_config({"investment_mode": "long_term", "investment_horizon": "6m"})
    monkeypatch.setattr(fundamental_analytics, "fetch_ticker_info", lambda _ticker: {})
    state = {
        **_state(),
        "trader_investment_plan": (
            "**Entry Price (建議入場價)**: 189.5\n"
            "**Target / Exit Price (建議離場價)**: 220.0\n"
            "**Stop Loss (止蝕價)**: 178.0\n"
        ),
    }
    out = write_report_tree(state, "AAPL", tmp_path)
    complete = out.read_text()
    assert "## 投資參數 / Investment Parameters" in complete
    assert "6 個月" in complete
    assert "189.5" in complete  # entry
    assert "220.0" in complete  # exit / target
    assert "178.0" in complete  # stop


@pytest.mark.unit
def test_save_reports_defaults_under_results_dir(tmp_path):
    mock_self = SimpleNamespace(config={"results_dir": str(tmp_path)})
    out = TradingAgentsGraph.save_reports(mock_self, _state(), "AAPL")
    assert out.exists()
    assert out.parent.parent.name == "reports"  # results_dir/reports/AAPL_<stamp>/...
    assert out.parent.name.startswith("AAPL_")
