import argparse
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf


WINDOWS = [30, 60, 90, 120, 180, 365]


def load_trade_plan(path):
    df = pd.read_csv(path)
    required_cols = {"股票", "買入股數", "現價", "止盈(上軌)", "止損(20MA)"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
    return df


def fetch_history(ticker, days):
    # 多抓一點 buffer，確保交易日足夠
    period = f"{days + 10}d"
    hist = yf.Ticker(ticker).history(period=period)
    if hist.empty:
        return hist
    return hist.tail(days)


def simulate_one(ticker, shares, entry_price, tp, sl, days):
    hist = fetch_history(ticker, days)
    if hist.empty or shares <= 0:
        return {
            "status": "no_data",
            "exit_price": None,
            "exit_date": None,
            "final_value": shares * entry_price,
        }

    exited = False
    exit_price = None
    exit_date = None

    for date, row in hist.iterrows():
        high = row["High"]
        low = row["Low"]

        # 同日觸及：止損優先
        if pd.notna(sl) and low <= sl:
            exit_price = sl
            exit_date = date
            exited = True
            break
        if pd.notna(tp) and high >= tp:
            exit_price = tp
            exit_date = date
            exited = True
            break

    if not exited:
        exit_price = hist["Close"].iloc[-1]
        exit_date = hist.index[-1]

    return {
        "status": "exit" if exited else "hold",
        "exit_price": float(exit_price),
        "exit_date": exit_date,
        "final_value": shares * float(exit_price),
    }


def run_backtest(plan_df, start_cash, days):
    cash = start_cash
    entries = 0
    full_exits = 0

    total_value = 0.0

    for _, row in plan_df.iterrows():
        ticker = row["股票"]
        shares = int(row["買入股數"])
        entry_price = float(row["現價"])
        tp = float(row["止盈(上軌)"]) if row["止盈(上軌)"] != "" else None
        sl = float(row["止損(20MA)"]) if row["止損(20MA)"] != "" else None

        if shares <= 0:
            continue

        entries += 1
        result = simulate_one(ticker, shares, entry_price, tp, sl, days)
        total_value += result["final_value"]

        if result["status"] == "exit":
            full_exits += 1

    final_value = total_value
    return {
        "start": start_cash,
        "final": final_value,
        "return_pct": (final_value - start_cash) / start_cash * 100 if start_cash else 0,
        "entries": entries,
        "full_exits": full_exits,
        "half_sells": 0,
        "round_trips": full_exits,
    }


def main():
    parser = argparse.ArgumentParser(description="Backtest from trade_plan CSV.")
    parser.add_argument("csv_path", help="Path to trade_plan_*.csv")
    parser.add_argument("--start", type=float, default=1300, help="Start cash in USD")
    args = parser.parse_args()

    plan_df = load_trade_plan(args.csv_path)

    for days in WINDOWS:
        stats = run_backtest(plan_df, args.start, days)
        print(f"Window: last {days} days")
        print(f"Start:  ${stats['start']:.2f}")
        print(f"Final:  ${stats['final']:.2f}")
        print(f"Return: {stats['return_pct']:.2f}%\n")
        print("Trades:")
        print(f"  Entries:     {stats['entries']}")
        print(f"  Full exits:  {stats['full_exits']}")
        print(f"  Half sells:  {stats['half_sells']}")
        print(f"  Round-trips: {stats['round_trips']}")
        print("\n" + "-" * 40 + "\n")


if __name__ == "__main__":
    main()