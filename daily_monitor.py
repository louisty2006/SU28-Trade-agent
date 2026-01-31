"""
每日持倉監控與今日決策報告（多數據源版）

- 讀取 data/positions.csv 持倉表
- 取得當前市價（多數據源：Yahoo → Stooq → FMP → ...）
- 以「市場＋持倉」做一次綜合決策（單一 LLM）：今日最好決定
- 產出今日決策報告：文字 + JSON，存於 reports/daily/YYYY-MM-DD/

後續可加：與 Stage 3 建議綁定、資金與時機規則、每日跑 Stage 1→2→3。
"""

import os
import re
import csv
import json
import requests
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

from dotenv import load_dotenv
from config import REIKAN_DAILY_TXT, REIKAN_DAILY_JSON

# 多數據源統一介面（優先交叉驗證）
from utils.data_sources import get_close_on_date, get_close_verified

# 載入 .env（與 stage3 一致，支援主專案目錄）
load_dotenv()
_env_dir = os.path.dirname(os.path.abspath(__file__))
for path in (os.path.join(_env_dir, ".env"), os.path.expanduser("~/stock_scanner/.env"), os.path.join(_env_dir, "..", ".env")):
    if path and os.path.isfile(path):
        load_dotenv(path, override=True)


# 持倉表路徑
POSITIONS_CSV = os.path.join(os.path.dirname(__file__), "data", "positions.csv")
REPORTS_BASE = os.path.join(os.path.dirname(__file__), "reports", "daily")


def load_positions(path: str = POSITIONS_CSV) -> List[Dict]:
    """載入持倉表 CSV，回傳 list of dict。"""
    if not os.path.isfile(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = (row.get("ticker") or "").strip()
            if not ticker:
                continue
            try:
                buy_price = float(row.get("buy_price") or 0)
                quantity = int(float(row.get("quantity") or 0))
            except (ValueError, TypeError):
                continue
            target_s = (row.get("target_price") or "").strip()
            stop_s = (row.get("stop_loss") or "").strip()
            target_price = float(target_s) if target_s else None
            stop_loss = float(stop_s) if stop_s else None
            buy_date_s = (row.get("buy_date") or "").strip()
            try:
                buy_date = datetime.strptime(buy_date_s, "%Y-%m-%d").date() if buy_date_s else date.today()
            except ValueError:
                buy_date = date.today()
            rows.append({
                "ticker": ticker,
                "buy_date": buy_date_s or str(buy_date),
                "buy_price": buy_price,
                "quantity": quantity,
                "target_price": target_price,
                "stop_loss": stop_loss,
                "notes": (row.get("notes") or "").strip(),
            })
    return rows


def get_current_price(ticker: str, as_of_date=None, backtest_start=None) -> Optional[float]:
    """
    使用多數據源取當前價（最近收盤）。
    優先使用 get_close_verified（至少 2 源交叉驗證），無足夠源時退為 get_close_on_date。
    as_of_date 有值時為回測，取該日收盤價。
    backtest_start 有值時限制數據 range（之前看不到）。
    """
    try:
        if as_of_date:
            # 回測模式：取 as_of_date 當日收盤價
            if hasattr(as_of_date, "strftime"):
                target_date = as_of_date
            else:
                target_date = datetime.strptime(str(as_of_date), "%Y-%m-%d").date()
            
            # 優先交叉驗證（2 源，價差 < 0.5%）
            close, verified, _ = get_close_verified(ticker, target_date, min_sources=2, max_variance_pct=0.5)
            if close is not None:
                return close
            # 退為單源
            return get_close_on_date(ticker, target_date)
        else:
            # 即時模式：取今日收盤價
            today = date.today()
            close, _, _ = get_close_verified(ticker, today, min_sources=2, max_variance_pct=0.5)
            if close is not None:
                return close
            close = get_close_on_date(ticker, today)
            if close is not None:
                return close
            # 若今日無資料（可能還沒收盤或休市），取昨日
            yesterday = today - timedelta(days=1)
            return get_close_on_date(ticker, yesterday)
    except Exception:
        return None


def days_held(buy_date_str: str, as_of_date=None) -> Optional[int]:
    """持倉天數（基準日 - 買入日）。as_of_date 為回測時的基準日（date 或 YYYY-MM-DD）。"""
    if not buy_date_str:
        return None
    if not as_of_date:
        ref = date.today()
    elif hasattr(as_of_date, "strftime"):
        ref = as_of_date
    else:
        try:
            ref = datetime.strptime(str(as_of_date), "%Y-%m-%d").date()
        except ValueError:
            ref = date.today()
    try:
        buy = datetime.strptime(buy_date_str, "%Y-%m-%d").date()
        return (ref - buy).days
    except ValueError:
        return None


def suggest_action(
    current_price: float,
    buy_price: float,
    target_price: Optional[float],
    stop_loss: Optional[float],
) -> tuple:
    """
    簡單決策邏輯：回傳 (動作, 理由)。
    動作: 持有 | 加碼 | 減碼 | 出場
    """
    pnl_pct = (current_price - buy_price) / buy_price * 100 if buy_price else 0

    if stop_loss is not None and current_price <= stop_loss:
        return "出場", f"觸及止損 {stop_loss:.2f}"
    if target_price is not None and current_price >= target_price:
        return "減碼", f"達目標價 {target_price:.2f}，可考慮獲利了結"
    if pnl_pct <= -8:
        return "出場", f"虧損 {pnl_pct:.1f}%，評估是否止損"
    if pnl_pct >= 15 and target_price is None:
        return "減碼", f"已漲 {pnl_pct:.1f}%，可考慮部分獲利"
    return "持有", "未觸及止損/目標，繼續持有"


def _extract_json(text: str) -> dict:
    """從 LLM 回應中提取 JSON。"""
    if not text:
        return {}
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    try:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:
        pass
    return {}


def _load_scan_top(csv_path: str) -> List[str]:
    """從 Stage 3 的 stage3_top20.csv 讀取今日掃描 Top 代碼列表。"""
    if not csv_path or not os.path.isfile(csv_path):
        return []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row.get("ticker", "").strip() for row in reader if row.get("ticker", "").strip()]
    except Exception:
        return []


def _write_positions_edit_csv(out_dir: str, positions: List[Dict]) -> None:
    """將當前持倉寫入報告目錄的 positions_edit.csv，供人手改動。"""
    path = os.path.join(out_dir, "positions_edit.csv")
    fieldnames = ["ticker", "buy_date", "buy_price", "quantity", "target_price", "stop_loss", "notes"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in positions:
            w.writerow({
                "ticker": p.get("ticker", ""),
                "buy_date": p.get("buy_date", ""),
                "buy_price": p.get("buy_price", ""),
                "quantity": p.get("quantity", ""),
                "target_price": p.get("target_price") if p.get("target_price") is not None else "",
                "stop_loss": p.get("stop_loss") if p.get("stop_loss") is not None else "",
                "notes": p.get("notes", ""),
            })


def _build_decision_prompt(positions_results: List[Dict], summary: Dict, scan_top: List[str] = None, as_of_date=None) -> str:
    """根據持倉事實（與可選今日掃描）建構「今日最好決定」的 LLM 提示。as_of_date 為回測時的當日。"""
    if as_of_date and hasattr(as_of_date, "strftime"):
        today = as_of_date.strftime("%Y-%m-%d")
    else:
        today = date.today().strftime("%Y-%m-%d")
    has_positions = len(positions_results) > 0
    
    lines = [
        f"你是投資顧問。今日日期：{today}。",
    ]
    
    if has_positions:
        lines.extend([
            "根據以下【持倉與市場狀況】，給出「今日最佳決策」：",
            "1. 對每檔持倉應 持有 / 加碼 / 減碼 / 出場，及簡短理由；",
            "2. 若有餘裕現金可考慮新標的，列出至多 3 檔（否則為空陣列）；",
            "請考慮：止損、目標價、盈虧%、持倉天數。資金有限，出入貨要時機。",
            "",
        ])
    else:
        lines.extend([
            "目前暫無持倉。根據以下【今日掃描 Top】，給出「今日最佳決策」：",
            "1. 若適合建倉，列出至多 3 檔值得買入的標的及理由（按優先順序）；",
            "2. 若市場不適合進場，說明原因並建議觀望；",
            "請考慮：技術面、基本面、市場環境、風險。資金有限，要選擇最佳時機。",
            "",
        ])
    
    if scan_top:
        lines.append("【今日掃描 Top】（可考慮新開倉參考）")
        lines.append("  " + ", ".join(scan_top[:15]))
        lines.append("")
    
    lines.append("【持倉】")
    if has_positions:
        for r in positions_results:
            price_str = f"{r['current_price']:.2f}" if r.get("current_price") is not None else "—"
            pnl_str = f"{r['pnl_pct']:.1f}%" if r.get("pnl_pct") is not None else "—"
            target = f"目標 {r.get('target_price')}" if r.get("target_price") else ""
            stop = f"止損 {r.get('stop_loss')}" if r.get("stop_loss") else ""
            days = f"持倉 {r.get('days_held')} 天" if r.get("days_held") is not None else ""
            lines.append(f"  {r['ticker']}: 買入 {r['buy_price']:.2f} x {r['quantity']}, 現價 {price_str}, 盈虧 {pnl_str}, {target} {stop} {days}".strip())
        lines.extend([
            "",
            f"【合計】總成本 {summary['total_cost']:.2f}, 總市值 {summary['total_value']:.2f}, 盈虧 {summary['total_pnl_pct']:.2f}%",
        ])
    else:
        lines.append("  暫無持倉")
    
    lines.extend([
        "",
        "請用以下 JSON 格式回覆（不要其他文字）：",
    ])
    
    if has_positions:
        lines.append('{ "summary": "一段話總結今日最佳決策", "positions": [ {"ticker": "AAPL", "action": "持有", "reason": "理由"} ], "new_entries": [ {"ticker": "XXX", "priority": 1, "reason": "理由"} ] }')
    else:
        lines.append('{ "summary": "一段話總結今日最佳決策", "positions": [], "new_entries": [ {"ticker": "XXX", "priority": 1, "reason": "理由"} ] }')
    
    return "\n".join(lines)


def _call_decision_llm(prompt: str) -> Optional[Dict]:
    """呼叫 Scitely 做「今日最好決定」綜合決策，回傳解析後的 JSON 或 None。"""
    api_key = os.getenv("SCITELY_API_KEY")
    if not api_key:
        return None
    url = "https://api.scitely.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "qwen3-235b-a22b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500,
    }
    try:
        r = requests.post(url, headers=headers, json=body, timeout=90)
        if r.status_code != 200:
            return None
        text = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        out = _extract_json(text)
        # 空持仓时 positions 可以是空数组，只要有 summary 就算有效
        if not out or "summary" not in out:
            return None
        # 确保 positions 和 new_entries 存在（可以是空数组）
        if "positions" not in out:
            out["positions"] = []
        if "new_entries" not in out:
            out["new_entries"] = []
        return out
    except Exception:
        return None


def run_daily_monitor(
    positions_path: str = POSITIONS_CSV,
    output_dir: str = None,
    stage3_csv_path: str = None,
    as_of_date=None,
    backtest_start=None,
) -> Dict:
    """
    執行每日監控：讀持倉、取市價、算建議、寫報告。
    as_of_date 有值時為回測；backtest_start 限制數據 range（之前看不到）。
    """
    if as_of_date and hasattr(as_of_date, "strftime"):
        today = as_of_date.strftime("%Y-%m-%d")
    else:
        today = date.today().strftime("%Y-%m-%d")
    out = output_dir or os.path.join(REPORTS_BASE, today)
    os.makedirs(out, exist_ok=True)

    positions = load_positions(positions_path)
    scan_top = _load_scan_top(stage3_csv_path) if stage3_csv_path else []
    if scan_top:
        print(f"  📊 今日掃描 Top 已載入（{len(scan_top)} 檔）")

    _write_positions_edit_csv(out, positions)
    print(f"  📝 持倉可編輯檔已寫入：{out}/positions_edit.csv")

    if not positions:
        print("💡 暫無持倉，將根據今日掃描給出新標的建議")

    results = []
    total_cost = 0.0
    total_value = 0.0
    alerts = []

    for p in positions:
        ticker = p["ticker"]
        current = get_current_price(ticker, as_of_date=as_of_date, backtest_start=backtest_start)
        if current is None:
            results.append({
                "ticker": ticker,
                "buy_date": p["buy_date"],
                "buy_price": p["buy_price"],
                "quantity": p["quantity"],
                "current_price": None,
                "pnl_pct": None,
                "days_held": days_held(p["buy_date"], as_of_date=as_of_date),
                "suggestion": "—",
                "reason": "無法取得市價",
                "notes": p.get("notes", ""),
            })
            total_cost += p["buy_price"] * p["quantity"]
            alerts.append(f"{ticker} 無法取得市價")
            continue

        cost = p["buy_price"] * p["quantity"]
        value = current * p["quantity"]
        total_cost += cost
        total_value += value
        pnl_pct = (current - p["buy_price"]) / p["buy_price"] * 100
        action, reason = suggest_action(
            current, p["buy_price"], p.get("target_price"), p.get("stop_loss")
        )
        if action == "出場":
            alerts.append(f"{ticker} 建議賣出：{reason}")
        elif action == "減碼":
            alerts.append(f"{ticker} 建議減碼/獲利了結：{reason}")

        results.append({
            "ticker": ticker,
            "buy_date": p["buy_date"],
            "buy_price": p["buy_price"],
            "quantity": p["quantity"],
            "current_price": round(current, 2),
            "market_value": round(value, 2),
            "pnl_pct": round(pnl_pct, 2),
            "days_held": days_held(p["buy_date"], as_of_date=as_of_date),
            "suggestion": action,
            "reason": reason,
            "notes": p.get("notes", ""),
        })

    total_pnl_pct = (total_value - total_cost) / total_cost * 100 if total_cost else 0
    summary = {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "alerts": alerts,
    }

    decision = None
    prompt = _build_decision_prompt(results, summary, scan_top=scan_top, as_of_date=as_of_date)
    decision = _call_decision_llm(prompt)
    if decision:
        print("  🤖 今日最好決定（LLM 綜合決策）已產出")
    else:
        print("  ⚠️ LLM 綜合決策未產出，報告沿用規則建議")

    report = {
        "date": today,
        "positions": results,
        "summary": summary,
        "decision": decision,
        "scan_top": scan_top,
        "positions_edit_path": "positions_edit.csv",
    }
    _write_report(out, report)
    _print_summary(report, out)
    return report


def _write_report(out_dir: str, report: Dict) -> None:
    """寫入 REIKAN_daily_report.json 與 REIKAN_daily_report.txt。"""
    # JSON
    json_path = os.path.join(out_dir, REIKAN_DAILY_JSON)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 文字
    txt_path = os.path.join(out_dir, REIKAN_DAILY_TXT)
    lines = [
        "# REISHI (霊視) 每日洞察報告",
        "",
        f"**洞察本質，智贏未來** | {report['date']}",
        "",
    ]
    if report.get("message"):
        lines.append(report["message"])
        edit_path = report.get("positions_edit_path") or "positions_edit.csv"
        lines.extend(["", "## 持倉表（人手改動）", "", f"本資料夾內 **{edit_path}** 可人手編輯。編輯後執行：", "  python main.py --daily --positions 本資料夾/" + edit_path, ""])
    else:
        # 今日掃描結果（若有）
        scan_top = report.get("scan_top") or []
        if scan_top:
            lines.extend(["## 今日掃描結果（Stage 1→2→3）", ""])
            lines.append("  " + ", ".join(scan_top))
            lines.append("")
        
        has_positions = len(report["positions"]) > 0
        lines.extend(["## 持倉與建議", ""])
        
        if has_positions:
            for r in report["positions"]:
                price_str = f"{r['current_price']:.2f}" if r.get("current_price") is not None else "—"
                pnl_str = f"{r['pnl_pct']:.1f}%" if r.get("pnl_pct") is not None else "—"
                lines.append(f"- **{r['ticker']}** 買入 {r['buy_date']} @ {r['buy_price']:.2f} x {r['quantity']} → 現價 {price_str} ({pnl_str}) | **{r['suggestion']}**：{r['reason']}")
                if r.get("notes"):
                    lines.append(f"  備註：{r['notes']}")
                lines.append("")
            s = report["summary"]
            lines.extend([
                "## 合計",
                f"- 總成本：{s['total_cost']:.2f}",
                f"- 總市值：{s['total_value']:.2f}",
                f"- 總盈虧：{s['total_pnl_pct']:.2f}%",
                "",
                "## 今日提醒",
            ])
            if s["alerts"]:
                for a in s["alerts"]:
                    lines.append(f"- {a}")
            else:
                lines.append("- 無")
            lines.append("")
        else:
            lines.extend([
                "目前暫無持倉。",
                "",
            ])
        # 今日最好決定（第一性原理：一次綜合決策）
        dec = report.get("decision")
        if dec:
            lines.extend(["## REISHI 今日最好決定（市場＋持倉 綜合決策）", ""])
            lines.append(dec.get("summary", ""))
            lines.append("")
            for p in dec.get("positions", []):
                action = p.get("action", "")
                action_display = "賣出" if action == "出場" else action  # 持倉出場→賣出
                lines.append(f"- **{p.get('ticker', '')}** {action_display}：{p.get('reason', '')}")
            ne = dec.get("new_entries") or []
            if ne:
                lines.append("")
                lines.append("可考慮新開倉（若有餘裕現金）：")
                for e in ne:
                    lines.append(f"- {e.get('ticker', '')}（優先 {e.get('priority', '')}）：{e.get('reason', '')}")
            lines.append("")
        # 持倉表（人手改動）
        edit_path = report.get("positions_edit_path") or "positions_edit.csv"
        lines.extend([
            "## 持倉表（人手改動）",
            "",
            f"本資料夾內 **{edit_path}** 可人手編輯。",
            "編輯後下次執行可指定：",
            f"  python main.py --daily --positions 本資料夾/{edit_path}",
            "或將編輯後的檔案覆蓋 data/positions.csv。",
            "",
        ])
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _print_summary(report: Dict, out_dir: str) -> None:
    """印出摘要到終端。"""
    print("\n" + "=" * 60)
    print(f"📅 REISHI 每日持倉監控 - {report['date']}")
    print("=" * 60)
    if report.get("message"):
        print(f"  {report['message']}")
        print("=" * 60)
        print(f"💾 報告已儲存：{out_dir}")
        print("=" * 60 + "\n")
        return
    
    has_positions = len(report["positions"]) > 0
    
    if has_positions:
        for r in report["positions"]:
            price_str = f"{r['current_price']:.2f}" if r.get("current_price") is not None else "—"
            pnl_str = f"{r['pnl_pct']:+.1f}%" if r.get("pnl_pct") is not None else "—"
            print(f"  {r['ticker']:6} 現價 {price_str:>8} | {pnl_str:>8} | {r['suggestion']}：{r['reason']}")
        s = report["summary"]
        print("-" * 60)
        print(f"  總成本 {s['total_cost']:.2f} → 總市值 {s['total_value']:.2f} | 盈虧 {s['total_pnl_pct']:+.2f}%")
        if s["alerts"]:
            print("  ⚠️ 今日提醒：")
            for a in s["alerts"]:
                print(f"    - {a}")
    else:
        print("  💡 目前暫無持倉")
    
    dec = report.get("decision")
    if dec:
        print("-" * 60)
        if has_positions:
            print("  📌 今日最好決定（市場＋持倉 綜合決策）：")
        else:
            print("  📌 今日最好決定（新標的建議）：")
        print(f"  {dec.get('summary', '')[:200]}")
        for p in dec.get("positions", []):
            print(f"    • {p.get('ticker', '')} {p.get('action', '')}：{p.get('reason', '')[:60]}")
        new_entries = dec.get("new_entries") or []
        if new_entries:
            print("  " + "-" * 56)
            print("  💰 可考慮新標的：")
            for e in new_entries:
                print(f"    • {e.get('ticker', '')} (優先度 {e.get('priority', '?')})：{e.get('reason', '')[:50]}")
    print("=" * 60)
    print(f"💾 報告已儲存：{out_dir}")
    print(f"📄 REISHI 報告：{REIKAN_DAILY_TXT} / {REIKAN_DAILY_JSON}")
    print(f"📝 持倉可編輯：{out_dir}/positions_edit.csv（人手改動後可加 --positions 該路徑再執行）")
    print("=" * 60 + "\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="每日持倉監控與今日決策報告")
    parser.add_argument("--positions", default=POSITIONS_CSV, help="持倉表 CSV 路徑")
    parser.add_argument("--output", default=None, help="報告輸出目錄，預設 reports/daily/YYYY-MM-DD")
    args = parser.parse_args()
    run_daily_monitor(positions_path=args.positions, output_dir=args.output)


if __name__ == "__main__":
    main()
