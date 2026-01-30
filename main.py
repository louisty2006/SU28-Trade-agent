"""
REISHI (霊視) v4.3 - 整合版 + 回測
一鍵運行 Stage 1 → Stage 2 → Stage 3
支援 --backtest YYYY-MM-DD：以該日為準取歷史數據，供回測用。
"""

import os
import sys
import argparse
from datetime import datetime, date
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


def run_daily_unified(positions_path: str = None, as_of_date: date = None, backtest_start: date = None):
    """
    每日合一 run：Stage 1→2→3（小範圍）＋持倉監控＋今日決策，產出單一報告目錄。
    as_of_date 有值時為回測模式：數據與情境皆截至該日。
    backtest_start 有值時：數據從該日開始（range 之前看不到）。
    """
    start_time = datetime.now()
    if as_of_date:
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

        run_stage1(run_dir=run_dir_abs, max_stocks=50, top_n=10, as_of_date=as_of_date, backtest_start=backtest_start)
        run_stage2(run_dir=run_dir_abs, as_of_date=as_of_date, backtest_start=backtest_start)
        run_stage3(run_dir=run_dir_abs, top_n=10, as_of_date=as_of_date)

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
    parser.add_argument('--backtest', metavar='YYYY-MM-DD', default=None, help='回測模式：以該日為準取歷史數據，報告寫入 reports/backtest/YYYY-MM-DD')
    parser.add_argument('--positions', default=None, help='持倉表 CSV 路徑（預設 data/positions.csv；可指定報告內 positions_edit.csv）')
    
    args = parser.parse_args()
    
    as_of_date = None
    if args.backtest:
        try:
            as_of_date = datetime.strptime(args.backtest, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ --backtest 格式須為 YYYY-MM-DD，例如 --backtest 2023-06-15")
            return
        try:
            run_daily_unified(positions_path=args.positions, as_of_date=as_of_date)
        except Exception as e:
            print(f"❌ 回測 run 錯誤: {e}")
            import traceback
            traceback.print_exc()
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
            start_str = input("  請輸入開始日期（YYYY-MM-DD）：").strip()
            end_str = input("  請輸入結束日期（YYYY-MM-DD）：").strip()
            
            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
                end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
                if start_dt >= end_dt:
                    print("❌ 結束日期必須晚於開始日期")
                    return
                print(f"\n🔮 啟動霊視回測（{start_dt} ~ {end_dt}），數據範圍限制中...")
                run_daily_unified(as_of_date=end_dt, backtest_start=start_dt)
            except ValueError as e:
                print(f"❌ 日期格式錯誤，須為 YYYY-MM-DD，例如 2023-06-15")
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
            print("  python main.py --backtest 2023-06-15  # 回測：以該日為準取歷史數據")
            print("  python main.py --daily --positions reports/daily/YYYY-MM-DD/positions_edit.csv  # 使用人手改動後的持倉")
            print("\n💡 --daily 會建立 reports/daily/日期/，內含 positions_edit.csv 可人手改動持倉")
            print("💡 --backtest 供回測用，數據與 LLM 情境皆截至指定日")
            print("💡 建議先用 --test 或 --test-all 測試")
        
        else:
            print("❌ 無效選項，請重新執行並選擇 1/2/0")


if __name__ == "__main__":
    main()
