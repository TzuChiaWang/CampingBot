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
        logger.info(f"準備發送的訊息: {json.dumps(data, ensure_ascii=False)}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # 如果狀態碼不是 200，會拋出異常
        logger.info(f"LINE API Response: {response.status_code} - {response.text}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"發送 LINE 訊息時發生錯誤: {str(e)}")
        if hasattr(e.response, 'text'):
            logger.error(f"錯誤詳情: {e.response.text}")
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

        # 計算總頁數（每頁10個營區）
        total_pages = (len(campsites) + 9) // 10
        current_page = 1
        start_idx = 0
        end_idx = min(10, len(campsites))
        current_campsites = campsites[start_idx:end_idx]

        # 建立 Flex Message
        bubbles = []
        for camp in current_campsites:
            if not camp.get("image_urls"):
                continue

            # 建立營區資訊 bubble
            bubble = {
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
                            "size": "xxl",
                            "wrap": True,
                            "color": "#1D7D81",
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
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": camp.get("location", "未知"),
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "bold",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "⛰️",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"海拔：{camp.get('altitude', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "✨",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"特色：{camp.get('features', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "🏕️",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"設施：{camp.get('facilities', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "📱",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"通訊：{camp.get('signal_strength', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "🐕",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"寵物：{camp.get('pets', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
                                            "flex": 5,
                                        },
                                    ],
                                },
                                {
                                    "type": "box",
                                    "layout": "baseline",
                                    "spacing": "md",
                                    "contents": [
                                        {
                                            "type": "text",
                                            "text": "🅿️",
                                            "size": "md",
                                            "color": "#000000",
                                        },
                                        {
                                            "type": "text",
                                            "text": f"停車：{camp.get('parking', '未知')}",
                                            "wrap": True,
                                            "color": "#666666",
                                            "size": "md",
                                            "weight": "regular",
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
                            "color": "#1D7D81",
                            "margin": "lg",
                            "action": {
                                "type": "uri",
                                "label": "立即預訂",
                                "uri": camp.get("booking_url", "https://www.easycamp.com.tw"),
                            },
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "margin": "lg",
                            "action": {
                                "type": "uri",
                                "label": "在 Google Map 中查看",
                                "uri": f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(camp['name'])}",
                            },
                        }
                    ],
                },
            }

            # 如果有社群連結，才加入查看更多照片按鈕
            if camp.get("social_url"):
                bubble["footer"]["contents"].append({
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "margin": "lg",
                    "action": {
                        "type": "uri",
                        "label": "查看更多照片",
                        "uri": camp["social_url"],
                    },
                })

            bubbles.append(bubble)

        messages = []
        # 發送輪播訊息
        if bubbles:
            carousel = {
                "type": "flex",
                "altText": f"找到 {len(campsites)} 個相關營區",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
            messages.append(carousel)

            # 如果還有更多結果，發送提示訊息
            if total_pages > 1:
                remaining = len(campsites) - end_idx
                text_message = {
                    "type": "text",
                    "text": f"以上是第 {current_page}/{total_pages} 頁的搜尋結果，還有 {remaining} 個營區。\n請輸入相同關鍵字以查看更多結果。"
                }
                messages.append(text_message)

            # 發送所有訊息
            success = send_line_message(reply_token, messages)
            if not success:
                logger.error("發送營區資訊失敗")
        else:
            success = send_line_message(
                reply_token,
                {
                    "type": "text",
                    "text": "抱歉，找到的營區沒有照片資訊。請嘗試其他關鍵字。",
                },
            )
            if not success:
                logger.error("發送無照片訊息失敗")

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        error_message = {
            "type": "text",
            "text": "抱歉，處理您的訊息時發生錯誤。請稍後再試。",
        }
        send_line_message(reply_token, error_message)
