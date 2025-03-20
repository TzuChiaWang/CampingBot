# CampingBot 露營資訊 LINE 機器人

這是一個基於 LINE Messaging API 開發的露營資訊查詢機器人，提供營地資訊查詢、照片瀏覽等功能。

## 功能特點

- 🏕️ 營地資訊查詢
  - 營地名稱
  - 地理位置
  - 海拔高度
  - 營地照片

- 📱 LINE 介面整合
  - 互動式選單
  - Flex Message 訊息卡片
  - 多圖片展示
  - 更多照片瀏覽功能

- 💾 資料庫整合
  - MongoDB 資料儲存
  - 營地資訊管理
  - 照片 URL 管理

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
├── forms.py            # 表單定義
├── models.py           # 資料模型
├── templates/          # HTML 模板
│   ├── base.html
│   ├── index.html
│   └── view_photos.html
├── requirements.txt    # 依賴套件
└── .env.example       # 環境變數範例
```

## 使用技術

- Python
- Flask
- LINE Messaging API
- MongoDB
- Bootstrap
- Jinja2 Templates

## 注意事項

- 請確保 `.env` 檔案中的敏感資訊不會被提交到版本控制系統
- 開發時請使用自己的 LINE Bot Channel 和 MongoDB 資料庫
- 建議在虛擬環境中開發