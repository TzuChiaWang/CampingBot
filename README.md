# CampingBot 露營資訊 LINE 機器人

這是一個基於 LINE Messaging API 開發的露營資訊查詢機器人，提供智能營地搜尋、照片瀏覽等功能。

## 功能特點

- 🔍 智能搜尋功能
  - 關鍵字搜尋（如：螢火蟲、日出等）
  - 智能篩選系統
  - 分頁瀏覽功能

- 🏕️ 營地資訊顯示
  - 營地名稱與照片
  - 地理位置與海拔
  - 停車與設施資訊
  - 社群連結與更多照片

- 📱 優化使用者體驗
  - 美觀的 Flex Message 卡片
  - 輪播式照片展示
  - 分頁導覽按鈕
  - 智能篩選介面

- 💾 資料庫整合
  - MongoDB 資料儲存
  - 營地資訊管理
  - 照片 URL 管理
  - 關鍵字索引優化

## 使用方式

1. 加入好友：
   - 掃描 QR Code 或搜尋 LINE ID 加入好友

2. 開始使用：
   - 輸入關鍵字搜尋營地（例如：「螢火蟲」、「雲海」）
   - 使用篩選功能縮小搜尋範圍
   - 點擊「下一頁」瀏覽更多結果
   - 點擊「查看更多照片」連結至社群媒體

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
- 複製 `.env.example` 到 `.env`
- 填入必要的環境變數：
  - LINE Bot 設定
  - MongoDB 連接資訊
  - Flask 設定
  - Ngrok URL（開發時使用）

```bash
cp .env.example .env
# 編輯 .env 文件填入相關設定
```

## 環境變數說明

- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Bot 的 Channel Access Token
- `LINE_CHANNEL_SECRET`: LINE Bot 的 Channel Secret
- `MONGODB_URI`: MongoDB 連接字串
- `MONGODB_DB`: MongoDB 資料庫名稱
- `MONGODB_COLLECTION`: MongoDB 集合名稱
- `FLASK_SECRET_KEY`: Flask 應用的密鑰
- `NGROK_URL`: Ngrok 的 URL（開發環境使用）

## 開發環境設置

1. 安裝 ngrok（用於開發測試）
2. 啟動 Flask 應用
```bash
python app.py
```
3. 啟動 ngrok
```bash
ngrok http 3000
```
4. 將 ngrok 提供的 URL 設定到 LINE Developer Console

## 專案結構

```
CampingBot/
├── app.py              # 主應用程式
├── line_bot.py         # LINE Bot 邏輯處理
├── models.py           # 資料模型與資料庫操作
├── scraper.py         # 資料爬蟲
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
- Beautiful Soup（網頁爬蟲）

## 注意事項

- 請確保 `.env` 檔案中的敏感資訊不會被提交到版本控制系統
- 開發時請使用自己的 LINE Bot Channel 和 MongoDB 資料庫
- 建議在虛擬環境中開發

## 最新更新

- 新增分頁功能，支援大量搜尋結果的瀏覽
- 優化 UI/UX 設計，提供更直觀的使用體驗
- 改進搜尋功能，支援更多關鍵字
- 增加營地資訊的顯示內容