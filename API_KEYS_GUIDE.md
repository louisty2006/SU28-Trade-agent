# 🔑 API Keys 快速註冊指南

## 🎯 推薦註冊順序

### 階段 1：最小可用配置（5 分鐘）

註冊這 2 個就能開始：

#### 1️⃣ IEX Cloud ⭐⭐⭐⭐⭐
**為什麼優先**：額度超大（1,666/天），可靠性極高

**註冊步驟**：
1. 訪問：https://iexcloud.io/
2. 點擊「Start Free」
3. 填寫 Email、密碼
4. 驗證 Email
5. 進入 Dashboard → API Tokens → 複製「Publishable Token」

**獲得額度**：50,000 calls/月 (≈ 1,666/天)

---

#### 2️⃣ Twelve Data ⭐⭐⭐⭐
**為什麼選它**：800/天，註冊簡單

**註冊步驟**：
1. 訪問：https://twelvedata.com/
2. 點擊「Get API Key」
3. 填寫資料
4. 驗證 Email
5. Dashboard → API Key

**獲得額度**：800 calls/天

---

✅ **完成！** 現在您有：
- Yahoo Finance（無限）
- IEX Cloud（1,666/天）
- Twelve Data（800/天）

**總計：2,466 calls/天** → 可處理 1,200+ 支股票

---

### 階段 2：標準配置（再 10 分鐘）

想要更穩定？再註冊這 3 個：

#### 3️⃣ Tiingo ⭐⭐⭐⭐

**註冊步驟**：
1. 訪問：https://www.tiingo.com/
2. 點擊「Sign Up」
3. 填寫資料
4. Account → API → 複製 Token

**獲得額度**：500 calls/天

---

#### 4️⃣ Finnhub ⭐⭐⭐⭐

**註冊步驟**：
1. 訪問：https://finnhub.io/
2. 點擊「Get free API key」
3. 填寫資料
4. Dashboard → 複製 API Key

**獲得額度**：60 calls/分鐘 (≈ 1,440/天)

---

#### 5️⃣ Financial Modeling Prep (FMP) ⭐⭐⭐⭐

**註冊步驟**：
1. 訪問：https://site.financialmodeprep.com/developer/docs/
2. 點擊「Get your Free API Key」
3. 填寫資料
4. Dashboard → 複製 API Key

**獲得額度**：250 calls/天

---

✅ **完成！** 現在您有 5 個數據源

**總計：4,406 calls/天** → 可處理 2,200+ 支股票（非常充裕）

---

### 階段 3：完整配置（可選，再 20 分鐘）

追求極致穩定？再註冊這些：

#### 6️⃣ Intrinio
- 網址：https://intrinio.com/
- 額度：500 calls/天

#### 7️⃣ Polygon.io
- 網址：https://polygon.io/
- 額度：250 calls/天

#### 8️⃣ Quandl/NASDAQ Data Link
- 網址：https://data.nasdaq.com/
- 額度：50 calls/天

#### 9️⃣ Alpha Vantage
- 網址：https://www.alphavantage.co/
- 額度：25 calls/天

#### 🔟 Marketstack
- 網址：https://marketstack.com/
- 額度：100 calls/月

---

## 📝 填入 .env 文件

註冊完成後，把 API Keys 填入 `.env` 文件：

```bash
# 複製範例文件
cp .env.example .env

# 編輯 .env
nano .env  # 或用任何文字編輯器
```

填入格式：

```bash
# 最小配置
IEX_CLOUD_API_KEY=pk_xxxxxxxxxxxxxxxxxxxxxxxx
TWELVE_DATA_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx

# 標準配置（再加這 3 個）
TIINGO_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
FINNHUB_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
FMP_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx

# 完整配置（再加這些）
INTRINIO_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
POLYGON_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
# ... 以此類推
```

---

## ✅ 驗證配置

執行測試腳本檢查：

```bash
python test.py
```

系統會自動檢測您啟用了哪些數據源，並顯示預估處理能力。

---

## 🎯 推薦方案

### 新手用戶
**註冊 2 個**：IEX + Twelve  
**預估時間**：5 分鐘  
**處理能力**：1,200+ 支  

### 一般用戶
**註冊 5 個**：IEX + Twelve + Tiingo + Finnhub + FMP  
**預估時間**：15 分鐘  
**處理能力**：2,200+ 支  

### 專業用戶
**註冊全部**：11 個數據源  
**預估時間**：35 分鐘  
**處理能力**：2,700+ 支  

---

## 💡 小提示

1. **Email 驗證**：註冊後記得驗證 Email
2. **API Key 保密**：不要分享您的 API Keys
3. **額度監控**：系統會自動追蹤並顯示剩餘額度
4. **免費額度**：所有推薦的都是免費版，無需信用卡

---

## 🆘 常見問題

### Q: 一定要註冊這麼多嗎？
A: 不用！最少 2 個（IEX + Twelve）就夠用了。

### Q: 註冊需要信用卡嗎？
A: 不需要！推薦的都是真正免費的。

### Q: API Key 會過期嗎？
A: 免費版通常不會過期，但建議定期檢查。

### Q: 忘記 API Key 怎麼辦？
A: 登入各平台的 Dashboard 就能查看。

---

## 🚀 開始註冊

選擇您的方案，開始註冊吧！

**推薦從階段 1 開始**，只需 5 分鐘，就能開始使用系統了！
