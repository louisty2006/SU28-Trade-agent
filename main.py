"""
REISHI (霊視) v4.3 - 整合版 + 回測
一鍵運行 Stage 1 → Stage 2 → Stage 3
支援 --backtest YYYY-MM-DD：以該日為準取歷史數據，供回測用。
"""

import os
import sys
import argparse
from datetime import datetime, date, timedelta
from config import REIKAN_RUN_LOG, REIKAN_STAGE1_CSV, REIKAN_STAGE3_CSV, APP_NAME, APP_NAME_JP, VERSION


# ---------------------------------------------------------------------------
# 每次運行一個資料夾 + log 輸出（不改變原本運行形式）
# ---------------------------------------------------------------------------

def _create_run_dir():
    """建立本次運行的資料夾，名稱：當天日期_時分秒"""
    run_dir = os.path.join("reports", datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


class _Tee:
    """同時輸出到終端與 log 檔"""
    def __init__(self, stdout, log_file):
        self._stdout = stdout
        self._log_file = log_file

    def write(self, data):
        self._stdout.write(data)
        if self._log_file:
            self._log_file.write(data)
            self._log_file.flush()

    def flush(self):
        self._stdout.flush()
        if self._log_file:
            self._log_file.flush()


def _start_log(run_dir):
    """開始將 stdout 同時寫入 run_dir/REIKAN_run.log，並寫入 REISHI 漸層深度版標題"""
    log_path = os.path.join(run_dir, REIKAN_RUN_LOG)
    log_file = open(log_path, "w", encoding="utf-8")
    banner = """
═══════════════════════════════════════════════════════════════════════
                                                                       
                     R  E  I  S  H  I                      
                   ━━━━━━━━━━━━━━━━                       
                 ━━━━━━━━━━━━━━━━━━━━                     
               ━━━━━━━━━━━━━━━━━━━━━━━━                   
                                                                       
                      霊      視                          
                                                                       
             ░░░░░░░░░⚡░░░░░░░░░                       
           ░░░░░░░░░░░░░░░░░░░░░░░░                     
         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░                   
                                                                       
                      v4.3
                                                                       
═══════════════════════════════════════════════════════════════════════

"""
    log_file.write(banner)
    log_file.flush()
    original_stdout = sys.stdout
    sys.stdout = _Tee(original_stdout, log_file)
    return log_file, original_stdout


def _stop_log(log_file, original_stdout):
    """還原 stdout 並關閉 log 檔"""
    if log_file and original_stdout is not None:
        sys.stdout = original_stdout
        log_file.close()


def run_stage1(run_dir=None, max_stocks=None, top_n=500, as_of_date=None, backtest_start=None):
    """執行 Stage 1: 快速掃描。as_of_date 有值時為回測模式，backtest_start 為回測起始日（數據範圍限制）。"""
    print("\n" + "=" * 70)
    print("🚀 Stage 1: 快速掃描全市場")
    if as_of_date:
        print(f"   📅 回測模式：數據截至 {as_of_date}")
    print("=" * 70)
    try:
        from stage1_quick_scan import Stage1Scanner
        output_dir = run_dir if run_dir else "reports/stage1"
        scanner = Stage1Scanner(output_dir=output_dir)
        return scanner.run(top_n=top_n, max_stocks=max_stocks, as_of_date=as_of_date, backtest_start=backtest_start)
    except Exception as e:
        print(f"❌ Stage 1 錯誤: {e}")
        return None


def run_stage2(stage1_path: str = None, run_dir=None, as_of_date=None, backtest_start=None):
    """執行 Stage 2: 深度驗證。as_of_date / backtest_start 為回測模式的時間範圍。"""
    print("\n" + "=" * 70)
    print("🔍 Stage 2: 深度驗證")
    if as_of_date:
        print(f"   📅 回測模式：數據截至 {as_of_date}")
    print("=" * 70)
    try:
        from stage2_deep_verify import Stage2Verifier
        path = stage1_path
        if run_dir and not path:
            candidate = os.path.join(run_dir, REIKAN_STAGE1_CSV)
            if os.path.exists(candidate):
                path = candidate
        verifier = Stage2Verifier(stage1_results_path=path, output_dir=run_dir, as_of_date=as_of_date, backtest_start=backtest_start)
        df = verifier.run()
        if df is not None and not df.empty:
            verifier.save_results(df)
        return df
    except Exception as e:
        print(f"❌ Stage 2 錯誤: {e}")
        return None


def run_stage3(stage2_path: str = None, run_dir=None, top_n=20, as_of_date=None):
    """執行 Stage 3: LLM 討論。as_of_date 有值時提示為「數據截至該日」，假裝那天在跑一次。"""
    print("\n" + "=" * 70)
    print("🤖 Stage 3: Multi-Agent LLM 討論")
    if as_of_date:
        print(f"   📅 回測模式：情境截至 {as_of_date}")
    print("=" * 70)
    try:
        from stage3_llm_discussion import Stage3Discussion
        discussion = Stage3Discussion(output_dir=run_dir)
        results = discussion.run(top_n=top_n, as_of_date=as_of_date)
        if results:
            discussion.save_report()
        return results
    except Exception as e:
        print(f"❌ Stage 3 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all():
    """執行完整流程: Stage 1 → 2 → 3，所有輸出與 log 寫入同一個 run 資料夾"""
    start_time = datetime.now()
    run_dir = _create_run_dir()
    log_file, original_stdout = _start_log(run_dir)
    try:
        print("\n" + "🚀" * 25)
        print(f"{APP_NAME} - 完整流程")
        print("🚀" * 25)
        print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 本次報告目錄: {run_dir}")
        print("=" * 70)

        stage1_results = run_stage1(run_dir)
        stage2_results = run_stage2(run_dir=run_dir)
        stage3_results = run_stage3(run_dir=run_dir)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("🎉 完整流程完成！")
        print("=" * 70)
        print(f"總耗時: {duration/60:.1f} 分鐘")
        if stage3_results:
            print(f"最終產生 {len(stage3_results)} 支推薦股票")
        print(f"📁 報告與 log: {run_dir}")
        print("=" * 70)
    finally:
        _stop_log(log_file, original_stdout)


def run_test():
    """快速測試 Stage 3，輸出與 log 寫入本次 run 資料夾"""
    run_dir = _create_run_dir()
    log_file, original_stdout = _start_log(run_dir)
    try:
        print("\n" + "🧪" * 25)
        print("快速測試 Stage 3 LLM 討論")
        print("🧪" * 25)
        print(f"📁 本次報告目錄: {run_dir}")

        from stage3_llm_discussion import Stage3Discussion
        stage3 = Stage3Discussion(output_dir=run_dir)
        results = stage3.run(top_n=5)
        if results:
            stage3.save_report()
        print(f"📁 報告與 log: {run_dir}")
    finally:
        _stop_log(log_file, original_stdout)


def run_daily_unified(positions_path: str = None, as_of_date: date = None, backtest_start: date = None, output_base: str = None, max_stocks: int = None, top_n: int = None):
    """
    每日合一 run：Stage 1→2→3（小範圍）＋持倉監控＋今日決策，產出單一報告目錄。
    as_of_date 有值時為回測模式：數據與情境皆截至該日。
    backtest_start 有值時：數據從該日開始（range 之前看不到）。
    output_base 有值時（僅回測）：報告目錄為 output_base/YYYY-MM-DD/，用於 365 天逐日回測。
    max_stocks / top_n 有值時覆寫每日掃描規模（小股數回測用）。
    """
    start_time = datetime.now()
    if as_of_date and output_base:
        run_dir = os.path.join(output_base, as_of_date.strftime("%Y-%m-%d"))
    elif as_of_date:
        run_dir = os.path.join("reports", "backtest", as_of_date.strftime("%Y-%m-%d"))
    else:
        run_dir = os.path.join("reports", "daily", date.today().strftime("%Y-%m-%d"))
    run_dir_abs = os.path.abspath(run_dir)
    os.makedirs(run_dir_abs, exist_ok=True)
    log_file, original_stdout = _start_log(run_dir)

    try:
        print("\n" + "=" * 70)
        print("🔮 啟動霊視，洞察市場")
        if as_of_date:
            if backtest_start:
                print(f"📅 回測 run（數據範圍 {backtest_start} ~ {as_of_date}）Stage 1→2→3 ＋ 持倉監控 ＋ 當日決策")
            else:
                print(f"📅 回測 run（數據截至 {as_of_date}）Stage 1→2→3 ＋ 持倉監控 ＋ 當日決策")
        else:
            print("📅 每日合一 run（Stage 1→2→3 ＋ 持倉監控 ＋ 今日最好決定）")
        print("=" * 70)
        print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 報告目錄: {run_dir_abs}")
        print("=" * 70)

        _max = max_stocks if max_stocks is not None else 50
        _top = top_n if top_n is not None else 10
        run_stage1(run_dir=run_dir_abs, max_stocks=_max, top_n=_top, as_of_date=as_of_date, backtest_start=backtest_start)
        run_stage2(run_dir=run_dir_abs, as_of_date=as_of_date, backtest_start=backtest_start)
        run_stage3(run_dir=run_dir_abs, top_n=_top, as_of_date=as_of_date)

        from daily_monitor import run_daily_monitor
        default_positions = os.path.join(os.path.dirname(__file__), "data", "positions.csv")
        resolved_positions = positions_path
        if positions_path:
            abs_path = os.path.abspath(positions_path)
            if not os.path.isfile(abs_path):
                print(f"⚠️ 指定的持倉檔不存在: {positions_path} → 改用預設 {default_positions}")
                resolved_positions = default_positions
            else:
                resolved_positions = abs_path
        else:
            resolved_positions = default_positions
        stage3_csv = os.path.join(run_dir_abs, REIKAN_STAGE3_CSV)
        run_daily_monitor(
            positions_path=resolved_positions,
            output_dir=run_dir_abs,
            stage3_csv_path=stage3_csv if os.path.isfile(stage3_csv) else None,
            as_of_date=as_of_date,
            backtest_start=backtest_start,
        )

        duration = (datetime.now() - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("🎉 洞察完成，建議如下")
        print("=" * 70)
        print(f"總耗時: {duration/60:.1f} 分鐘")
        print(f"📁 報告與持倉可編輯檔: {run_dir_abs}")
        print("=" * 70)
    finally:
        _stop_log(log_file, original_stdout)


def run_backtest_range(start_dt: date, end_dt: date, quick: bool = False):
    """
    365 天逐日回測：從 start_dt 到 end_dt 每個交易日跑一次完整 pipeline。
    決策僅用「前一交易日及之前」的數據（無偷看）；執行以當日收盤價模擬。
    quick=True 時每日只掃少數股票（max_stocks=15, top_n=5）以加快。
    """
    from backtest_simulator import (
        get_trading_days,
        prev_trading_day,
        load_state,
        save_state,
        load_report_decision,
        apply_decision,
        portfolio_value,
    )
    from daily_monitor import get_current_price
    from config import BACKTEST_INITIAL_CASH

    base_dir = os.path.join("reports", "backtest_range", f"{start_dt:%Y-%m-%d}_{end_dt:%Y-%m-%d}")
    base_dir_abs = os.path.abspath(base_dir)
    state_dir = os.path.join(base_dir_abs, "state")
    os.makedirs(state_dir, exist_ok=True)

    # 初始狀態：空持倉、初始現金（寫入 state 供第一天讀取）
    save_state(state_dir, BACKTEST_INITIAL_CASH, [], start_dt - timedelta(days=1) if start_dt else start_dt)

    trading_days = get_trading_days(start_dt, end_dt)
    if not trading_days:
        print("❌ 區間內無交易日")
        return

    start_time = datetime.now()
    summary_rows = []

    print("\n" + "=" * 70)
    print("🔮 啟動霊視，洞察市場")
    print(f"📅 回測 range：{start_dt} ~ {end_dt}，共 {len(trading_days)} 個交易日，逐日跑 pipeline")
    if quick:
        print("📌 小股數回測（每日少掃股票，加快）")
    print("📌 決策僅用「前一交易日及之前」數據；執行以當日收盤價（無偷看未來）")
    print("=" * 70)
    print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 報告目錄: {base_dir_abs}")
    print("=" * 70)

    for i, d in enumerate(trading_days):
        prev_d = prev_trading_day(d)
        # 決策用數據只到 prev_d；第一天若 prev_d < start_dt 則取 prev_d 前約 90 天
        backtest_start_eff = (prev_d - timedelta(days=90)) if prev_d < start_dt else start_dt

        cash, positions = load_state(state_dir)
        state_path = os.path.join(state_dir, "positions.csv")
        print(f"\n📅 [{i+1}/{len(trading_days)}] 執行日 {d} | 數據截至 {prev_d} | 現金 {cash:.0f} | 持倉 {len(positions)} 檔")
        run_daily_unified(
            positions_path=state_path,
            as_of_date=prev_d,
            backtest_start=backtest_start_eff,
            output_base=base_dir_abs,
            max_stocks=15 if quick else None,
            top_n=5 if quick else None,
        )

        # 報告寫在 base_dir/prev_d（as_of_date=prev_d）
        run_dir_report = os.path.join(base_dir_abs, prev_d.strftime("%Y-%m-%d"))
        decision = load_report_decision(run_dir_report)
        # 執行價一律用「當日 d」收盤價（決策已只用 prev_d 及之前）
        tickers_needed = {p["ticker"] for p in positions}
        for e in (decision.get("new_entries") or [])[:3]:
            t = (e.get("ticker") or "").strip()
            if t:
                tickers_needed.add(t)
        execution_prices_d = {}
        for ticker in tickers_needed:
            p = get_current_price(ticker, as_of_date=d, backtest_start=start_dt)
            if p is not None:
                execution_prices_d[ticker] = p
        cash, positions = apply_decision(
            cash, positions, decision, execution_prices_d, execution_prices_d, d.strftime("%Y-%m-%d"),
        )
        save_state(state_dir, cash, positions, d)
        value = portfolio_value(cash, positions, execution_prices_d)
        ret_pct = (value - BACKTEST_INITIAL_CASH) / BACKTEST_INITIAL_CASH * 100
        summary_rows.append({
            "date": d.strftime("%Y-%m-%d"),
            "portfolio_value": round(value, 2),
            "cash": round(cash, 2),
            "positions_count": len(positions),
            "return_pct": round(ret_pct, 2),
        })
        print(f"   組合價值 {value:.0f} | 報酬 {ret_pct:+.2f}%")

    # 寫入回測摘要
    import csv as csv_module
    summary_path = os.path.join(base_dir_abs, "backtest_summary.csv")
    with open(summary_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv_module.DictWriter(f, fieldnames=["date", "portfolio_value", "cash", "positions_count", "return_pct"])
        w.writeheader()
        w.writerows(summary_rows)
    final_value = summary_rows[-1]["portfolio_value"] if summary_rows else BACKTEST_INITIAL_CASH
    final_ret = (final_value - BACKTEST_INITIAL_CASH) / BACKTEST_INITIAL_CASH * 100
    duration = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("🎉 回測 range 完成")
    print("=" * 70)
    print(f"總交易日: {len(trading_days)}")
    print(f"初始現金: {BACKTEST_INITIAL_CASH:,.0f}")
    print(f"期末組合價值: {final_value:,.2f}")
    print(f"總報酬率: {final_ret:+.2f}%")
    print(f"總耗時: {duration/60:.1f} 分鐘")
    print(f"📁 報告與摘要: {base_dir_abs}")
    print(f"📄 每日價值: {summary_path}")
    print("=" * 70)


def run_test_all():
    """小樣本跑完 Stage 1→2→3（約 15 檔掃描、Top 5→Stage2→Stage3 取 5 支），驗證輸出與 log"""
    start_time = datetime.now()
    run_dir = _create_run_dir()
    log_file, original_stdout = _start_log(run_dir)
    try:
        print("\n" + "🧪" * 25)
        print("小樣本三階段測試 (Stage 1→2→3)")
        print("🧪" * 25)
        print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 本次報告目錄: {run_dir}")
        print("=" * 70)

        run_stage1(run_dir=run_dir, max_stocks=15, top_n=5)
        run_stage2(run_dir=run_dir)
        run_stage3(run_dir=run_dir, top_n=5)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print("\n" + "=" * 70)
        print("🎉 小樣本三階段測試完成！")
        print("=" * 70)
        print(f"總耗時: {duration:.1f} 秒")
        print(f"📁 報告與 log: {run_dir}")
        print("=" * 70)
    finally:
        _stop_log(log_file, original_stdout)


def main():
    parser = argparse.ArgumentParser(description=f'{APP_NAME} v{VERSION}')
    parser.add_argument('--all', action='store_true', help='運行完整流程 (Stage 1→2→3)')
    parser.add_argument('--stage1', action='store_true', help='只運行 Stage 1')
    parser.add_argument('--stage2', action='store_true', help='只運行 Stage 2')
    parser.add_argument('--stage3', action='store_true', help='只運行 Stage 3')
    parser.add_argument('--test', action='store_true', help='快速測試 Stage 3')
    parser.add_argument('--test-all', action='store_true', dest='test_all', help='小樣本跑完 Stage 1→2→3（約 15 檔）')
    parser.add_argument('--daily', action='store_true', help='每日合一：Stage 1→2→3 ＋ 持倉監控 ＋ 今日最好決定，單一報告目錄')
    parser.add_argument('--backtest', nargs='+', metavar='YYYY-MM-DD', default=None,
                        help='回測：單日 --backtest 2025-01-10；區間 --backtest 2025-01-01 2025-01-15')
    parser.add_argument('--quick', action='store_true', help='回測區間時小股數加快（每日約 15 檔）')
    parser.add_argument('--positions', default=None, help='持倉表 CSV 路徑（預設 data/positions.csv；可指定報告內 positions_edit.csv）')
    
    args = parser.parse_args()
    
    as_of_date = None
    if args.backtest:
        if len(args.backtest) == 1:
            try:
                as_of_date = datetime.strptime(args.backtest[0], "%Y-%m-%d").date()
            except ValueError:
                print(f"❌ --backtest 格式須為 YYYY-MM-DD，例如 --backtest 2023-06-15")
                return
            try:
                run_daily_unified(positions_path=args.positions, as_of_date=as_of_date)
            except Exception as e:
                print(f"❌ 回測 run 錯誤: {e}")
                import traceback
                traceback.print_exc()
        elif len(args.backtest) == 2:
            try:
                start_dt = datetime.strptime(args.backtest[0], "%Y-%m-%d").date()
                end_dt = datetime.strptime(args.backtest[1], "%Y-%m-%d").date()
            except ValueError:
                print("❌ --backtest 區間格式須為 YYYY-MM-DD YYYY-MM-DD，例如 --backtest 2025-01-01 2025-01-15")
                return
            if start_dt >= end_dt:
                print("❌ 結束日期須晚於開始日期")
                return
            try:
                run_backtest_range(start_dt, end_dt, quick=args.quick)
            except Exception as e:
                print(f"❌ 回測 run 錯誤: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ --backtest 請給 1 個日期（單日）或 2 個日期（區間），例如 --backtest 2025-01-01 2025-01-15 --quick")
            return
    elif args.daily:
        try:
            run_daily_unified(positions_path=args.positions)
        except Exception as e:
            print(f"❌ 每日合一 run 錯誤: {e}")
            import traceback
            traceback.print_exc()
    elif args.test_all:
        run_test_all()
    elif args.stage1:
        run_dir = _create_run_dir()
        log_file, original_stdout = _start_log(run_dir)
        try:
            print(f"📁 本次報告目錄: {run_dir}")
            run_stage1(run_dir)
            print(f"📁 報告與 log: {run_dir}")
        finally:
            _stop_log(log_file, original_stdout)
    elif args.stage2:
        run_dir = _create_run_dir()
        log_file, original_stdout = _start_log(run_dir)
        try:
            print(f"📁 本次報告目錄: {run_dir}")
            run_stage2(run_dir=run_dir)
            print(f"📁 報告與 log: {run_dir}")
        finally:
            _stop_log(log_file, original_stdout)
    elif args.stage3:
        run_dir = _create_run_dir()
        log_file, original_stdout = _start_log(run_dir)
        try:
            print(f"📁 本次報告目錄: {run_dir}")
            run_stage3(run_dir=run_dir)
            print(f"📁 報告與 log: {run_dir}")
        finally:
            _stop_log(log_file, original_stdout)
    elif args.test:
        run_test()
    elif args.all:
        run_all()
    else:
        # 互動式啟動
        print("""
═══════════════════════════════════════════════════════════════════════
                                                                       
                     R  E  I  S  H  I                      
                   ━━━━━━━━━━━━━━━━                       
                 ━━━━━━━━━━━━━━━━━━━━                     
               ━━━━━━━━━━━━━━━━━━━━━━━━                   
                                                                       
                      霊      視                          
                                                                       
             ░░░░░░░░░⚡░░░░░░░░░                       
           ░░░░░░░░░░░░░░░░░░░░░░░░                     
         ░░░░░░░░░░░░░░░░░░░░░░░░░░░░                   
                                                                       
                      v4.3
                                                                       
═══════════════════════════════════════════════════════════════════════
""")
        print("\n請選擇運行模式：")
        print("  [1] 正常 mode - 今日決策（持倉 + 當天思考）")
        print("  [2] 回測 mode - 歷史回放（測試策略）")
        print("  [0] 顯示命令列參數說明")
        
        choice = input("\n請輸入選項 [1/2/0]: ").strip()
        
        if choice == "1":
            print("\n🔮 啟動霊視，洞察市場...")
            try:
                run_daily_unified()
            except Exception as e:
                print(f"❌ 每日合一 run 錯誤: {e}")
                import traceback
                traceback.print_exc()
        
        elif choice == "2":
            print("\n📅 回測模式")
            print("  請選擇回測規模：")
            print("    [1] 正常回測（完整掃描，每日約 50 檔）")
            print("    [2] 小股數回測（少掃股票，每日約 15 檔，加快）")
            choice2 = input("  請輸入 [1/2]: ").strip()
            quick = choice2 == "2"
            start_str = input("  請輸入開始日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")
            end_str = input("  請輸入結束日期（YYYY-MM-DD 或 YYYYMMDD）：").strip().replace(" ", "")
            
            def _norm_date(s):
                """接受 YYYY-MM-DD 或 YYYYMMDD（8 位），回傳 YYYY-MM-DD"""
                s = s.strip()
                if len(s) == 8 and s.isdigit():
                    return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
                return s
            
            try:
                from backtest_simulator import get_trading_days
                start_dt = datetime.strptime(_norm_date(start_str), "%Y-%m-%d").date()
                end_dt = datetime.strptime(_norm_date(end_str), "%Y-%m-%d").date()
                if start_dt >= end_dt:
                    print("❌ 結束日期必須晚於開始日期")
                    return
                n_days = len(get_trading_days(start_dt, end_dt))
                mode_str = "小股數" if quick else "正常"
                print(f"\n🔮 啟動霊視回測（{mode_str}）（{start_dt} ~ {end_dt}），共 {n_days} 個交易日，逐日跑 pipeline...")
                run_backtest_range(start_dt, end_dt, quick=quick)
            except ValueError:
                print("❌ 日期格式錯誤，請用 YYYY-MM-DD 或 YYYYMMDD，例如 2023-06-15 或 20230101")
            except Exception as e:
                print(f"❌ 回測 run 錯誤: {e}")
                import traceback
                traceback.print_exc()
        
        elif choice == "0":
            print("\n" + "=" * 50)
            print("📋 命令列參數說明")
            print("=" * 50)
            print("  python main.py --all     # 完整流程 (Stage 1→2→3)")
            print("  python main.py --stage1  # 只運行 Stage 1")
            print("  python main.py --stage2  # 只運行 Stage 2")
            print("  python main.py --stage3  # 只運行 Stage 3")
            print("  python main.py --test    # 快速測試 Stage 3")
            print("  python main.py --test-all # 小樣本跑完 Stage 1→2→3（約 15 檔）")
            print("  python main.py --daily    # 每日合一：Stage 1→2→3 ＋ 持倉 ＋ 今日最好決定（單一報告）")
            print("  python main.py --backtest 2025-01-10  # 回測單日")
            print("  python main.py --backtest 2025-01-01 2025-01-15 --quick  # 回測區間（小股數加快）")
            print("  python main.py --daily --positions reports/daily/YYYY-MM-DD/positions_edit.csv  # 使用人手改動後的持倉")
            print("\n💡 --daily 會建立 reports/daily/日期/，內含 positions_edit.csv 可人手改動持倉")
            print("💡 --backtest 供回測用，數據與 LLM 情境皆截至指定日")
            print("💡 建議先用 --test 或 --test-all 測試")
        
        else:
            print("❌ 無效選項，請重新執行並選擇 1/2/0")


if __name__ == "__main__":
    main()
