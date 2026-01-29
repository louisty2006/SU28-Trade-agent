VERSION = "4.2"

"""
Stock Scanner v4.2 - 整合版
一鍵運行 Stage 1 → Stage 2 → Stage 3
"""

import os
import sys
import argparse
from datetime import datetime


def run_stage1():
    """執行 Stage 1: 快速掃描"""
    print("\n" + "=" * 70)
    print("🚀 Stage 1: 快速掃描全市場")
    print("=" * 70)
    try:
        from stage1_quick_scan import Stage1Scanner
        scanner = Stage1Scanner()
        return scanner.run()
    except Exception as e:
        print(f"❌ Stage 1 錯誤: {e}")
        return None


def run_stage2(stage1_path: str = None):
    """執行 Stage 2: 深度驗證"""
    print("\n" + "=" * 70)
    print("🔍 Stage 2: 深度驗證")
    print("=" * 70)
    try:
        from stage2_deep_verify import Stage2Verifier
        verifier = Stage2Verifier(stage1_path)
        return verifier.run()
    except Exception as e:
        print(f"❌ Stage 2 錯誤: {e}")
        return None


def run_stage3(stage2_path: str = None):
    """執行 Stage 3: LLM 討論"""
    print("\n" + "=" * 70)
    print("🤖 Stage 3: Multi-Agent LLM 討論")
    print("=" * 70)
    try:
        from stage3_llm_discussion import Stage3Discussion
        discussion = Stage3Discussion()
        results = discussion.run(top_n=20)
        if results:
            discussion.save_report()
        return results
    except Exception as e:
        print(f"❌ Stage 3 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all():
    """執行完整流程: Stage 1 → 2 → 3"""
    start_time = datetime.now()
    
    print("\n" + "🚀" * 25)
    print("股票掃描系統 v4.2 - 完整流程")
    print("🚀" * 25)
    print(f"開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Stage 1
    stage1_results = run_stage1()
    
    # Stage 2
    stage2_results = run_stage2()
    
    # Stage 3
    stage3_results = run_stage3()
    
    # 完成
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("🎉 完整流程完成！")
    print("=" * 70)
    print(f"總耗時: {duration/60:.1f} 分鐘")
    if stage3_results:
        print(f"最終產生 {len(stage3_results)} 支推薦股票")
    print("=" * 70)


def run_test():
    """快速測試 Stage 3"""
    print("\n" + "🧪" * 25)
    print("快速測試 Stage 3 LLM 討論")
    print("🧪" * 25)
    
    from stage3_llm_discussion import Stage3Discussion
    stage3 = Stage3Discussion()
    results = stage3.run(top_n=5)
    if results:
        stage3.save_report()


def main():
    parser = argparse.ArgumentParser(description='Stock Scanner v4.2')
    parser.add_argument('--all', action='store_true', help='運行完整流程 (Stage 1→2→3)')
    parser.add_argument('--stage1', action='store_true', help='只運行 Stage 1')
    parser.add_argument('--stage2', action='store_true', help='只運行 Stage 2')
    parser.add_argument('--stage3', action='store_true', help='只運行 Stage 3')
    parser.add_argument('--test', action='store_true', help='快速測試 Stage 3')
    
    args = parser.parse_args()
    
    if args.stage1:
        run_stage1()
    elif args.stage2:
        run_stage2()
    elif args.stage3:
        run_stage3()
    elif args.test:
        run_test()
    elif args.all:
        run_all()
    else:
        # 顯示選單
        print("\n" + "=" * 50)
        print("📊 Stock Scanner v4.2")
        print("=" * 50)
        print("\n請選擇運行模式：")
        print("  python main.py --all     # 完整流程 (Stage 1→2→3)")
        print("  python main.py --stage1  # 只運行 Stage 1")
        print("  python main.py --stage2  # 只運行 Stage 2")
        print("  python main.py --stage3  # 只運行 Stage 3")
        print("  python main.py --test    # 快速測試 Stage 3")
        print("\n💡 建議先用 --test 測試 LLM 連接")


if __name__ == "__main__":
    main()
