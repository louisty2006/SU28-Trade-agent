# REISHI 終端機流程擇要說明

執行每日分析或回測時，每個步驟會在 terminal 輸出 **流程擇要、判斷基準與關鍵數據**，方便肉眼追蹤與除錯。

---

## 統一前綴

所有新增的流程擇要均以 **`[REISHI]`** 開頭，方便過濾。

---

## 快速查看

```bash
# 只看流程擇要與判斷基準
python main_v5.py 2>&1 | grep '\[REISHI\]'

# 或執行後從 log 篩選（若已重導向）
tail -f REIKAN_steps.log
```

---

## 輸出位置一覽

| 檔案 | 位置 | 內容 |
|------|------|------|
| **main_v5.py** | run_daily() 步驟 1～9 | 每步開始：`[REISHI] [步驟N] 判斷基準：…`；每步結束：`[REISHI] 擇要：…`（有效數、前5檔等） |
| **main_v5.py** | run_daily_for_backtest() | 當 `silent=False` 時，各回測步驟前後輸出 `[REISHI] [回測步驟N]` 與擇要 |
| **analysis/fundamental_analysis.py** | analyze_batch 開始/結束 | ticker 數、as_of_date；成功數、前3檔 summary_text 擇要 |
| **analysis/sentiment_analysis.py** | analyze_batch 結束 | 檔數、有新聞數、前5檔 score |
| **analysis/multi_agent.py** | analyze_all 結束 | 候選數、前5檔共識 action |
| **core/decision_engine.py** | decide() 內 | 送給 LLM 的摘要長度與前 300 字預覽；解析完成後 actions 數與前3筆 |

---

## 步驟與判斷基準對照（每日分析）

1. **數據獲取與驗證**：Yahoo/多數據源 K 線；僅美股/港股；數據源依 config  
2. **基本面分析**：get_yahoo_info / get_yahoo_financials_as_of；PE/PB/ROE/營收與盈利成長  
3. **圖表型態識別**：收盤≥20日高 0.98 視為突破；成交量/均線未檢核  
4. **因果推理**：Finnhub 新聞 + 持倉；LLM 因果鏈（四角）  
5. **情緒分析**：新聞內容→LLM；score(-1~1)/key_factors/risks；無新聞或失敗→中性  
6. **Multi-Agent**：三角色 + 單輪共識；consensus_action / disagreements / final_recommendation  
7. **霊視記憶**：霊視記憶 DB + 圖表候選；LLM 摘要/洞察  
8. **決策引擎**：三大原則 + AllAnalyses 摘要→防幻覺 LLM→解析 actions  
9. **驗證與審計**：output_validator 邏輯/數字；final_auditor 審計  
