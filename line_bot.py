import os
import json
import hmac
import base64
import hashlib
import logging
import requests
from flask import abort
from dotenv import load_dotenv

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

# LINE API 設定
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    logger.error("未設置 LINE API 認證資訊")
    raise ValueError(
        "請在 .env 文件中設置 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET"
    )

def verify_signature(request_body, signature):
    """驗證 LINE 訊息的簽名"""
    channel_secret = CHANNEL_SECRET.encode("utf-8")
    hash = hmac.new(channel_secret, request_body, hashlib.sha256).digest()
    calculated_signature = base64.b64encode(hash).decode("utf-8")
    return hmac.compare_digest(calculated_signature, signature)

def send_line_message(reply_token, messages):
    """發送 LINE 訊息"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    }
    data = {
        "replyToken": reply_token,
        "messages": messages if isinstance(messages, list) else [messages],
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # 如果狀態碼不是 200，會拋出異常
        logger.info(f"LINE API Response: {response.status_code} - {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"發送 LINE 訊息時發生錯誤: {str(e)}")
        return False

def handle_message(event, Campsite):
    """處理收到的訊息"""
    try:
        text = event["message"]["text"].strip()
        reply_token = event["replyToken"]
        logger.info(f"收到訊息: {text}")

        # 測試回覆
        if text == "test":
            success = send_line_message(
                reply_token, {"type": "text", "text": "測試成功！機器人正常運作中。"}
            )
            if not success:
                logger.error("發送測試訊息失敗")
            return

        # 搜尋營區
        campsites = Campsite.search_by_keywords(text)

        if not campsites:
            success = send_line_message(
                reply_token,
                {
                    "type": "text",
                    "text": "抱歉，找不到符合條件的營區。請嘗試其他關鍵字，例如：海景、森林、親子等。",
                },
            )
            if not success:
                logger.error("發送無結果訊息失敗")
            return

        # 取第一個符合的營區
        camp = campsites[0]
        logger.info(f"找到營區: {camp['name']}, ID: {camp['_id']}")

        # 建立 Flex Message
        if not camp.get("image_urls"):
            success = send_line_message(
                reply_token,
                {
                    "type": "text",
                    "text": f"找到營區：{camp['name']}\n很抱歉，目前沒有照片。",
                },
            )
            if not success:
                logger.error("發送無圖片訊息失敗")
            return

        bubbles = []

        # 第一個 bubble 顯示第一張照片和營區資訊
        first_bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": camp["image_urls"][0],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xl",
                "contents": [
                    {
                        "type": "text",
                        "text": camp["name"],
                        "weight": "bold",
                        "size": "xl",
                        "wrap": True,
                        "color": "#000000",
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "xl",
                        "spacing": "lg",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "md",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "📍",
                                        "size": "sm",
                                        "color": "#000000",
                                    },
                                    {
                                        "type": "text",
                                        "text": camp.get("location", "未知"),
                                        "wrap": True,
                                        "color": "#000000",
                                        "size": "sm",
                                        "flex": 5,
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "⛰️",
                                        "size": "sm",
                                        "color": "#000000",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"海拔：{camp.get('altitude', '未知')}",
                                        "wrap": True,
                                        "color": "#000000",
                                        "size": "sm",
                                        "flex": 5,
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "✨",
                                        "size": "sm",
                                        "color": "#000000",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"特色：{camp.get('features', '未知')}",
                                        "wrap": True,
                                        "color": "#000000",
                                        "size": "sm",
                                        "flex": 5,
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "📱",
                                        "size": "sm",
                                        "color": "#000000",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"通訊：{camp.get('signal_strength', '未知')}",
                                        "wrap": True,
                                        "color": "#000000",
                                        "size": "sm",
                                        "flex": 5,
                                    },
                                ],
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "🐕",
                                        "size": "sm",
                                        "color": "#000000",
                                    },
                                    {
                                        "type": "text",
                                        "text": f"寵物：{camp.get('pets', '未知')}",
                                        "wrap": True,
                                        "color": "#000000",
                                        "size": "sm",
                                        "flex": 5,
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "立即預訂",
                            "uri": camp.get("booking_url", ""),
                        },
                        "color": "#1D7D81",
                        "margin": "lg",
                    }
                ],
            },
        }

        bubbles.append(first_bubble)

        flex_message = {
            "type": "flex",
            "altText": f"營區：{camp['name']}",
            "contents": {"type": "carousel", "contents": bubbles},
        }

        logger.info(f"準備發送的 Flex Message: {json.dumps(flex_message)}")

        # 發送 Flex Message
        success = send_line_message(reply_token, flex_message)
        if success:
            logger.info("Flex Message 發送成功")
        else:
            logger.error("Flex Message 發送失敗")
            # 嘗試發送簡單文字訊息作為備用
            reply_error = send_line_message(
                reply_token,
                {
                    "type": "text",
                    "text": f"找到營區：{camp['name']}\n地址：{camp.get('location', '未知')}\n預訂連結：{camp.get('booking_url', '')}",
                },
            )
            if not reply_error:
                logger.error(f"發送錯誤訊息失敗: {str(reply_error)}")

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        try:
            send_line_message(
                reply_token,
                {"type": "text", "text": "抱歉，處理您的訊息時發生錯誤。請稍後再試。"},
            )
        except Exception as reply_error:
            logger.error(f"發送錯誤訊息失敗: {str(reply_error)}")
