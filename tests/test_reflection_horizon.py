"""Reflection holding days follow investment horizon in long-term mode."""

from unittest import mock

import pytest

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


@pytest.mark.unit
def test_trading_graph_init_applies_mode_profile():
    with mock.patch("tradingagents.graph.trading_graph.set_config"), \
         mock.patch("tradingagents.graph.trading_graph.os.makedirs"), \
         mock.patch("tradingagents.graph.trading_graph.create_llm_client") as mock_llm, \
         mock.patch("tradingagents.graph.trading_graph.TradingMemoryLog"), \
         mock.patch("tradingagents.graph.trading_graph.GraphSetup") as mock_setup, \
         mock.patch("tradingagents.graph.trading_graph.Propagator"), \
         mock.patch("tradingagents.graph.trading_graph.Reflector"), \
         mock.patch("tradingagents.graph.trading_graph.SignalProcessor"), \
         mock.patch("tradingagents.graph.trading_graph.ConditionalLogic"):
        mock_client = mock.Mock()
        mock_client.get_llm.return_value = mock.Mock()
        mock_llm.return_value = mock_client
        mock_setup.return_value.setup_graph.return_value.compile.return_value = mock.Mock()

        graph = TradingAgentsGraph(
            config={
                **DEFAULT_CONFIG,
                "investment_mode": "long_term",
                "investment_horizon": "6m",
            },
            debug=False,
        )
        assert graph.config["reflection_holding_days"] == 126
        assert graph.config["market_lookback_days"] == 756
