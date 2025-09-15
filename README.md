# 回憶露-露營資訊平台

這是一個多平台的露營資訊查詢系統，同時提供網頁介面和 LINE 機器人服務：

- 💻 網頁平台：提供完整的營地搜尋、篩選和預訂功能
- 📱 LINE 機器人：隨時隨地快速查詢營地資訊

## 功能特點

- 🌐 雙平台整合

  - 網頁介面支援詳細營地瀏覽和進階搜尋
  - LINE 機器人提供互動式選單搜尋
  - 資料同步更新，體驗一致

- 🔍 智能搜尋系統

  - 網頁平台：關鍵字快速搜尋
  - LINE 機器人：
    - 互動式地區選擇（北中南東）
    - 縣市篩選功能
    - 海拔高度選擇
    - 特色功能篩選（寵物、停車等）

- 🏕️ 營地資訊顯示

  - 營地名稱與精選照片
  - 地理位置與海拔資訊
  - 停車與設施介紹
  - 立即預訂按鈕
  - 更多照片瀏覽功能

- 📱 優化使用者體驗

  - 美觀的 Flex Message 卡片
  - 輪播式營地展示
  - 智能篩選介面
  - 一鍵預訂功能

- 💾 資料庫整合
  - MongoDB 資料儲存
  - 完整營地資訊管理
  - 照片庫管理
  - 關鍵字搜尋優化

## 使用方式

1. 網頁平台：

   - 瀏覽首頁查看所有營地
   - 使用搜尋欄位輸入關鍵字
   - 點擊營地卡片查看詳細資訊
   - 使用預訂按鈕聯繫營地

2. LINE 機器人：
   - 掃描 QR Code 或搜尋 LINE ID 加入好友
   - 透過互動式選單尋找理想營地：
     - 選擇想要的地區（北中南東）
     - 選擇特定縣市
     - 選擇海拔高度
     - 選擇特色功能（如寵物、停車需求）
   - 瀏覽搜尋結果，每個營地提供：
     - 立即預訂功能
     - Google Map 位置查看

## 安裝說明

1. 克隆專案

```bash
git clone https://github.com/TzuChiaWang/CampingBot.git
cd CampingBot
```

2. 安裝依賴

```bash
pip install -r requirements.txt
```

3. 環境設定

- 到 `.env` 並填入必要的 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 與 MONGODB 環境變數

## 專案結構

```
CampingBot/
├── app.py              # 主應用程式
├── line_bot.py         # LINE Bot 邏輯處理
├── models.py           # 資料模型與資料庫操作
├── scraper.py          # 資料爬蟲
├── requirements.txt    # 依賴套件
└── .env.example       # 環境變數範例
```

## 使用技術

- Python 3.8+
- LINE Messaging API
  - Flex Message
  - Postback Events
  - Carousel Messages
- Flask Web Framework
- MongoDB

## 注意事項

- 請確保 `.env` 檔案中的敏感資訊不會被提交到版本控制系統
- 開發時請使用自己的 LINE Bot Channel 和 MongoDB 資料庫
- 建議在虛擬環境中開發

## 最新更新

- 優化搜尋結果顯示邏輯，根據結果數量自動調整顯示方式
- 新增智能篩選系統，支援地區、海拔和特色篩選
- 改進營地資訊卡片設計，新增立即預訂功能
- 優化照片瀏覽體驗，支援更多照片的查看
