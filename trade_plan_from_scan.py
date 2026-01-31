import argparse
from datetime import datetime

import pandas as pd
import yfinance as yf


def calculate_bollinger(prices, period=20):
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return upper, sma, lower


def fetch_exit_levels(ticker):
    """Fetch 20MA and Bollinger upper band from recent history."""
    try:
        hist = yf.Ticker(ticker).history(period="60d")
        if hist.empty or len(hist) < 20:
            return None
        upper, ma20, _ = calculate_bollinger(hist["Close"], period=20)
        return {
            "20MA": float(ma20.iloc[-1]),
            "Boll_Upper": float(upper.iloc[-1]),
        }
    except Exception:
        return None


def load_scan_csv(path):
    df = pd.read_csv(path)
    required_cols = {"股票", "價格", "評分"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
    return df


def is_us_ticker(ticker):
    return not str(ticker).upper().endswith(".HK")


def build_trade_plan(df, total_budget):
    df = df.sort_values("評分", ascending=False)
    df = df[df["股票"].map(is_us_ticker)]
    df = df.head(20).copy()

    count = len(df)
    if count == 0:
        return pd.DataFrame()

    per_budget = total_budget / count
    rows = []
    for _, row in df.iterrows():
        ticker = row["股票"]
        price = float(row["價格"])
        score = row["評分"]

        shares = int(per_budget // price) if price > 0 else 0
        invested = shares * price
        leftover = per_budget - invested

        exit_levels = fetch_exit_levels(ticker)
        if exit_levels:
            take_profit = exit_levels["Boll_Upper"]
            stop_loss = exit_levels["20MA"]
        else:
            take_profit = None
            stop_loss = None

        rows.append(
            {
                "股票": ticker,
                "評分": score,
                "現價": round(price, 2),
                "每股預算": round(per_budget, 2),
                "買入股數": shares,
                "預計投入": round(invested, 2),
                "預算剩餘": round(leftover, 2),
                "止盈(上軌)": round(take_profit, 2) if take_profit else "",
                "止損(20MA)": round(stop_loss, 2) if stop_loss else "",
            }
        )

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Build trade plan from scan CSV.")
    parser.add_argument("csv_path", help="Path to scan_YYYYMMDD_HHMM.csv")
    parser.add_argument("--budget", type=float, default=1300, help="Total budget in USD")
    args = parser.parse_args()

    df = load_scan_csv(args.csv_path)
    plan_df = build_trade_plan(df, args.budget)

    if plan_df.empty:
        print("❌ 沒有可用的美股資料。")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output = f"trade_plan_{timestamp}.csv"
    plan_df.to_csv(output, index=False, encoding="utf-8-sig")

    print("✅ 已產生交易計劃")
    print(f"📄 輸出檔案: {output}")
    print(f"📊 股票數量: {len(plan_df)}")
    print(f"💰 總本金: {args.budget} USD")


if __name__ == "__main__":
    main()
