"""
股票掃描系統 v4 - 主程式
可選擇執行單一 Stage 或連續執行
"""
import sys
import os

# 添加當前目錄到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stage1_quick_scan import Stage1Scanner
from stage2_deep_verify import Stage2Verifier


def print_banner():
    """顯示啟動橫幅"""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         📊 股票掃描系統 v4 - 三階段智能篩選                    ║
║                                                               ║
║  Stage 1: 快速篩選 (10,000+ → 1,000)                         ║
║  Stage 2: 深度驗證 (1,000 → 250)                             ║
║  Stage 3: LLM 討論 (250 → 20) [開發中]                       ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def print_menu():
    """顯示選單"""
    print("\n請選擇執行模式：")
    print("  1️⃣  僅執行 Stage 1 (快速篩選)")
    print("  2️⃣  僅執行 Stage 2 (深度驗證)")
    print("  3️⃣  執行 Stage 1 + Stage 2 (連續)")
    print("  4️⃣  執行完整流程 (Stage 1 + 2 + 3) [開發中]")
    print("  0️⃣  退出")
    print()


def run_stage1_only():
    """僅執行 Stage 1"""
    print("\n" + "=" * 80)
    print("開始執行：Stage 1 快速篩選")
    print("=" * 80 + "\n")
    
    scanner = Stage1Scanner()
    df = scanner.run()
    
    if not df.empty:
        output_dir = scanner.save_results(df)
        print(f"\n✅ Stage 1 完成！")
        print(f"📁 結果路徑：{output_dir}/stage1_results.csv")
        return output_dir
    else:
        print("\n❌ Stage 1 失敗")
        return None


def run_stage2_only(stage1_path: str = None):
    """僅執行 Stage 2"""
    print("\n" + "=" * 80)
    print("開始執行：Stage 2 深度驗證")
    print("=" * 80 + "\n")
    
    verifier = Stage2Verifier(stage1_path)
    df = verifier.run()
    
    if not df.empty:
        output_dir = verifier.save_results(df)
        print(f"\n✅ Stage 2 完成！")
        print(f"📁 結果路徑：{output_dir}/stage2_results.csv")
        return output_dir
    else:
        print("\n❌ Stage 2 失敗")
        return None


def run_stage1_and_2():
    """連續執行 Stage 1 和 Stage 2"""
    print("\n" + "=" * 80)
    print("開始執行：Stage 1 + Stage 2 連續流程")
    print("=" * 80 + "\n")
    
    # Stage 1
    stage1_dir = run_stage1_only()
    
    if stage1_dir is None:
        print("\n❌ 流程終止：Stage 1 失敗")
        return
    
    # 自動找到 Stage 1 輸出的 CSV
    stage1_csv = os.path.join(stage1_dir, "stage1_results.csv")
    
    print("\n" + "⏸️ " * 40)
    print("⏸️  Stage 1 完成，準備開始 Stage 2...")
    print("⏸️ " * 40 + "\n")
    
    input("按 Enter 繼續執行 Stage 2...")
    
    # Stage 2
    stage2_dir = run_stage2_only(stage1_csv)
    
    if stage2_dir:
        print("\n" + "=" * 80)
        print("🎉 Stage 1 + Stage 2 全部完成！")
        print("=" * 80)
        print(f"📊 Stage 1 結果：{stage1_dir}/")
        print(f"📊 Stage 2 結果：{stage2_dir}/")
        print(f"\n➡️  接下來可執行 Stage 3 (開發中)")
    else:
        print("\n❌ 流程終止：Stage 2 失敗")


def run_full_pipeline():
    """執行完整流程 (Stage 1 + 2 + 3)"""
    print("\n⚠️  Stage 3 尚在開發中，目前僅執行 Stage 1 + 2")
    run_stage1_and_2()


def interactive_mode():
    """互動模式"""
    print_banner()
    
    while True:
        print_menu()
        choice = input("請輸入選項 (0-4): ").strip()
        
        if choice == "1":
            run_stage1_only()
        elif choice == "2":
            # 詢問是否指定 Stage 1 結果路徑
            custom_path = input("\n輸入 Stage 1 結果 CSV 路徑（留空自動尋找最新）: ").strip()
            run_stage2_only(custom_path if custom_path else None)
        elif choice == "3":
            run_stage1_and_2()
        elif choice == "4":
            run_full_pipeline()
        elif choice == "0":
            print("\n👋 再見！")
            break
        else:
            print("\n❌ 無效選項，請重新選擇")
        
        print("\n" + "-" * 80 + "\n")


def command_line_mode():
    """命令行模式"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="股票掃描系統 v4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python main.py --stage1                    # 僅執行 Stage 1
  python main.py --stage2                    # 僅執行 Stage 2（自動尋找 Stage 1 結果）
  python main.py --stage2 --input path.csv   # 執行 Stage 2（指定輸入）
  python main.py --all                       # 執行 Stage 1 + 2
        """
    )
    
    parser.add_argument('--stage1', action='store_true', help='執行 Stage 1 快速篩選')
    parser.add_argument('--stage2', action='store_true', help='執行 Stage 2 深度驗證')
    parser.add_argument('--all', action='store_true', help='執行完整流程 (Stage 1 + 2)')
    parser.add_argument('--input', type=str, help='Stage 2 輸入 CSV 路徑')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.all:
        run_stage1_and_2()
    elif args.stage1:
        run_stage1_only()
    elif args.stage2:
        run_stage2_only(args.input)
    else:
        # 沒有參數，進入互動模式
        interactive_mode()


if __name__ == "__main__":
    try:
        command_line_mode()
    except KeyboardInterrupt:
        print("\n\n⚠️  程式被中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
