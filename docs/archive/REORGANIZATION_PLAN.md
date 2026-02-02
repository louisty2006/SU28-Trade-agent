# 文件整理方案

## 📊 当前状况
- **21个 Markdown 文档** - 部分重复/过时
- **4个 Python 模块文件夹** - 结构良好
- **1个备份文件夹** - 可以归档
- **临时文件** - 需要清理

---

## 🎯 整理计划

### 1. 创建 docs/ 文档中心
```
docs/
├── changelogs/      # 所有版本更新日志
├── guides/          # 用户指南
├── development/     # 开发文档
└── archive/         # 归档文档
```

### 2. 保留在根目录的文件
- `README.md` - 主要入口
- `.gitignore`
- `.env.example`
- `requirements.txt`
- `config.py`
- `config.json.example`
- `config.yaml.example`

### 3. 要移动的文档

#### → docs/changelogs/
- `CHANGELOG_4.3.md`
- `CHANGELOG_V4.2_TO_V4.3.md`
- `CHANGELOG_V5.0.md`
- `CHANGELOG_V5.0.1.md`
- `__REISHI____v4.3_____changelog.md` (删除，重复)

#### → docs/guides/
- `QUICKSTART.md` → `quickstart_v4.md`
- `QUICKSTART_V5.md` → `quickstart_v5.md`
- `USAGE.md`
- `API_KEYS_GUIDE.md`
- `ORCHESTRATOR_INTEGRATION.md`
- `V5.0_BACKTEST_GUIDE.md`
- `backtest_usage.md`

#### → docs/development/
- `PROJECT_SUMMARY.md`
- `V5.0_ROADMAP.md`
- `DATA_SOURCES.md`
- `BRAND.md`

#### → docs/archive/
- `RECENT_CHANGES.md` (已过时)
- `UPDATE_SUMMARY.md` (已整合到CHANGELOG)
- `V5.0_DEPLOYMENT_SUMMARY.md` (临时文档)
- `V5.0.1_SUMMARY.md` (临时文档)
- `WELCOME_BACK.md` (临时文档)

### 4. 保留在根目录（作为主入口）
- `V5.0_README.md` → 保留，重要

### 5. 备份文件夹重命名
- `backup_v41/` → `archive/v4.1_backup/`

### 6. 要删除的文件
- `backtest_usage.pdf` (已有 .md 版本)
- `Stock Scanner v4.2 完整更新報告.pdf` (已过时)
- `test.py` (临时测试文件)
- `__REISHI____v4.3_____changelog.md` (重复)

### 7. 临时脚本移到 scripts/
- `backtest_from_plan.py`
- `trade_plan_from_plan.py`
- `data/build_universe_from_complete.py`
- `data/get_all_8167_stocks.py`

---

## ✅ 执行顺序
1. 创建新文件夹结构
2. 移动文档到对应位置
3. 删除重复/过时文件
4. 更新 .gitignore
5. 提交到 Git

---

是否立即执行？
