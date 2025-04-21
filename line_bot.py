import os
import json
import hmac
import base64
import hashlib
import logging
import requests
from flask import abort
from dotenv import load_dotenv
from typing import Dict, Any

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

# 用戶搜尋狀態管理
user_states: Dict[str, Dict[str, Any]] = {}

# 定義各區域的縣市
REGION_CITIES = {
    "北部": ["台北", "新北", "基隆", "新竹", "桃園", "宜蘭"],
    "中部": ["台中", "苗栗", "彰化", "南投", "雲林"],
    "南部": ["高雄", "台南", "嘉義", "屏東", "澎湖"],
    "東部": ["花蓮", "台東"]
}

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

def create_location_selection():
    """創建地區選擇介面"""
    region_display = {
        "北部": "我想去北部露營！",
        "中部": "去中部享受大自然！",
        "南部": "南部陽光真好！",
        "東部": "看東部的海！"
    }
    return {
        "type": "flex",
        "altText": "請選擇地區",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.pinimg.com/736x/4a/4c/74/4a4c7402eadeaf088689a4123d2458b0.jpg",  
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "您想去哪放鬆呢",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f5f5f5",
                                "cornerRadius": "lg",
                                "paddingAll": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "action": {
                                            "type": "postback",
                                            "label": region,
                                            "data": json.dumps({
                                                "action": "select_region",
                                                "region": region
                                            }),
                                            "displayText": region_display[region]
                                        },
                                        "style": "link",
                                        "color": "#905c44",
                                        "height": "sm"
                                    }
                                ]
                            } for region in ["北部", "中部", "南部", "東部"]
                        ]
                    }
                ]
            }
        }
    }

def create_city_selection(region):
    """創建縣市選擇介面"""
    region_images = {
        "北部": "https://i.pinimg.com/736x/90/e5/c3/90e5c33650b6d47d4d1684e647aa360c.jpg",  
        "中部": "https://i.pinimg.com/1200x/c2/76/11/c276110d1c0ffca4f65c1d7550b5c666.jpg",  
        "南部": "https://i.pinimg.com/1200x/50/4e/d5/504ed577905484b9f87d12a2d6ac2fe4.jpg",  
        "東部": "https://i.pinimg.com/1200x/ff/9b/94/ff9b947da12a9926e49be5319f66029b.jpg"   
    }
    return {
        "type": "flex",
        "altText": f"請選擇{region}的縣市",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": region_images[region],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": f"偷偷跟我說去{region}哪裡",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f5f5f5",
                                "cornerRadius": "lg",
                                "paddingAll": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "action": {
                                            "type": "postback",
                                            "label": city,
                                            "data": json.dumps({
                                                "action": "select_city",
                                                "city": city
                                            }),
                                            "displayText": city
                                        },
                                        "style": "link",
                                        "color": "#905c44",
                                        "height": "sm"
                                    }
                                ]
                            } for city in REGION_CITIES[region]
                        ]
                    }
                ]
            }
        }
    }

def create_altitude_selection():
    """創建海拔選擇介面"""
    altitude_display = {
        "高海拔": "我想去高山上露營！",
        "低海拔": "平地營地最適合我！",
        "兩者皆可": "海拔高低都可以～"
    }
    return {
        "type": "flex",
        "altText": "請選擇海拔高度",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.pinimg.com/736x/6b/6a/f1/6b6af12461bd255b02733b79915a69e3.jpg",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "選擇海拔高度",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f5f5f5",
                                "cornerRadius": "lg",
                                "paddingAll": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "action": {
                                            "type": "postback",
                                            "label": altitude,
                                            "data": json.dumps({
                                                "action": "select_altitude",
                                                "altitude": altitude
                                            }),
                                            "displayText": altitude_display[altitude]
                                        },
                                        "style": "link",
                                        "color": "#905c44",
                                        "height": "sm"
                                    }
                                ]
                            } for altitude in ["高海拔", "低海拔", "兩者皆可"]
                        ]
                    }
                ]
            }
        }
    }

def create_pet_selection():
    """創建寵物選擇介面"""
    pet_display = {
        "可帶寵物": "我要帶毛小孩一起去！",
        "不可帶寵物": "無法敵擋毛小孩",
        "兩者皆可": "有沒有寵物都可以！"
    }
    return {
        "type": "flex",
        "altText": "請選擇是否可帶寵物",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.pinimg.com/736x/70/c3/7c/70c37c051c0aaff0bf5c96d0057d82aa.jpg",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "希望有毛小孩嗎",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f5f5f5",
                                "cornerRadius": "lg",
                                "paddingAll": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "action": {
                                            "type": "postback",
                                            "label": pet_option,
                                            "data": json.dumps({
                                                "action": "select_pet",
                                                "pet": pet_option
                                            }),
                                            "displayText": pet_display[pet_option]
                                        },
                                        "style": "link",
                                        "color": "#905c44",
                                        "height": "sm"
                                    }
                                ]
                            } for pet_option in ["可帶寵物", "不可帶寵物", "兩者皆可"]
                        ]
                    }
                ]
            }
        }
    }

def create_parking_selection():
    """創建停車選擇介面"""
    parking_display = {
        "車停營位旁": "想把車停在帳篷旁邊！",
        "集中停車": "集中停車也不錯～",
        "兩者皆可": "停車方式都可以！"
    }
    return {
        "type": "flex",
        "altText": "請選擇停車方式",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.pinimg.com/736x/49/ad/ca/49adcaf22616ca09e6fe04e27c4f3fc7.jpg",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "停車方式",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "vertical",
                                "backgroundColor": "#f5f5f5",
                                "cornerRadius": "lg",
                                "paddingAll": "md",
                                "contents": [
                                    {
                                        "type": "button",
                                        "action": {
                                            "type": "postback",
                                            "label": parking_option,
                                            "data": json.dumps({
                                                "action": "select_parking",
                                                "parking": parking_option
                                            }),
                                            "displayText": parking_display[parking_option]
                                        },
                                        "style": "link",
                                        "color": "#905c44",
                                        "height": "sm"
                                    }
                                ]
                            } for parking_option in ["車停營位旁", "集中停車", "兩者皆可"]
                        ]
                    }
                ]
            }
        }
    }

def create_search_button():
    """創建搜索營地按鈕"""
    return {
        "type": "flex",
        "altText": "開始搜尋營地",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "施展魔法吧！",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#f5f5f5",
                        "cornerRadius": "lg",
                        "paddingAll": "md",
                        "contents": [
                            {
                                "type": "button",
                                "action": {
                                    "type": "postback",
                                    "label": "GO！",
                                    "data": json.dumps({
                                        "action": "search_start"
                                    }),
                                    "displayText": "GO！"
                                },
                                "style": "link",
                                "color": "#905c44",
                                "height": "sm"
                            }
                        ]
                    }
                ]
            }
        }
    }

def create_go_button():
    """創建GO按鈕介面"""
    return {
        "type": "flex",
        "altText": "開始搜尋",
        "contents": {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.imgur.com/dGto3z1.jpg",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "contents": [
                    {
                        "type": "text",
                        "text": "開始探索",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": "#905c44"
                    },
                    {
                        "type": "button",
                        "action": {
                            "type": "postback",
                            "label": "搜尋營地",
                            "data": json.dumps({
                                "action": "search_start"
                            }),
                            "displayText": "搜尋營地"
                        },
                        "style": "primary",
                        "color": "#905c44"
                    }
                ]
            }
        }
    }

def safe_get_text(value, field_name=""):
    """安全地獲取文字內容，處理不同的資料類型"""
    if value is None:
        return "未知"
    if isinstance(value, str):
        return value.replace('有訊號', '').strip() if field_name == "signal_strength" else value
    if isinstance(value, (list, tuple)):
        return ", ".join(map(str, value))
    return str(value)

def create_camp_bubble(camp):
    """建立營區資訊 bubble"""
    bubble = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": camp["image_urls"][0] if isinstance(camp.get("image_urls"), list) and camp["image_urls"] else "https://example.com/default.jpg",
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
                    "text": safe_get_text(camp.get("name")),
                    "weight": "bold",
                    "size": "xxl",
                    "wrap": True,
                    "color": "#905c44"
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
                                    "text": f"地點：{safe_get_text(camp.get('location'))}",
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
                                    "text": f"海拔：{safe_get_text(camp.get('altitude'))}",
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
                                    "text": f"特色：{safe_get_text(camp.get('features'))}",
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
                                    "text": f"設施：{safe_get_text(camp.get('facilities'))}",
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
                                    "text": f"通訊：{safe_get_text(camp.get('signal_strength'), 'signal_strength')}",
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
                                    "text": f"寵物：{safe_get_text(camp.get('pets'))}",
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
                                    "text": f"停車：{safe_get_text(camp.get('parking'))}",
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
                    "color": "#905c44",
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
                        "uri": f"https://www.google.com/maps/search/?api=1&query={requests.utils.quote(safe_get_text(camp.get('name')))}",
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

    return bubble

def create_next_page_bubble(current_page, total_pages, keyword):
    """建立下一頁按鈕 bubble"""
    next_page_bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "position": "relative",
            "offsetTop": "40%",
            "width": "100%",
            "contents": [
                {
                    "type": "text",
                    "text": "更多營區",
                    "size": "xl",
                    "weight": "bold",
                    "align": "center",
                    "color": "#905c44"
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
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "xl",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#905c44",
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
    }
    return next_page_bubble

def handle_message(event, Campsite):
    """處理收到的訊息"""
    message_text = event["message"]["text"].strip()
    user_id = event["source"]["userId"]
    
    if message_text == "開始搜尋！":
        # 初始化用戶狀態
        user_states[user_id] = {
            "step": "region",
            "region": None,
            "city": None,
            "altitude": None,
            "pet": None,
            "parking": None
        }
        # 發送地區選擇介面
        send_line_message(event["replyToken"], [create_location_selection()])
        return
    
    # 如果不是開始搜尋指令，使用原有的搜尋邏輯
    campsites = Campsite.search_by_keywords(message_text)
    current_page = 1

    if not campsites:
        send_line_message(
            event["replyToken"],
            [{"type": "text", "text": """❗抱歉，找不到符合的營區。
請試試其他關鍵字🔎

您可以：
1. 點選「開始搜尋！」使用篩選搜尋
2. 或是輸入區域和其他條件📍
例如：
   - 中部 海拔高
   - 北部 可帶寵物"""}],
        )
        return

    return handle_search_results(event["replyToken"], campsites, current_page, message_text)

def handle_postback(event, Campsite):
    """處理 postback 事件"""
    try:
        data = json.loads(event["postback"]["data"])
        user_id = event["source"]["userId"]
        
        if data.get("action") == "next_page":
            try:
                current_page = data.get("page", 1)
                keyword = data.get("keyword", "")
                logger.info(f"處理下一頁請求: 頁碼={current_page}, 關鍵字={keyword}")  # 添加日誌
                
                # 如果關鍵字是空的，返回錯誤訊息
                if not keyword:
                    send_line_message(
                        event["replyToken"],
                        [{"type": "text", "text": "抱歉，無法找到搜尋條件。請重新開始搜尋。"}]
                    )
                    return
                
                # 執行搜尋
                campsites = Campsite.search_by_keywords(keyword)
                
                # 檢查搜尋結果
                if not campsites:
                    send_line_message(
                        event["replyToken"],
                        [{"type": "text", "text": "抱歉，找不到符合條件的營區。請重新搜尋。"}]
                    )
                    return
                
                # 處理搜尋結果
                return handle_search_results(event["replyToken"], campsites, current_page, keyword)
            except Exception as e:
                logger.error(f"處理下一頁時發生錯誤: {str(e)}")
                send_line_message(
                    event["replyToken"],
                    [{"type": "text", "text": "抱歉，顯示更多營區時發生錯誤。請重新搜尋。"}]
                )
                return
            
        # 處理地區選擇
        elif data.get("action") == "select_region":
            region = data.get("region")
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]["region"] = region
            user_states[user_id]["step"] = "city"
            # 發送對應地區的縣市選擇介面
            send_line_message(event["replyToken"], [create_city_selection(region)])
            
        # 處理縣市選擇
        elif data.get("action") == "select_city":
            city = data.get("city")
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]["city"] = city
            user_states[user_id]["step"] = "altitude"
            send_line_message(event["replyToken"], [create_altitude_selection()])
            
        # 處理海拔選擇
        elif data.get("action") == "select_altitude":
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]["altitude"] = data.get("altitude", "兩者皆可")
            user_states[user_id]["step"] = "pet"
            send_line_message(event["replyToken"], [create_pet_selection()])
            
        # 處理寵物選擇
        elif data.get("action") == "select_pet":
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]["pet"] = data.get("pet", "兩者皆可")
            user_states[user_id]["step"] = "parking"
            send_line_message(event["replyToken"], [create_parking_selection()])
            
        # 處理停車選擇
        elif data.get("action") == "select_parking":
            if user_id not in user_states:
                user_states[user_id] = {}
            user_states[user_id]["parking"] = data.get("parking", "兩者皆可")
            user_states[user_id]["step"] = "go"
            send_line_message(event["replyToken"], [create_search_button()])
            
        # 處理搜尋開始
        elif data.get("action") == "search_start":
            state = user_states.get(user_id, {})
            
            # 檢查用戶狀態是否完整
            if (not state or 
                "city" not in state or 
                not state.get("city") or 
                "step" not in state or 
                state.get("step") != "go"):
                # 初始化用戶狀態並顯示地區選擇介面
                user_states[user_id] = {
                    "step": "region",
                    "region": None,
                    "city": None,
                    "altitude": None,
                    "pet": None,
                    "parking": None
                }
                send_line_message(
                    event["replyToken"],
                    [
                        {"type": "text", "text": "讓我們重新開始搜尋吧！🔍\n請先選擇想去的地區："},
                        create_location_selection()
                    ]
                )
                return

            try:
                # 構建搜尋關鍵字
                keywords = []
                
                # 使用選擇的縣市
                city = state.get("city")
                if city:
                    keywords.append(city)
                
                # 處理其他條件
                if state.get("altitude") and state["altitude"] != "兩者皆可":
                    keywords.append(state["altitude"])
                if state.get("pet") and state["pet"] != "兩者皆可":
                    keywords.append(state["pet"])
                if state.get("parking") and state["parking"] != "兩者皆可":
                    keywords.append(state["parking"])
                
                # 執行搜尋
                search_text = " ".join(filter(None, keywords))
                logger.info(f"搜尋條件: {search_text}")  # 添加日誌
                campsites = Campsite.search_by_keywords(search_text)
                logger.info(f"找到 {len(campsites)} 個營區")  # 添加日誌
                
                if not campsites:
                    send_line_message(
                        event["replyToken"],
                        [{
                            "type": "text", 
                            "text": f"抱歉，找不到符合以下條件的營區：\n- 地區：{city}\n" + 
                                   (f"- 海拔：{state['altitude']}\n" if state.get('altitude') and state['altitude'] != '兩者皆可' else "") +
                                   (f"- 寵物：{state['pet']}\n" if state.get('pet') and state['pet'] != '兩者皆可' else "") +
                                   (f"- 停車：{state['parking']}" if state.get('parking') and state['parking'] != '兩者皆可' else "") +
                                   "\n請嘗試放寬搜尋條件。"
                        }]
                    )
                else:
                    # 清除用戶狀態
                    user_states.pop(user_id, None)
                    # 顯示搜尋結果
                    return handle_search_results(event["replyToken"], campsites, 1, search_text)
                    
            except Exception as e:
                logger.error(f"搜尋過程中發生錯誤: {str(e)}")
                send_line_message(
                    event["replyToken"],
                    [{
                        "type": "text", 
                        "text": "抱歉，搜尋過程中發生錯誤。請重新搜尋。"
                    }]
                )
            
    except Exception as e:
        logger.error(f"處理 postback 時發生錯誤: {str(e)}")
        send_line_message(
            event["replyToken"],
            [{"type": "text", "text": "抱歉，處理您的請求時發生錯誤。請重新搜尋。"}]
        )

def handle_search_results(reply_token, campsites, current_page, keyword):
    """處理搜尋結果的顯示邏輯"""
    try:
        # 計算分頁資訊
        total_pages = (len(campsites) + 9) // 10
        
        # 檢查頁碼是否有效
        if current_page < 1 or current_page > total_pages:
            send_line_message(
                reply_token,
                [{"type": "text", "text": "抱歉，請求的頁碼無效。請重新搜尋。"}]
            )
            return
            
        start_idx = (current_page - 1) * 10
        end_idx = min(start_idx + 10, len(campsites))
        current_campsites = campsites[start_idx:end_idx]
        
        # 檢查是否有有效的營區資料
        if not current_campsites:
            send_line_message(
                reply_token,
                [{"type": "text", "text": "抱歉，此頁沒有可顯示的營區資訊。"}]
            )
            return
            
        # 建立 Flex Message
        bubbles = []
        
        # 處理每個營區資訊
        for camp in current_campsites:
            if not camp.get("image_urls"):
                continue
                
            # 建立營區資訊 bubble
            bubble = create_camp_bubble(camp)
            bubbles.append(bubble)
            
        # 如果沒有有效的營區資訊
        if not bubbles:
            send_line_message(
                reply_token,
                [{"type": "text", "text": "抱歉，無法顯示營區資訊。請重新搜尋。"}]
            )
            return
            
        # 如果還有下一頁，加入分頁按鈕
        if current_page < total_pages:
            next_page_bubble = create_next_page_bubble(current_page, total_pages, keyword)
            bubbles.append(next_page_bubble)
            
        # 創建並發送 Flex Message
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
        
    except Exception as e:
        logger.error(f"處理搜尋結果時發生錯誤: {str(e)}")
        send_line_message(
            reply_token,
            [{"type": "text", "text": "抱歉，顯示搜尋結果時發生錯誤。請重新搜尋。"}]
        )
