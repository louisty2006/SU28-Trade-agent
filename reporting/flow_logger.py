"""
REISHI 霊視 v5.0 - Flow Chart 風格 Log

Log 完全跟隨流程圖結構輸出：
  輸入層 → 第一層防護：數據驗證 → 五大 AI 方向分析層 → 第二層防護：LLM 防幻覺 → 輸出驗證與審計 → 報告
並在每一步標示：使用哪個數據源、哪些股票、分析什麼數字/圖表、得到什麼結果。
"""

from typing import List, Optional, Any
import sys


# 流程圖框線
_BOX_TOP = "┌"
_BOX_BOTTOM = "└"
_BOX_SIDE = "│"
_BOX_MID = "├"
_LINE_H = "─"
_LINE_V = "│"
_ARROW = "▼"


class FlowLogger:
    """
    依流程圖一層層輸出的 Logger。
    可注入 file= 或使用預設 sys.stdout；flush 確保即時寫入。
    """

    def __init__(self, file=None, flush_each=True):
        self._file = file if file is not None else sys.stdout
        self._flush = flush_each

    def _out(self, msg: str):
        print(msg, file=self._file, flush=self._flush)

    def _box(self, title: str, body_lines: List[str], indent: str = "  ", width: int = 70):
        """輸出一個流程圖風格的區塊"""
        w = width - 4  # 內容寬度（左右各留一空格 + 框線）
        self._out(indent + _BOX_TOP + _LINE_H * (width - 2) + "┐")
        self._out(indent + _BOX_SIDE + " " + (title[:w] if len(title) > w else title.ljust(w)) + " " + _BOX_SIDE)
        for line in body_lines:
            if not line.strip():
                self._out(indent + _BOX_SIDE + " " * (width - 2) + _BOX_SIDE)
            else:
                self._out(indent + _BOX_SIDE + " " + (line[:w] if len(line) > w else line.ljust(w)) + " " + _BOX_SIDE)
        self._out(indent + _BOX_BOTTOM + _LINE_H * (width - 2) + "┘")

    def _arrow(self, indent: str = "  "):
        self._out(indent + " " + _LINE_V)
        self._out(indent + " " + _ARROW)

    # ---------- 輸入層：你的狀態 → 市場數據 → 即時新聞 → 霊視記憶 ----------
    def log_input_layer(
        self,
        your_state: str,
        market_data_desc: str,
        news_desc: str,
        memory_desc: str,
        as_of_date: str = "",
        mode: str = "每日分析",
    ):
        """
        輸入層：依序呈現
          你的狀態 → 市場數據 → 即時新聞 → 霊視記憶
        然後進入【第一層防護：數據驗證】。
        """
        body = [
            "你的狀態：  " + (your_state or "—"),
            "市場數據：  " + (market_data_desc or "—"),
            "即時新聞：  " + (news_desc or "—"),
            "霊視記憶：  " + (memory_desc or "—"),
        ]
        if as_of_date:
            body.append("數據截至：  " + as_of_date)
        if mode:
            body.append("模式：      " + mode)
        self._out("")
        self._box("【輸入層】你的狀態 → 市場數據 → 即時新聞 → 霊視記憶", body)
        self._arrow()

    # ---------- 第一層防護：數據驗證 ----------
    def log_layer1_start(self, data_source: str):
        """第一層防護開始：使用的數據源"""
        body = [
            "本步驟數據來源：  " + data_source,
            "動作：拉取歷史 K 線、驗證筆數與欄位",
        ]
        self._box("【第一層防護】數據驗證", body)
        self._arrow()

    def log_layer1_fetch(self, ticker: str, index: int, total: int):
        """正在取得某一檔（數據來自本步驟數據源）"""
        self._out(f"  {_BOX_MID} 正在取得 {ticker} ({index}/{total}) …")

    def log_layer1_result(self, valid_count: int, tickers: List[str], data_source: str = "", skipped: Optional[List[str]] = None):
        """數據驗證結果"""
        body = [
            "數據來源：  " + (data_source or "—"),
            f"有效數據：{valid_count} 檔",
            f"標的：{', '.join(tickers[:8])}{' ...' if len(tickers) > 8 else ''}",
        ]
        if skipped:
            body.append(f"跳過（資料不足）：{', '.join(skipped[:5])}{' ...' if len(skipped) > 5 else ''}")
        self._box("【第一層防護】數據驗證 — 結果", body)
        self._arrow()

    # ---------- 五大 AI 方向分析層 ----------
    def log_ai_layer_start(self):
        """五大 AI 方向分析層 — 區塊開始"""
        self._out("")
        self._box("【五大 AI 方向分析層】", [
            "以下依序：圖表型態識別 → 因果推理 → 情緒分析 → Multi-Agent 協作 → 霊視記憶參考",
            "每一步下方標明「本步驟數據來源」與「LLM 正在做什麼」（若有）",
        ])
        self._arrow()

    def log_ai_2_start(self, ticker_count: int, data_sources: str = ""):
        """[2] 圖表型態識別 — 開始"""
        default_src = "第一層驗證後的 K 線（步驟 1 的 Yahoo/DataFetcher）"
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            f"輸入：{ticker_count} 檔 OHLCV",
            "分析：突破、VCP、均線排列；LLM 看圖驗證（MVP 可未呼叫）",
        ]
        self._box("  [2/5] 圖表型態識別（規則偵測 + 型態）", body)
        self._arrow()

    def log_ai_2_fetch(self, ticker: str, index: int, total: int):
        self._out(f"    {_BOX_MID} 正在掃描 {ticker} ({index}/{total}) …")

    def log_ai_2_result(self, candidate_count: int, candidate_tickers: Optional[List[str]] = None):
        body = [f"候選數：{candidate_count} 檔"]
        if candidate_tickers:
            body.append(f"候選：{', '.join(candidate_tickers[:8])}{' ...' if len(candidate_tickers) > 8 else ''}")
        self._box("  [2/5] 圖表型態識別 — 結果", body)
        self._arrow()

    def log_ai_3_start(self, data_sources: str = ""):
        """[3] 因果推理"""
        default_src = "即時新聞（Finnhub）、持倉（本地）；LLM 因果鏈（四角）"
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            "分析：新聞影響、供應鏈風險、持倉集中度與連鎖風險",
        ]
        self._box("  [3/5] 因果推理", body)
        self._arrow()

    def log_ai_3_result(self):
        self._box("  [3/5] 因果推理 — 結果", ["產出：影響鏈、風險摘要、建議動作"])
        self._arrow()

    def log_ai_4_start(self, ticker_count: int, data_sources: str = ""):
        """[4] 情緒分析"""
        default_src = "即時新聞（Finnhub）、標的列表；LLM 情緒分析（四角）"
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            f"輸入：{ticker_count} 檔標的",
            "分析：情緒分數、關鍵因素、風險提示",
        ]
        self._box("  [4/5] 情緒分析", body)
        self._arrow()

    def log_ai_4_fetch(self, ticker: str, index: int, total: int):
        self._out(f"    {_BOX_MID} 正在分析 {ticker} ({index}/{total}) …")

    def log_ai_4_result(self):
        self._box("  [4/5] 情緒分析 — 結果", ["產出：各標的情緒分數與風險清單"])
        self._arrow()

    def log_ai_5_start(self, candidate_count: int, data_sources: str = ""):
        """[5] Multi-Agent 協作分析"""
        default_src = "圖表候選（步驟 2）、市場數據（步驟 1）；LLM 四角（Scitely/Cohere/Mistral/OpenRouter）"
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            f"輸入：圖表候選 {candidate_count} 檔 + 市場數據",
            "分析：基本面／技術／風險／宏觀共識、分歧點、最終建議",
        ]
        self._box("  [5/5] Multi-Agent 協作分析", body)
        self._arrow()

    def log_ai_5_result(self):
        self._box("  [5/5] Multi-Agent — 結果", ["產出：共識評分、共識動作、最終建議"])
        self._arrow()

    def log_ai_6_start(self, data_sources: str = ""):
        """[6] 霊視記憶參考（與 [2]~[5] 同屬五大 AI 層，編號延續）"""
        default_src = "霊視記憶 DB（本地）、圖表候選（步驟 2）；LLM 摘要/洞察（四角）"
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            "分析：類似案例、執行率、洞察摘要",
        ]
        self._box("  [6] 霊視記憶參考", body)
        self._arrow()

    def log_ai_6_result(self, insight_count: int = 0):
        self._box("  [6] 霊視記憶參考 — 結果", [f"產出：{insight_count} 條洞察、歷史摘要"])
        self._arrow()

    # ---------- 第二層防護：LLM 防幻覺 ----------
    def log_layer2_start(self, data_sources: str = ""):
        """第二層防護：決策引擎內建防幻覺；LLM 每階段會輸出「LLM 正在：第 X/Y 階段…」"""
        default_src = "防幻覺模組（Scitely/Cohere/Mistral/OpenRouter）、步驟 1～6 分析結果"
        self._out("")
        body = [
            "本步驟數據來源：  " + (data_sources or default_src),
            "流程：組裝 prompt → 防幻覺包裝 → 自我質疑／多輪 LLM → 解析決策 JSON",
            "LLM 活動：下方會依序輸出「LLM 正在：第 X/Y 階段 …」及使用之 provider",
        ]
        self._box("【第二層防護】LLM 防幻覺（決策引擎內）", body)
        self._arrow()

    def log_layer2_llm_phase(self, phase: int, total: int, message: str, provider: Optional[str] = None):
        """決策引擎內 LLM 正在做什麼（每階段都會輸出）"""
        if provider:
            self._out(f"  {_BOX_MID} LLM 正在：第 {phase}/{total} 階段「{message}」— 完成，使用：{provider}")
        else:
            self._out(f"  {_BOX_MID} LLM 正在：第 {phase}/{total} 階段「{message}」…")

    def log_llm_doing(self, step_label: str, message: str, provider: Optional[str] = None):
        """任意步驟的 LLM 活動（供其他模組呼叫，方便追蹤 app 運行）"""
        if provider:
            self._out(f"  {_BOX_MID} [{step_label}] LLM 正在：{message} — 使用：{provider}")
        else:
            self._out(f"  {_BOX_MID} [{step_label}] LLM 正在：{message} …")

    def log_layer2_result(self, action_count: int, actions_summary: Optional[str] = None):
        body = [f"解析出的行動數：{action_count}"]
        if actions_summary:
            body.append(actions_summary[:60] + ("..." if len(actions_summary) > 60 else ""))
        self._box("【第二層防護】決策引擎 — 結果", body)
        self._arrow()

    # ---------- 輸出驗證與最終審計 ----------
    def log_validation_start(self):
        self._box("【輸出驗證】邏輯與數字檢查", ["驗證決策格式、倉位與風險欄位"])
        self._arrow()

    def log_audit_start(self):
        self._box("【最終審計】最後一道檢查", ["審計員檢查、不代為判斷"])
        self._arrow()

    # ---------- 報告 ----------
    def log_report_start(self, report_path: str = ""):
        # #region agent log
        try:
            import time
            import json
            _p = report_path or ""
            _data = {"len": len(_p), "path_pre": _p[:30], "path_suffix": _p[-30:] if len(_p) > 30 else _p}
            with open("/Users/lautinyam/stock_scanner/.cursor/debug.log", "a", encoding="utf-8") as _dbg:
                _dbg.write(json.dumps({"hypothesisId": "H3", "message": "report_path", "data": _data, "timestamp": int(time.time() * 1000)}, ensure_ascii=False) + "\n")
        except Exception:
            pass
        # #endregion
        body = ["生成每日報告、寫入檔案"]
        if report_path:
            # Box width 70 → content ~66 chars; show short path to avoid truncation
            _w = 62
            if len(report_path) > _w:
                import os
                _tail = os.path.basename(report_path.rstrip("/")) or report_path.split("/")[-1] or report_path
                body.append(f"路徑：.../{_tail}")
            else:
                body.append(f"路徑：{report_path}")
        self._box("【報告】", body)
        self._out("")

    def log_flow_end(self):
        """流程結束"""
        self._out("  " + _LINE_H * 32 + " 流程結束 " + _LINE_H * 32)
        self._out("")
