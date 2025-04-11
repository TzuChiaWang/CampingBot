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
    """創建縣市選擇介面"""
    return {
        "type": "flex",
        "altText": "請選擇地區",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "你想去哪裡呢？🎉",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": region,
                                    "data": json.dumps({
                                        "action": "select_region",
                                        "region": region
                                    }),
                                    "displayText": region
                                },
                                "margin": "sm"
                            } for region in ["北部", "中部", "南部", "東部"]
                        ]
                    }
                ]
            }
        }
    }

def create_city_selection(region):
    """創建縣市選擇介面"""
    return {
        "type": "flex",
        "altText": f"請選擇{region}的縣市",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"告訴我{region}的哪裡吧！🏙️",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": city,
                                    "data": json.dumps({
                                        "action": "select_city",
                                        "city": city
                                    }),
                                    "displayText": city
                                },
                                "margin": "sm"
                            } for city in REGION_CITIES[region]
                        ]
                    }
                ]
            }
        }
    }

def create_altitude_selection():
    """創建海拔選擇介面"""
    return {
        "type": "flex",
        "altText": "請選擇海拔高度",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "適合你的海拔高度⛰️",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": altitude,
                                    "data": json.dumps({
                                        "action": "select_altitude",
                                        "altitude": altitude
                                    }),
                                    "displayText": altitude
                                },
                                "margin": "sm"
                            } for altitude in ["高海拔", "低海拔", "兩者皆可"]
                        ]
                    }
                ]
            }
        }
    }

def create_pet_selection():
    """創建寵物選擇介面"""
    return {
        "type": "flex",
        "altText": "請選擇是否可帶寵物",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "有可愛的毛小孩嗎？🐾",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": pet_option,
                                    "data": json.dumps({
                                        "action": "select_pet",
                                        "pet": pet_option
                                    }),
                                    "displayText": pet_option
                                },
                                "margin": "sm"
                            } for pet_option in ["可帶寵物", "不可帶寵物", "兩者皆可"]
                        ]
                    }
                ]
            }
        }
    }

def create_parking_selection():
    """創建停車選擇介面"""
    return {
        "type": "flex",
        "altText": "請選擇停車方式",
        "contents": {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "想不想做苦力活？🅿️",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#1D7D81",
                                "action": {
                                    "type": "postback",
                                    "label": parking_option,
                                    "data": json.dumps({
                                        "action": "select_parking",
                                        "parking": parking_option
                                    }),
                                    "displayText": parking_option
                                },
                                "margin": "sm"
                            } for parking_option in ["車停營位旁", "集中停車", "兩者皆可"]
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
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "施展魔法吧！🪄",
                        "weight": "bold",
                        "size": "xl",
                        "align": "center",
                        "color": "#1D7D81",
                        "margin": "md"
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1D7D81",
                        "action": {
                            "type": "postback",
                            "label": "GO！",
                            "data": json.dumps({
                                "action": "search_start"
                            }),
                            "displayText": "GO！"
                        },
                        "margin": "lg"
                    }
                ]
            }
        }
    }

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
            current_page = data.get("page", 1)
            keyword = data.get("keyword", "")
            campsites = Campsite.search_by_keywords(keyword)
            return handle_search_results(event["replyToken"], campsites, current_page, keyword)
            
        # 處理地區選擇
        elif data.get("action") == "select_region":
            region = data.get("region")
            user_states[user_id]["region"] = region
            user_states[user_id]["step"] = "city"
            # 發送對應地區的縣市選擇介面
            send_line_message(event["replyToken"], [create_city_selection(region)])
            
        # 處理縣市選擇
        elif data.get("action") == "select_city":
            city = data.get("city")
            user_states[user_id]["city"] = city
            user_states[user_id]["step"] = "altitude"
            send_line_message(event["replyToken"], [create_altitude_selection()])
            
        # 處理海拔選擇
        elif data.get("action") == "select_altitude":
            user_states[user_id]["altitude"] = data.get("altitude")
            user_states[user_id]["step"] = "pet"
            send_line_message(event["replyToken"], [create_pet_selection()])
            
        # 處理寵物選擇
        elif data.get("action") == "select_pet":
            user_states[user_id]["pet"] = data.get("pet")
            user_states[user_id]["step"] = "parking"
            send_line_message(event["replyToken"], [create_parking_selection()])
            
        # 處理停車選擇
        elif data.get("action") == "select_parking":
            user_states[user_id]["parking"] = data.get("parking")
            user_states[user_id]["step"] = "go"
            send_line_message(event["replyToken"], [create_go_button()])
            
        # 處理搜尋開始
        elif data.get("action") == "search_start":
            state = user_states.get(user_id, {})
            if not state:
                send_line_message(event["replyToken"], [{"type": "text", "text": "請重新開始搜尋流程"}])
                return
                
            # 構建搜尋關鍵字
            keywords = []
            keywords.append(state["city"])  # 使用選擇的縣市而不是地區
            
            if state["altitude"] != "兩者皆可":
                keywords.append(state["altitude"])
            if state["pet"] != "兩者皆可":
                keywords.append(state["pet"])
            if state["parking"] != "兩者皆可":
                keywords.append(state["parking"])
                
            # 執行搜尋
            search_text = " ".join(keywords)
            campsites = Campsite.search_by_keywords(search_text)
            
            # 清除用戶狀態
            del user_states[user_id]
            
            # 顯示搜尋結果
            return handle_search_results(event["replyToken"], campsites, 1, search_text)
            
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
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "xl",
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
