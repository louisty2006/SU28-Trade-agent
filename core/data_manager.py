"""
REISHI v5.2 - 本地數據管理

- K 線：data/market_data/us_stocks/YYYY.parquet + metadata.json
- 新聞：data/news_data/ + metadata.json（GDELT/SEC/CommonCrawl 等）
- 狀態檢查、修復、下載、驗證、清理

約定（保證行為）：
- 所有下載與續跑都寫入「同一個資料夾」：專案根目錄下的 data/market_data/us_stocks/
- 按年份存檔：每年一個檔案，檔名為 YYYY.parquet（如 2005.parquet、2024.parquet）
- 中斷後再執行 [B] 或該年修復，會從既有 partial 繼續，不會另建資料夾或覆蓋其他年份
- 回測選「本地數據」時，從同一資料夾依年份讀取，使用數據應順利無誤
"""
from __future__ import annotations

import os
import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# 專案根目錄：若當前工作目錄為專案根（有 main_v5.py 與 core/），用 cwd 讓資料寫入執行目錄
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    _cwd = os.getcwd()
    if os.path.isfile(os.path.join(_cwd, "main_v5.py")) and os.path.isdir(os.path.join(_cwd, "core")):
        _PROJECT_ROOT = os.path.abspath(_cwd)
except Exception:
    pass
_DEBUG_LOG_PATH = os.path.join(_PROJECT_ROOT, ".cursor", "debug.log")
_DEBUG_LOG_FALLBACK = os.path.join(_PROJECT_ROOT, "debug_run.log")

def _debug_log(payload):
    """寫入兩處 log（.cursor/debug.log 與專案根 debug_run.log），並列印一行到 stdout 以保留運行證據。"""
    line = json.dumps(payload, ensure_ascii=False)
    for _path in (_DEBUG_LOG_PATH, _DEBUG_LOG_FALLBACK):
        try:
            os.makedirs(os.path.dirname(_path), exist_ok=True)
            with open(_path, "a", encoding="utf-8") as _f:
                _f.write(line + "\n")
                _f.flush()
        except Exception as e:
            # 寫檔失敗時至少列印，方便排查路徑/權限
            try:
                import sys
                sys.stdout.write(f"[REISHI debug_log write failed {_path!r}: {e}\n")
                sys.stdout.flush()
            except Exception:
                pass
    # 僅對關鍵 tag 列印到 stdout，確保續跑排查有運行證據
    _print_tags = ("repair_start", "resume_load_ok", "resume_load_fail", "write_partial_ok", "write_partial_fail")
    if payload.get("tag") in _print_tags:
        try:
            import sys
            # 先換行結束當前的 \r 進度列，否則 write_partial_ok 會被下一次進度覆蓋
            sys.stdout.write("\n")
            sys.stdout.flush()
            tag = payload.get("tag", "log")
            short = line[:200] + "..." if len(line) > 200 else line
            sys.stdout.write(f"[REISHI {tag}] {short}\n")
            sys.stdout.flush()
        except Exception:
            pass

def _resolve_data_roots():
    """依當前工作目錄更新資料路徑，確保與執行目錄一致。"""
    global MARKET_DATA_DIR, MARKET_STOCKS_DIR, MARKET_METADATA_PATH, NEWS_DATA_DIR, NEWS_METADATA_PATH, UNIVERSE_PATH
    root = _PROJECT_ROOT
    try:
        cwd = os.getcwd()
        if os.path.isfile(os.path.join(cwd, "main_v5.py")) and os.path.isdir(os.path.join(cwd, "core")):
            root = os.path.abspath(cwd)
    except Exception:
        pass
    MARKET_DATA_DIR = os.path.join(root, "data", "market_data")
    MARKET_STOCKS_DIR = os.path.join(MARKET_DATA_DIR, "us_stocks")
    MARKET_METADATA_PATH = os.path.join(MARKET_DATA_DIR, "metadata.json")
    NEWS_DATA_DIR = os.path.join(root, "data", "news_data")
    NEWS_METADATA_PATH = os.path.join(NEWS_DATA_DIR, "metadata.json")
    UNIVERSE_PATH = os.path.join(root, "data", "us_universe.csv")


MARKET_DATA_DIR = os.path.join(_PROJECT_ROOT, "data", "market_data")
MARKET_STOCKS_DIR = os.path.join(MARKET_DATA_DIR, "us_stocks")
MARKET_METADATA_PATH = os.path.join(MARKET_DATA_DIR, "metadata.json")
NEWS_DATA_DIR = os.path.join(_PROJECT_ROOT, "data", "news_data")
NEWS_METADATA_PATH = os.path.join(NEWS_DATA_DIR, "metadata.json")
UNIVERSE_PATH = os.path.join(_PROJECT_ROOT, "data", "us_universe.csv")


@dataclass
class YearStatus:
    """單年 K 線狀態"""
    year: str
    status: str  # "complete" | "partial" | "none"
    stocks_count: int
    completeness_pct: float
    size_mb: float
    date_range: Optional[Tuple[str, str]] = None
    expected_stocks: int = 7055


def _ensure_dirs():
    os.makedirs(MARKET_DATA_DIR, exist_ok=True)
    os.makedirs(MARKET_STOCKS_DIR, exist_ok=True)
    os.makedirs(NEWS_DATA_DIR, exist_ok=True)


def _load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: str, data: dict):
    _ensure_dirs()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_universe_count() -> int:
    """取得 us_universe 股票數量"""
    if not os.path.isfile(UNIVERSE_PATH):
        return 7055
    try:
        with open(UNIVERSE_PATH, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f) - 1  # 減標題
    except Exception:
        return 7055


def get_market_metadata() -> dict:
    """讀取 K 線 metadata.json"""
    meta = _load_json(MARKET_METADATA_PATH)
    if not meta:
        meta = {"last_updated": None, "years": {}}
    return meta


def save_market_metadata(meta: dict):
    meta["last_updated"] = datetime.now().isoformat()
    _save_json(MARKET_METADATA_PATH, meta)


def get_kline_status() -> List[YearStatus]:
    """
    掃描 data/market_data/us_stocks/*.parquet 與 metadata，回傳每年狀態。
    狀態：complete（完整）、partial（部分）、none（無）。
    會先 _resolve_data_roots() 以確保讀取路徑與下載一致，令「上次已下載」立刻反映在表上。
    """
    _resolve_data_roots()
    expected = get_universe_count()
    meta = get_market_metadata()
    years_meta = meta.get("years", {})
    result: List[YearStatus] = []
    for y in range(2005, 2026):
        year_str = str(y)
        parquet_path = os.path.join(MARKET_STOCKS_DIR, f"{year_str}.parquet")
        info = years_meta.get(year_str, {})
        status_str = info.get("status", "none")
        stocks_count = info.get("stocks_count", 0)
        date_range = info.get("date_range")
        file_size_mb = info.get("file_size_mb", 0.0)
        if os.path.isfile(parquet_path):
            try:
                sz = os.path.getsize(parquet_path)
                file_size_mb = round(sz / (1024 * 1024), 1)
            except Exception:
                pass
            if status_str == "none":
                status_str = "partial"  # 有檔案但 metadata 未標
            if stocks_count <= 0:
                try:
                    import pandas as pd
                    df = pd.read_parquet(parquet_path)
                    if "symbol" in df.columns:
                        stocks_count = df["symbol"].nunique()
                    elif "ticker" in df.columns:
                        stocks_count = df["ticker"].nunique()
                    else:
                        stocks_count = len(df)  # 粗略
                except Exception:
                    stocks_count = 0
            completeness = (stocks_count / expected * 100) if expected else 0
            if completeness >= 99:
                status_str = "complete"
            elif completeness > 0:
                status_str = "partial"
            ys = YearStatus(
                year=year_str,
                status=status_str,
                stocks_count=stocks_count,
                completeness_pct=round(completeness, 1),
                size_mb=file_size_mb,
                date_range=tuple(date_range) if isinstance(date_range, list) and len(date_range) >= 2 else None,
                expected_stocks=expected,
            )
            result.append(ys)
            # #region agent log
            if year_str == "2005":
                try:
                    payload = {"location": "data_manager:get_kline_status", "message": "result_2005", "stocks_count": stocks_count, "completeness_pct": round(completeness, 1), "from_meta": info.get("stocks_count"), "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H_status"}
                    with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _f:
                        _f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                except Exception:
                    pass
            # #endregion
        else:
            result.append(YearStatus(
                year=year_str,
                status="none",
                stocks_count=0,
                completeness_pct=0,
                size_mb=0,
                date_range=None,
                expected_stocks=expected,
            ))
    return result


def get_news_status() -> List[Dict[str, Any]]:
    """
    讀取新聞 metadata，回傳各區間狀態（可依 GDELT/SEC/CommonCrawl 等）。
    目前為佔位結構，實際來源需對接 GDELT/SEC 等。
    """
    meta = _load_json(NEWS_METADATA_PATH)
    rows = meta.get("ranges", [])
    if not rows:
        # 佔位
        return [
            {"range": "2015-2025", "status": "none", "source": "GDELT+SEC", "count": 0, "size_gb": 0},
            {"range": "2010-2014", "status": "none", "source": "CommonCrawl", "count": 0, "size_gb": 0},
            {"range": "2005-2009", "status": "none", "source": "SEC only", "count": 0, "size_gb": 0},
        ]
    return rows


def format_kline_table(rows: List[YearStatus]) -> str:
    """輸出 K 線狀態表格字串"""
    lines = []
    lines.append("【K 線數據】")
    lines.append(f"{'年份':<6} {'狀態':<12} {'股票數':>8} {'完整度':>8} {'大小':>10}")
    for r in rows:
        status_display = {"complete": "✓ 完整", "partial": "⚠ 部分", "none": "✗ 無"}.get(r.status, r.status)
        size_str = f"{r.size_mb/1024:.1f} GB" if r.size_mb >= 1024 else f"{r.size_mb:.1f} MB"
        lines.append(f"{r.year:<6} {status_display:<12} {r.stocks_count:>8,} {r.completeness_pct:>6.0f}%   {size_str:>10}")
    return "\n".join(lines)


def _get_one_year_status_from_disk(year: str) -> Optional[YearStatus]:
    """從磁碟直接讀取該年 parquet 的狀態（不依賴 metadata），確保即時反映剛寫入的 partial。"""
    _resolve_data_roots()
    parquet_path = os.path.join(MARKET_STOCKS_DIR, f"{year}.parquet")
    if not os.path.isfile(parquet_path):
        return None
    expected = get_universe_count()
    try:
        sz = os.path.getsize(parquet_path)
        file_size_mb = round(sz / (1024 * 1024), 1)
    except Exception:
        file_size_mb = 0.0
    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
        if "symbol" in df.columns:
            stocks_count = int(df["symbol"].nunique())
        elif "ticker" in df.columns:
            stocks_count = int(df["ticker"].nunique())
        else:
            stocks_count = len(df)
    except Exception:
        return None
    completeness = (stocks_count / expected * 100) if expected else 0
    status_str = "complete" if completeness >= 99 else ("partial" if completeness > 0 else "none")
    return YearStatus(
        year=year,
        status=status_str,
        stocks_count=stocks_count,
        completeness_pct=round(completeness, 1),
        size_mb=file_size_mb,
        date_range=None,
        expected_stocks=expected,
    )


def _print_kline_status_one_line(year: str):
    """下載中：從磁碟直接讀取該年 parquet 並印出該年一行，即時反映剛寫入的 partial（不依賴 metadata）。"""
    s = _get_one_year_status_from_disk(year)
    if s is None:
        return
    status_display = {"complete": "✓ 完整", "partial": "⚠ 部分", "none": "✗ 無"}.get(s.status, s.status)
    size_str = f"{s.size_mb/1024:.1f} GB" if s.size_mb >= 1024 else f"{s.size_mb:.1f} MB"
    line = f"  【即時】{s.year} {status_display} {s.stocks_count:,} 檔 {s.completeness_pct:.0f}% {size_str}"
    try:
        import sys
        sys.stdout.write("\n" + line + "\n")
        sys.stdout.flush()
    except Exception:
        pass


def _print_kline_status_refresh(during_download: bool = False):
    """重新讀取 K 線狀態並列印表格，令用家立刻看到最新狀態（下載後或上次已下載）。during_download 時加標題方便辨識即時更新。"""
    status = get_kline_status()
    # #region agent log
    if during_download and status:
        try:
            s2005 = next((s for s in status if s.year == "2005"), None)
            payload = {"location": "data_manager:_print_kline_status_refresh", "message": "refresh_during_download", "year_2005": {"stocks_count": getattr(s2005, "stocks_count", None), "completeness_pct": getattr(s2005, "completeness_pct", None), "status": getattr(s2005, "status", None)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H_refresh"}
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _f:
                _f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            pass
    # #endregion
    print()
    if during_download:
        print("  【當前 K 線狀態】")
    print(format_kline_table(status))
    print()
    try:
        import sys
        sys.stdout.flush()
    except Exception:
        pass


def format_news_table(rows: List[Dict[str, Any]]) -> str:
    """輸出新聞狀態表格字串"""
    lines = []
    lines.append("【歷史新聞】")
    lines.append(f"{'年份':<14} {'狀態':<10} {'來源':<16} {'筆數':>10} {'大小':>10}")
    for r in rows:
        status_display = {"complete": "✓ 完整", "partial": "⚠ 部分", "none": "△ 有限"}.get(r.get("status", "none"), str(r.get("status", "")))
        cnt = r.get("count", 0)
        cnt_str = f"{cnt/1e6:.1f}M" if cnt >= 1e6 else f"{cnt/1e3:.0f}K" if cnt >= 1000 else str(cnt)
        sz = r.get("size_gb", 0) or (r.get("size_mb", 0) / 1024)
        size_str = f"{sz:.2f} GB" if sz >= 1 else f"{sz*1024:.0f} MB"
        lines.append(f"{r.get('range', ''):<14} {status_display:<10} {r.get('source', ''):<16} {cnt_str:>10} {size_str:>10}")
    return "\n".join(lines)


def check_data_sufficient(start_date: date, end_date: date) -> Tuple[bool, str, List[YearStatus]]:
    """
    檢查 [start_date, end_date] 區間內本地 K 線數據是否足夠。
    讀取路徑與下載一致：data/market_data/us_stocks/。回傳 (是否足夠, 訊息, 相關年份狀態列表)。
    """
    _resolve_data_roots()
    # #region agent log
    _debug_log({"location": "data_manager.py:check_data_sufficient", "message": "entry", "data": {"start": str(start_date), "end": str(end_date)}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H2"})
    # #endregion
    statuses = get_kline_status()
    y_start = start_date.year
    y_end = end_date.year
    years_needed = {str(y) for y in range(y_start, y_end + 1)}
    relevant = [s for s in statuses if s.year in years_needed]
    complete = all(s.status == "complete" for s in relevant)
    partial = any(s.status == "partial" for s in relevant)
    none = any(s.status == "none" for s in relevant)
    if complete and relevant:
        out = (True, "數據完整，可開始本地回測", relevant)
    elif none:
        missing = [s.year for s in relevant if s.status == "none"]
        out = (False, f"缺少年份：{', '.join(missing)}，請先下載或修復", relevant)
    elif partial:
        out = (False, "部分年份數據不完整，建議修復後再回測", relevant)
    else:
        out = (False, "尚無該區間數據", relevant)
    # #region agent log
    _debug_log({"location": "data_manager.py:check_data_sufficient", "message": "exit", "data": {"sufficient": out[0], "msg": out[1], "relevant_count": len(out[2])}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H2"})
    # #endregion
    return out


def diagnose_year(year: str) -> Dict[str, Any]:
    """診斷某年：缺少多少股票、哪些日期（佔位，可擴充）"""
    parquet_path = os.path.join(MARKET_STOCKS_DIR, f"{year}.parquet")
    if not os.path.isfile(parquet_path):
        return {"year": year, "has_file": False, "missing_stocks": None, "missing_dates": None, "message": "無該年 parquet"}
    try:
        import pandas as pd
        df = pd.read_parquet(parquet_path)
        expected = get_universe_count()
        if "symbol" in df.columns:
            have = set(df["symbol"].unique())
        elif "ticker" in df.columns:
            have = set(df["ticker"].unique())
        else:
            have = set()
        # 從 universe 讀取應有列表
        tickers_all = []
        if os.path.isfile(UNIVERSE_PATH):
            import csv
            with open(UNIVERSE_PATH, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    s = (row.get("symbol") or row.get("Symbol") or "").strip()
                    if s:
                        tickers_all.append(s)
        missing = set(tickers_all) - have if tickers_all else None
        return {
            "year": year,
            "has_file": True,
            "stocks_in_file": len(have),
            "expected_stocks": expected,
            "missing_stocks": len(missing) if missing is not None else None,
            "missing_dates": None,  # 可擴充：比對交易日
            "message": f"已有 {len(have)} 檔，缺 {len(missing) if missing else 0} 檔" if missing is not None else "已掃描",
        }
    except Exception as e:
        return {"year": year, "has_file": True, "message": str(e)}


def repair_or_download_year(year: str, on_progress: Optional[callable] = None) -> bool:
    """
    修復或下載指定年份 K 線數據。支援續跑與並行：
    - 年度續跑：若該年 parquet 已存在且完整（≥99% 標的）則跳過，不重下。
    - 單年內續跑：若該年 parquet 已存在但未完整，只下載「尚未有的標的」並合併；每 50 檔寫入一次 partial。
    - 並行下載：預設 8 緒同時下載，加快速度；失敗的標的會自動順序補下載一次（間隔 1s），仍失敗的留待下次續跑再試。
    中斷後（如 Ctrl+C）：直接再次執行同一年或 [B]，會從上次 partial 繼續。
    """
    _resolve_data_roots()
    _ensure_dirs()
    parquet_engine, parquet_err = _get_parquet_engine()
    if parquet_engine is None:
        if callable(on_progress):
            _invoke_progress(on_progress, "", False)
        print(f"\n❌ {parquet_err}\n")
        return False
    # 運行證據：路徑與是否存在 partial，用於排查續跑不生效
    _out_path = os.path.join(MARKET_STOCKS_DIR, f"{year}.parquet")
    _debug_log({
        "tag": "repair_start",
        "year": year,
        "project_root": _PROJECT_ROOT,
        "cwd": os.getcwd(),
        "market_stocks_dir": MARKET_STOCKS_DIR,
        "out_path": _out_path,
        "out_path_exists": os.path.isfile(_out_path),
        "out_path_abs": os.path.abspath(_out_path),
    })
    import pandas as pd
    from datetime import date as date_type
    start_d = date_type(int(year), 1, 1)
    end_d = date_type(int(year), 12, 31)
    tickers = []
    if os.path.isfile(UNIVERSE_PATH):
        import csv
        with open(UNIVERSE_PATH, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                s = (row.get("symbol") or row.get("Symbol") or "").strip()
                if s:
                    tickers.append(s)
    if not tickers:
        if callable(on_progress):
            _invoke_progress(on_progress, "us_universe.csv 無標的，跳過下載", False)
        return False
    total = len(tickers)
    out_path = os.path.join(MARKET_STOCKS_DIR, f"{year}.parquet")
    existing_df = None
    have = set()
    if os.path.isfile(out_path):
        try:
            existing_df = pd.read_parquet(out_path, engine=parquet_engine)
            # 支援 symbol 或 ticker 欄位，方便與既有 parquet 相容
            if "symbol" not in existing_df.columns and "ticker" in existing_df.columns:
                existing_df = existing_df.copy()
                existing_df["symbol"] = existing_df["ticker"]
            if "symbol" in existing_df.columns:
                have = set(existing_df["symbol"].unique())
                _debug_log({"tag": "resume_load_ok", "year": year, "path": os.path.abspath(out_path), "have_count": len(have), "total": total})
                # 年度續跑：已完整則跳過
                if len(have) >= total * 0.99:
                    if callable(on_progress):
                        _invoke_progress(on_progress, f"{year} 已完整（{len(have)} 檔），跳過", False)
                    return True
        except Exception as e:
            _debug_log({"tag": "resume_load_fail", "year": year, "path": os.path.abspath(out_path), "error": str(e)})
            existing_df = None
            have = set()
    tickers_to_fetch = [t for t in tickers if t not in have]
    have_count = len(have)
    if not tickers_to_fetch:
        if callable(on_progress):
            _invoke_progress(on_progress, f"{year} 已完整，跳過", False)
        return True
    try:
        from utils.data_sources import get_daily_bars
    except ImportError:
        if callable(on_progress):
            _invoke_progress(on_progress, "無法載入 data_sources，請安裝依賴", False)
        return False
    import logging
    _yf_log = logging.getLogger("yfinance")
    _yf_prev_level = _yf_log.level
    _yf_log.setLevel(logging.ERROR)
    _yf_log.disabled = True
    _bar_width = 20
    _max_line = PROGRESS_LINE_WIDTH - 18
    _checkpoint_every = 50
    _max_workers = 8
    _retry_delay_sec = 1.0
    if callable(on_progress):
        if have_count:
            _invoke_progress(on_progress, f"續跑 {year}：已有 {have_count} 檔，待補 {len(tickers_to_fetch)} 檔（並行 {_max_workers}，可隨時 Ctrl+C，下次續跑）", False)
        else:
            _invoke_progress(on_progress, f"開始 {year}（共 {total} 檔，並行 {_max_workers}；可隨時 Ctrl+C，下次續跑）", False)
    rows = []
    failed_tickers = []
    _wait_timeout_sec = 90  # 若 90 秒內無任一筆完成，列印「仍在取得數據」避免看起來卡住
    _fetch_timeout_sec = 60  # 單一股票最多等 60 秒，避免卡死 worker
    try:
        from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED, TimeoutError as FuturesTimeoutError

        def _fetch_one(ticker: str):
            try:
                with ThreadPoolExecutor(max_workers=1) as sub_exec:
                    fut = sub_exec.submit(
                        get_daily_bars, ticker, start_d, end_d, min_bars=1, merge_sources=True
                    )
                    df = fut.result(timeout=_fetch_timeout_sec)
                if df is not None and not df.empty:
                    df = df.copy()
                    df["symbol"] = ticker
                    return (ticker, df)
            except (FuturesTimeoutError, Exception):
                pass
            return (ticker, None)

        with ThreadPoolExecutor(max_workers=_max_workers) as executor:
            future_to_ticker = {executor.submit(_fetch_one, t): t for t in tickers_to_fetch}
            pending = set(future_to_ticker.keys())
            try:
                while pending:
                    done, pending = wait(pending, timeout=_wait_timeout_sec, return_when=FIRST_COMPLETED)
                    if not done:
                        if callable(on_progress):
                            _invoke_progress(on_progress, f"  仍在取得數據…（剩 {len(pending)} 檔，可 Ctrl+C 中斷）", False)
                        continue
                    for f in done:
                        ticker = future_to_ticker[f]
                        try:
                            _, df = f.result()
                        except Exception:
                            df = None
                        if df is not None:
                            rows.append(df)
                            downloaded_so_far = have_count + len(rows)
                            remaining = total - downloaded_so_far
                            pct = downloaded_so_far / total if total else 0
                            filled = min(_bar_width, int(_bar_width * pct))
                            bar = "[" + "#" * filled + "-" * (_bar_width - filled) + "]"
                            pct_str = f"{pct*100:.1f}%" if pct < 0.01 else f"{pct*100:.0f}%"
                            line = f"{bar} {pct_str} 已下載 {downloaded_so_far} 餘 {remaining} 當前:{ticker}"
                            if len(line) > _max_line:
                                line = line[:_max_line - 3] + "..."
                            if callable(on_progress):
                                _invoke_progress(on_progress, line, True)
                            if len(rows) <= 50 or len(rows) % _checkpoint_every == 0:
                                _write_partial(year, existing_df, rows, out_path, start_d, end_d, on_progress, parquet_engine)
                                # 寫入後即時印出該年一行狀態，數字隨 partial 更新
                                _print_kline_status_one_line(year)
                        else:
                            failed_tickers.append(ticker)
            except KeyboardInterrupt:
                if rows or (existing_df is not None and not existing_df.empty):
                    if callable(on_progress):
                        _invoke_progress(on_progress, "  中斷前寫入進度…", False)
                    _write_partial(year, existing_df, rows, out_path, start_d, end_d, on_progress, parquet_engine)
                raise
        # 補下載：失敗的改為順序重試一次，間隔 _retry_delay_sec，避免第三方限流後立刻再打
        rows_before_retry = len(rows)
        if failed_tickers and callable(on_progress):
            _invoke_progress(on_progress, f"  補下載 {len(failed_tickers)} 檔（順序重試，間隔 {_retry_delay_sec}s）…", False)
        import time
        for t in failed_tickers:
            try:
                time.sleep(_retry_delay_sec)
                df = get_daily_bars(t, start_d, end_d, min_bars=1, merge_sources=True)
                if df is not None and not df.empty:
                    df = df.copy()
                    df["symbol"] = t
                    rows.append(df)
                    if callable(on_progress):
                        _invoke_progress(on_progress, f"  補下載成功: {t}", False)
                    if len(rows) % _checkpoint_every == 0:
                        _write_partial(year, existing_df, rows, out_path, start_d, end_d, on_progress, parquet_engine)
                        _print_kline_status_one_line(year)
            except Exception:
                pass
        still_failed = len(failed_tickers) - (len(rows) - rows_before_retry)
        if still_failed > 0 and callable(on_progress):
            _invoke_progress(on_progress, f"  本輪未成功 {still_failed} 檔，下次執行續跑會自動再試", False)
    finally:
        _yf_log.disabled = False
        _yf_log.setLevel(_yf_prev_level)
    if callable(on_progress):
        _invoke_progress(on_progress, "", False)
    if not rows and existing_df is None:
        if callable(on_progress):
            _invoke_progress(on_progress, f"{year} 無可寫入數據", False)
        return False
    combined = _concat_existing_and_rows(existing_df, rows)
    if combined is None or combined.empty:
        return True
    combined.to_parquet(out_path, index=False, engine=parquet_engine)
    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    uniq_col = "symbol" if "symbol" in combined.columns else "ticker"
    stocks_in_file = int(combined[uniq_col].nunique())
    meta = get_market_metadata()
    if "years" not in meta:
        meta["years"] = {}
    meta["years"][year] = {
        "status": "complete" if stocks_in_file >= get_universe_count() * 0.99 else "partial",
        "stocks_count": stocks_in_file,
        "date_range": [start_d.isoformat(), end_d.isoformat()],
        "file_size_mb": round(size_mb, 1),
    }
    save_market_metadata(meta)
    if callable(on_progress):
        _invoke_progress(on_progress, f"{year} 完成：{stocks_in_file} 檔，{len(combined)} 筆，{size_mb:.1f} MB", False)
    return True


# 歷史 K 線寫入的標準欄位與順序，確保齊備清晰
_KLINE_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "symbol"]


def _normalize_kline_columns(df):
    """將 DataFrame 統一為標準欄位名稱與順序：Date, Open, High, Low, Close, Volume, symbol。"""
    if df is None or df.empty:
        return df
    out = df.copy()
    renames = {}
    if "date" in out.columns and "Date" not in out.columns:
        renames["date"] = "Date"
    for name in ["open", "high", "low", "close", "volume"]:
        cap = name.capitalize()
        if name in out.columns and cap not in out.columns:
            renames[name] = cap
    if renames:
        out = out.rename(columns=renames)
    if "ticker" in out.columns and "symbol" not in out.columns:
        out["symbol"] = out["ticker"]
    existing = [c for c in _KLINE_COLUMNS if c in out.columns]
    if len(existing) >= 6:
        return out[existing]
    return out


def _sort_kline_df(df):
    """依 symbol、Date 排序，方便檢視與後續分析。"""
    if df is None or df.empty or "symbol" not in df.columns:
        return df
    date_col = "Date" if "Date" in df.columns else ("date" if "date" in df.columns else None)
    if not date_col:
        return df
    return df.sort_values(by=["symbol", date_col], ignore_index=True)


def _concat_existing_and_rows(existing_df, rows):
    if not rows and (existing_df is None or existing_df.empty):
        return None
    import pandas as pd
    if not rows:
        return _sort_kline_df(_normalize_kline_columns(existing_df))
    new_df = pd.concat(rows, ignore_index=True)
    if existing_df is None or existing_df.empty:
        out = new_df
    else:
        out = pd.concat([existing_df, new_df], ignore_index=True)
    date_col = "Date" if "Date" in out.columns else ("date" if "date" in out.columns else None)
    if date_col and "symbol" in out.columns:
        out = out.drop_duplicates(subset=[date_col, "symbol"], keep="last")
    out = _normalize_kline_columns(out)
    return _sort_kline_df(out)


def _write_partial(year: str, existing_df, rows, out_path, start_d, end_d, on_progress, engine: str = "pyarrow"):
    """每 50 檔寫入一次 partial parquet，中斷後下次可續跑；另在滿 1、10 檔時也會寫入。engine 由 repair_or_download_year 傳入。"""
    _ensure_dirs()
    out_path = os.path.abspath(out_path)
    combined = _concat_existing_and_rows(existing_df, rows)
    if combined is None or combined.empty:
        _debug_log({"tag": "write_partial_skip", "year": year, "reason": "combined empty", "rows_len": len(rows) if rows else 0})
        return
    tmp_path = out_path + ".tmp"
    n_stocks = int(combined["symbol"].nunique()) if "symbol" in combined.columns else 0
    try:
        combined.to_parquet(tmp_path, index=False, engine=engine)
        if os.path.isfile(tmp_path):
            os.replace(tmp_path, out_path)
        _debug_log({"tag": "write_partial_ok", "year": year, "path": out_path, "n_stocks": n_stocks, "size_bytes": os.path.getsize(out_path)})
    except Exception as e:
        global _pyarrow_hint_printed
        _debug_log({"tag": "write_partial_fail", "year": year, "path": out_path, "n_stocks": n_stocks, "error": str(e)})
        if not _pyarrow_hint_printed and ("Unable to find a usable engine" in str(e) or "pyarrow" in str(e).lower()):
            _pyarrow_hint_printed = True
            try:
                import sys
                sys.stdout.write("\n  ⚠ 寫入 Parquet 需要 pyarrow，請執行: pip install pyarrow\n")
                sys.stdout.flush()
            except Exception:
                pass
        try:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return
    # 若當前工作目錄為專案根且與 out_path 不同，再寫一份到 cwd，確保終端所在目錄也有檔案
    try:
        import shutil
        cwd = os.getcwd()
        if os.path.isfile(os.path.join(cwd, "main_v5.py")) and os.path.isdir(os.path.join(cwd, "core")):
            mirror_dir = os.path.join(cwd, "data", "market_data", "us_stocks")
            if os.path.abspath(os.path.dirname(out_path)) != os.path.abspath(mirror_dir):
                os.makedirs(mirror_dir, exist_ok=True)
                mirror_path = os.path.join(mirror_dir, f"{year}.parquet")
                shutil.copy2(out_path, mirror_path)
    except Exception:
        pass
    uniq_col = "symbol" if "symbol" in combined.columns else "ticker"
    n_stocks = int(combined[uniq_col].nunique())
    meta = get_market_metadata()
    if "years" not in meta:
        meta["years"] = {}
    meta["years"][year] = {
        "status": "partial",
        "stocks_count": n_stocks,
        "date_range": [start_d.isoformat(), end_d.isoformat()],
        "file_size_mb": round(os.path.getsize(out_path) / (1024 * 1024), 1),
    }
    save_market_metadata(meta)
    if callable(on_progress):
        _invoke_progress(on_progress, f"  → 已寫入 partial（{n_stocks} 檔） {out_path}", False)


# 進度列單行最大寬度，避免 \r 覆蓋時換行殘影
PROGRESS_LINE_WIDTH = 100

# 僅列印一次 pyarrow 安裝提示，避免洗版
_pyarrow_hint_printed = False


def _get_parquet_engine() -> Tuple[Optional[str], Optional[str]]:
    """回傳 (engine_name, None) 或 (None, error_message)。優先 pyarrow，其次 fastparquet。"""
    try:
        import pyarrow  # noqa: F401
        return ("pyarrow", None)
    except ImportError:
        pass
    try:
        import fastparquet  # noqa: F401
        return ("fastparquet", None)
    except ImportError:
        pass
    return (None, "請先安裝 Parquet 引擎：pip install pyarrow  或  pip install fastparquet")


def _invoke_progress(on_progress, msg: str, same_line: bool):
    """呼叫 on_progress(msg, same_line)。若 callback 只接受一參數則僅傳 msg（相容舊用法）。"""
    try:
        on_progress(msg, same_line)
    except TypeError:
        if same_line:
            import sys
            msg_trim = msg[:PROGRESS_LINE_WIDTH - 2] if len(msg) > PROGRESS_LINE_WIDTH - 2 else msg
            pad = " " * max(0, PROGRESS_LINE_WIDTH - 2 - len(msg_trim))
            sys.stdout.write(f"\r  {msg_trim}{pad}")
            sys.stdout.flush()
        else:
            if msg:
                on_progress(msg)
            else:
                import sys
                sys.stdout.write("\n")
                sys.stdout.flush()


def validate_integrity() -> List[str]:
    """驗證現有 parquet 完整性（可檢查損壞、缺列等），回傳問題列表"""
    issues = []
    for fname in os.listdir(MARKET_STOCKS_DIR or ""):
        if not fname.endswith(".parquet"):
            continue
        path = os.path.join(MARKET_STOCKS_DIR, fname)
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            if df.empty:
                issues.append(f"{fname}: 檔案為空")
            required = ["Date", "Open", "High", "Low", "Close", "Volume"] if "Date" in df.columns else ["symbol", "date", "open", "high", "low", "close", "volume"]
            for c in required:
                if c not in df.columns and c not in [x.lower() for x in df.columns]:
                    issues.append(f"{fname}: 缺少欄位 {c}")
        except Exception as e:
            issues.append(f"{fname}: 讀取失敗 - {e}")
    return issues


def cleanup_corrupted() -> List[str]:
    """清理損壞的 parquet（無法讀取或為空），回傳已刪除檔案列表"""
    removed = []
    for fname in os.listdir(MARKET_STOCKS_DIR or ""):
        if not fname.endswith(".parquet"):
            continue
        path = os.path.join(MARKET_STOCKS_DIR, fname)
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            if df.empty:
                os.remove(path)
                removed.append(path)
        except Exception:
            try:
                os.remove(path)
                removed.append(path)
            except Exception:
                pass
    if removed:
        meta = get_market_metadata()
        for p in removed:
            y = os.path.basename(p).replace(".parquet", "")
            if "years" in meta and y in meta["years"]:
                del meta["years"][y]
        save_market_metadata(meta)
    return removed


def run_data_management_ui():
    """數據管理選單：狀態表 + [F][1-9][A][B][C][D][E][0]"""
    _resolve_data_roots()
    _ensure_dirs()
    while True:
        kline_status = get_kline_status()
        news_status = get_news_status()
        print("\n" + "=" * 60)
        print("📁 REISHI v5.2 數據管理")
        print("=" * 60)
        print(format_kline_table(kline_status))
        print()
        # 每年後方 [1] 修復 / [2] 下載 僅在列印時用簡化顯示，操作用下方選項
        print(format_news_table(news_status))
        print()
        print("操作選項：")
        print("  [F] 修復所有不完整年份")
        print("  [1]-[9] 修復/下載 2005-2013（1=2005, 2=2006…9=2013）；或輸入兩位數如 24=2024")
        print("  [A] 補下載特定年份（自訂範圍）")
        print("  [B] 下載完整 20 年數據（2005-2025）")
        print("  [C] 更新至最新")
        print("  [D] 驗證數據完整性")
        print("  [E] 清理損壞數據")
        print("  [0] 返回主選單")
        choice = input("\n請輸入選項: ").strip().upper()
        if choice == "0":
            return
        if choice == "F":
            to_repair = [s.year for s in kline_status if s.status == "partial"]
            if not to_repair:
                print("無不完整年份需修復")
                continue
            print(f"將修復：{', '.join(to_repair)}")
            if input("確認？[y/N]: ").strip().lower() != "y":
                continue
            for y in to_repair:
                print(f"  修復 {y}...")
                repair_or_download_year(y, on_progress=lambda msg: print(f"    {msg}"))
            _print_kline_status_refresh()
            continue
        if choice in "123456789" or (len(choice) == 2 and choice.isdigit()):
            # 單鍵 1-9 => 2005-2013；兩位數 14,24 => 2014, 2024
            if len(choice) == 1:
                year_full = str(2004 + int(choice))  # 1=2005, 2=2006, ..., 9=2013
            else:
                year_full = "20" + choice  # 24→2024
            y = int(year_full)
            if y < 2005 or y > 2025:
                print("年份請在 2005-2025 之間")
                continue
            print(f"下載/修復年份 {year_full}")
            repair_or_download_year(year_full, on_progress=lambda msg: print(f"  {msg}"))
            _print_kline_status_refresh()
            continue
        if choice == "A":
            r = input("輸入年份範圍（例 2020 2023）: ").strip().split()
            if len(r) >= 2:
                try:
                    y1, y2 = int(r[0]), int(r[1])
                    for y in range(y1, y2 + 1):
                        repair_or_download_year(str(y), on_progress=lambda m: print(f"  {m}"))
                except ValueError:
                    print("請輸入兩個整數年份")
            _print_kline_status_refresh()
            continue
        if choice == "B":
            print("下載 2005-2025 共 21 年，耗時較長")
            if input("確認？[y/N]: ").strip().lower() != "y":
                continue
            years_list = list(range(2005, 2026))
            n_years = len(years_list)
            for idx, y in enumerate(years_list, 1):
                def _progress(msg, same_line=False, _yr=y, _i=idx, _n=n_years):
                    prefix = f"  [{_i}/{_n}] {_yr} "
                    if same_line:
                        full = prefix + msg
                        if len(full) > PROGRESS_LINE_WIDTH:
                            full = full[: PROGRESS_LINE_WIDTH - 1] + "…"
                        pad = " " * max(0, PROGRESS_LINE_WIDTH - len(full))
                        print(f"\r{full}{pad}", end="", flush=True)
                    else:
                        if msg:
                            print(f"{prefix}{msg}", flush=True)
                        else:
                            print(flush=True)
                print(f"  [{idx}/{n_years}] 開始年份 {y} …", flush=True)
                repair_or_download_year(str(y), on_progress=_progress)
                # 該年完成後立刻更新狀態表，令用家隨時看到最新年份/狀態/股票數/完整度
                _print_kline_status_refresh()
            print("  全部 21 年下載完成。", flush=True)
            _print_kline_status_refresh()
            continue
        if choice == "C":
            from datetime import date as dt_date
            y = str(dt_date.today().year)
            print(f"更新至最新（{y} 年）...")
            repair_or_download_year(y, on_progress=lambda m: print(f"  {m}"))
            _print_kline_status_refresh()
            continue
        if choice == "D":
            issues = validate_integrity()
            if not issues:
                print("驗證通過，無損壞")
            else:
                for i in issues:
                    print(f"  ⚠ {i}")
            _print_kline_status_refresh()
            continue
        if choice == "E":
            removed = cleanup_corrupted()
            if not removed:
                print("無損壞檔案需清理")
            else:
                print("已刪除:", removed)
            _print_kline_status_refresh()
            continue
        print("無效選項，請重新輸入")


def read_local_market_data_for_date(trading_date: date, tickers: List[str], lookback_days: int = 90) -> Optional[dict]:
    """
    從本地 parquet 讀取某日所需的 K 線（trading_date 前 lookback_days 至 trading_date）。
    讀取路徑與下載／續跑一致：data/market_data/us_stocks/YYYY.parquet（依專案根目錄）。
    回傳 { ticker: DataFrame }，格式與 DataFetcher 一致（index=Date, columns Open/High/Low/Close/Volume）。
    若本地無數據則回傳 None。
    """
    _resolve_data_roots()
    # #region agent log
    _debug_log({"location": "data_manager.py:read_local", "message": "entry", "data": {"trading_date": str(trading_date), "tickers_count": len(tickers), "lookback_days": lookback_days}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H5"})
    # #endregion
    import pandas as pd
    from datetime import timedelta
    start_d = trading_date - timedelta(days=lookback_days)
    end_d = trading_date
    years = [str(y) for y in range(start_d.year, end_d.year + 1)]
    all_parts: List[pd.DataFrame] = []
    for year in years:
        path = os.path.join(MARKET_STOCKS_DIR, f"{year}.parquet")
        if not os.path.isfile(path):
            return None
        try:
            df = pd.read_parquet(path)
            if "symbol" not in df.columns and "ticker" in df.columns:
                df = df.rename(columns={"ticker": "symbol"})
            if "Date" not in df.columns and "date" in df.columns:
                df["Date"] = pd.to_datetime(df["date"])
            else:
                df["Date"] = pd.to_datetime(df["Date"])
            df = df[(df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)]
            all_parts.append(df)
        except Exception:
            return None
    if not all_parts:
        return None
    combined = pd.concat(all_parts, ignore_index=True)
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        if c not in combined.columns and c.lower() in combined.columns:
            combined = combined.rename(columns={c.lower(): c})
    ticker_set = set(tickers)
    result: Dict[str, pd.DataFrame] = {}
    for sym in combined["symbol"].unique():
        if sym not in ticker_set:
            continue
        sub = combined[combined["symbol"] == sym].copy()
        sub = sub.drop_duplicates(subset=["Date"]).set_index("Date").sort_index()
        if len(sub) >= 20:
            result[sym] = sub[["Open", "High", "Low", "Close", "Volume"]]
    # #region agent log
    _debug_log({"location": "data_manager.py:read_local", "message": "exit", "data": {"returned_tickers": len(result) if result else 0, "is_none": result is None}, "timestamp": int(__import__("time").time() * 1000), "sessionId": "debug-session", "hypothesisId": "H5"})
    # #endregion
    return result if result else None
