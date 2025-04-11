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
    message_text = event["message"]["text"].strip()
    
    # 使用整合後的關鍵字搜尋
    campsites = Campsite.search_by_keywords(message_text)
    current_page = 1

    if not campsites:
        send_line_message(
            event["replyToken"],
            [{"type": "text", "text": """抱歉，找不到符合的營區。
請試試其他關鍵字！

您可以：
1. 輸入區域搜尋（北部、中部、南部、東部）
2. 結合區域和其他條件，例如：
   - 中部 海拔高
   - 北部 可帶寵物
   - 南部 wifi
3. 或直接搜尋特定地點，例如：
   - 苗栗 海拔高
   - 宜蘭 寵物可"""}],
        )
        return

    return handle_search_results(event["replyToken"], campsites, current_page, message_text)

def handle_postback(event, Campsite):
    """處理 postback 事件"""
    try:
        data = json.loads(event["postback"]["data"])
        if data.get("action") == "next_page":
            current_page = data.get("page", 1)
            keyword = data.get("keyword", "")
            campsites = Campsite.search_by_keywords(keyword)
            return handle_search_results(event["replyToken"], campsites, current_page, keyword)
    except Exception as e:
        logger.error(f"處理 postback 時發生錯誤: {str(e)}")
        send_line_message(
            event["replyToken"],
            [{"type": "text", "text": "抱歉，處理您的請求時發生錯誤。請重新搜尋。"}],
        )

def handle_search_results(reply_token, campsites, current_page, keyword):
    """處理搜尋結果的顯示邏輯"""
    # 計算分頁資訊
    total_pages = (len(campsites) + 9) // 10
    start_idx = (current_page - 1) * 10
    end_idx = min(start_idx + 10, len(campsites))
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
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xl",
                "paddingAll": "xl",
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": camp["name"],
                        "weight": "bold",
                        "size": "xxl",
                        "wrap": True,
                        "color": "#1D7D81"
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
                                        "text": f"通訊：{camp.get('signal_strength', '未知').replace('有訊號', '').strip()}",
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
                "spacing": "sm",
                "paddingAll": "xl",
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

    # 如果還有下一頁，加入分頁按鈕
    if current_page < total_pages:
        next_page_bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "position": "relative",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "position": "absolute",
                        "offsetTop": "40%",
                        "width": "100%",
                        "contents": [
                            {
                                "type": "text",
                                "text": "更多營區",
                                "size": "xl",
                                "weight": "bold",
                                "align": "center",
                                "color": "#1D7D81"
                            },
                            {
                                "type": "text",
                                "text": f"第 {current_page} 頁，共 {total_pages} 頁",
                                "size": "md",
                                "align": "center",
                                "color": "#666666",
                                "margin": "lg"
                            }
                        ]
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "position": "absolute",
                        "offsetTop": "70%",
                        "width": "100%",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": "下一頁",
                                    "data": json.dumps({
                                        "action": "next_page",
                                        "page": current_page + 1,
                                        "keyword": keyword
                                    }),
                                    "displayText": "查看更多營區"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        bubbles.append(next_page_bubble)

    carousel = {
        "type": "carousel",
        "contents": bubbles
    }

    flex_message = {
        "type": "flex",
        "altText": "營區搜尋結果",
        "contents": carousel
    }

    send_line_message(reply_token, [flex_message])
