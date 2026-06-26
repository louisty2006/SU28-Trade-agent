from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from tradingagents.agents.utils.agent_utils import (
    get_indicators,
    get_instrument_context_from_state,
    get_language_instruction,
    get_stock_data,
    get_verified_market_snapshot,
)
from tradingagents.dataflows.config import get_config
from tradingagents.mode_profiles import get_analyst_system_prompt


_INDICATOR_CATALOG = """
Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator.
- close_200_sma: 200 SMA: A long-term trend benchmark.
- close_10_ema: 10 EMA: A responsive short-term average.

MACD Related: macd, macds, macdh
Momentum: rsi
Volatility: boll, boll_ub, boll_lb, atr
Volume: vwma

Select up to 8 complementary indicators. Call get_stock_data first, then get_indicators.
Call get_verified_market_snapshot before exact price/indicator claims.
"""


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = get_instrument_context_from_state(state)
        cfg = get_config()
        lookback = cfg.get("market_lookback_days", 30)

        tools = [
            get_stock_data,
            get_indicators,
            get_verified_market_snapshot,
        ]

        base = get_analyst_system_prompt("market", cfg)
        system_message = (
            base
            + _INDICATOR_CATALOG
            + f" Default look_back_days for get_indicators and get_verified_market_snapshot: {lookback}."
            + " Append a Markdown table at the end of the report."
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}."
                    " Today's date is {current_date}; treat it as 'now' for all analysis and tool-call date ranges. {instrument_context}\n"
                    "{system_message}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
