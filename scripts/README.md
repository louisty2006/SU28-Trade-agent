# 🔧 REISHI 霊視 - 工具脚本

这个文件夹包含各种工具和辅助脚本。

---

## 📋 脚本列表

### 数据处理
- **`build_universe_from_complete.py`** - 从完整股票列表构建交易宇宙
- **`get_all_8167_stocks.py`** - 获取完整的股票列表（8167支）

### 交易辅助
- **`backtest_from_plan.py`** - 从交易计划生成回测
- **`trade_plan_from_scan.py`** - 从扫描结果生成交易计划

---

## 🚀 使用方法

### 构建股票池
```bash
cd scripts
python build_universe_from_complete.py
```

### 获取完整股票列表
```bash
cd scripts
python get_all_8167_stocks.py
```

---

## ⚠️ 注意事项

这些脚本主要用于：
- 数据预处理
- 一次性任务
- 开发辅助

**不建议在生产环境中直接使用，请先在测试环境验证。**

---

**最后更新**：2026-02-02
