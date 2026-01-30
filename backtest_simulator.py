"""
回測模擬器：365 天逐日回測

- 每日僅使用「當日及之前」的數據，無偷看未來。
- 依 AI 當日決策（持有/加碼/減碼/出場、新買入）以當日收盤價模擬執行。
- 追蹤持倉與組合價值，產出報酬與摘要。
"""

import os
import csv
import json
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple

from config import (
    REIKAN_DAILY_JSON,
    BACKTEST_INITIAL_CASH,
    BACKTEST_PCT_PER_NEW_ENTRY,
    BACKTEST_ADD_PCT,
    BACKTEST_REDUCE_PCT,
)


def get_trading_days(start: date, end: date) -> List[date]:
    """取得 [start, end] 內的交易日（排除週六日，不排除假日）。"""
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:  # 0=Mon .. 4=Fri
            days.append(d)
        d += timedelta(days=1)
    return days


def prev_trading_day(d: date) -> date:
    """d 的前一個交易日（不含週末）。"""
    out = d - timedelta(days=1)
    while out.weekday() >= 5:
        out -= timedelta(days=1)
    return out


def load_report_decision(report_dir: str) -> Optional[Dict]:
    """從報告目錄讀取 REIKAN_daily_report.json，回傳 decision 或 None。"""
    path = os.path.join(report_dir, REIKAN_DAILY_JSON)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("decision")
    except Exception:
        return None


def load_report_positions_prices(report_dir: str) -> Dict[str, float]:
    """從報告 JSON 讀取當日持倉的收盤價 {ticker: price}。"""
    path = os.path.join(report_dir, REIKAN_DAILY_JSON)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = {}
        for p in data.get("positions") or []:
            ticker = (p.get("ticker") or "").strip()
            price = p.get("current_price")
            if ticker and price is not None:
                out[ticker] = float(price)
        return out
    except Exception:
        return {}


def apply_decision(
    cash: float,
    positions: List[Dict],
    decision: Optional[Dict],
    position_prices: Dict[str, float],
    new_entry_prices: Dict[str, float],
    today_str: str,
) -> Tuple[float, List[Dict]]:
    """
    依當日 AI 決策與當日收盤價執行買賣，回傳 (新現金, 新持倉)。
    無偷看：僅使用當日收盤價。
    """
    if not decision:
        return cash, positions

    pos_by_ticker = {p["ticker"]: p for p in positions}
    new_positions = []

    # 1. 處理既有持倉：出場 / 減碼 / 加碼 / 持有
    dec_positions = {p.get("ticker"): p for p in decision.get("positions") or [] if p.get("ticker")}
    for p in positions:
        ticker = p["ticker"]
        price = position_prices.get(ticker)
        if price is None:
            new_positions.append(p)
            continue
        action = (dec_positions.get(ticker) or {}).get("action") or "持有"
        qty = p["quantity"]
        cost_per_share = p["buy_price"]

        if action == "出場":
            cash += price * qty
            continue
        if action == "減碼":
            sell_qty = max(1, int(qty * BACKTEST_REDUCE_PCT))
            cash += price * sell_qty
            qty -= sell_qty
            if qty <= 0:
                continue
            new_positions.append({
                **p,
                "quantity": qty,
            })
            continue
        if action == "加碼":
            add_cash = cash * BACKTEST_ADD_PCT
            if add_cash >= price:
                add_qty = int(add_cash / price)
                if add_qty >= 1:
                    cash -= add_qty * price
                    new_positions.append({
                        "ticker": ticker,
                        "buy_date": p["buy_date"],
                        "buy_price": (p["buy_price"] * qty + price * add_qty) / (qty + add_qty),
                        "quantity": qty + add_qty,
                        "target_price": p.get("target_price"),
                        "stop_loss": p.get("stop_loss"),
                        "notes": p.get("notes", ""),
                    })
                    continue
        # 持有
        new_positions.append(p)

    # 2. 新買入（new_entries，最多 3 筆，每筆動用 BACKTEST_PCT_PER_NEW_ENTRY 現金）
    new_entries = (decision.get("new_entries") or [])[:3]
    held_tickers = {p["ticker"] for p in new_positions}
    for e in new_entries:
        ticker = (e.get("ticker") or "").strip()
        if not ticker or ticker in held_tickers:
            continue
        price = new_entry_prices.get(ticker)
        if price is None or price <= 0:
            continue
        use_cash = cash * BACKTEST_PCT_PER_NEW_ENTRY
        if use_cash < price:
            continue
        qty = int(use_cash / price)
        if qty < 1:
            continue
        cash -= qty * price
        new_positions.append({
            "ticker": ticker,
            "buy_date": today_str,
            "buy_price": price,
            "quantity": qty,
            "target_price": None,
            "stop_loss": None,
            "notes": "",
        })
        held_tickers.add(ticker)

    return cash, new_positions


def write_positions_csv(path: str, positions: List[Dict]) -> None:
    """將持倉寫入 CSV（與 data/positions.csv 同格式）。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fieldnames = ["ticker", "buy_date", "buy_price", "quantity", "target_price", "stop_loss", "notes"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for p in positions:
            row = {k: ("" if v is None else v) for k, v in p.items() if k in fieldnames}
            w.writerow(row)


def portfolio_value(cash: float, positions: List[Dict], prices: Dict[str, float]) -> float:
    """組合價值 = 現金 + 持倉市值（用給定的 prices）。"""
    total = cash
    for p in positions:
        ticker = p["ticker"]
        total += prices.get(ticker, 0) * p["quantity"]
    return total


STATE_JSON = "state.json"


def load_state(state_dir: str) -> Tuple[float, List[Dict]]:
    """讀取 state_dir 內的 state.json（現金）與 positions.csv（持倉）。若無則回傳初始現金與空持倉。"""
    cash = BACKTEST_INITIAL_CASH
    positions = []
    json_path = os.path.join(state_dir, STATE_JSON)
    if os.path.isfile(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cash = float(data.get("cash", cash))
        except Exception:
            pass
    pos_path = os.path.join(state_dir, "positions.csv")
    if os.path.isfile(pos_path):
        try:
            with open(pos_path, "r", encoding="utf-8-sig") as f:
                r = csv.DictReader(f)
                for row in r:
                    ticker = (row.get("ticker") or "").strip()
                    if not ticker:
                        continue
                    try:
                        qty = int(float(row.get("quantity") or 0))
                        buy_price = float(row.get("buy_price") or 0)
                    except (ValueError, TypeError):
                        continue
                    target_s = (row.get("target_price") or "").strip()
                    stop_s = (row.get("stop_loss") or "").strip()
                    positions.append({
                        "ticker": ticker,
                        "buy_date": (row.get("buy_date") or "").strip(),
                        "buy_price": buy_price,
                        "quantity": qty,
                        "target_price": float(target_s) if target_s else None,
                        "stop_loss": float(stop_s) if stop_s else None,
                        "notes": (row.get("notes") or "").strip(),
                    })
        except Exception:
            pass
    return cash, positions


def save_state(state_dir: str, cash: float, positions: List[Dict], as_of_date: date) -> None:
    """寫入 state.json 與 positions.csv，供下一日使用。"""
    os.makedirs(state_dir, exist_ok=True)
    json_path = os.path.join(state_dir, STATE_JSON)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"cash": cash, "last_date": as_of_date.strftime("%Y-%m-%d")}, f, indent=2)
    pos_path = os.path.join(state_dir, "positions.csv")
    write_positions_csv(pos_path, positions)
