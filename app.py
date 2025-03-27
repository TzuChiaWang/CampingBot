from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    Response,
    jsonify,
)

from forms import CampsiteForm
from models import Campsite
import requests
import json
import os
import logging
import hmac
import hashlib
import base64
from dotenv import load_dotenv
from scraper import scrape_campsite, save_campsite

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "your_secret_key")

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


@app.route("/callback", methods=["POST"])
def callback():
    # 獲取 X-Line-Signature header 值
    signature = request.headers.get("X-Line-Signature", "")

    # 獲取請求內容
    body = request.get_data()
    logger.info("Request body: " + body.decode("utf-8"))

    # 驗證簽名
    if not verify_signature(body, signature):
        logger.error("Invalid signature")
        abort(400)

    try:
        events = json.loads(body.decode("utf-8"))["events"]
        logger.info(f"Received events: {events}")

        for event in events:
            if event["type"] == "message" and event["message"]["type"] == "text":
                handle_message(event)

        return "OK"
    except Exception as e:
        logger.error(f"處理 webhook 時發生錯誤: {str(e)}")
        abort(400)


def handle_message(event):
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
                            "uri": camp.get(
                                "booking_url", "https://www.easycamp.com.tw"
                            ),
                        },
                        "color": "#1D7D81",
                        "margin": "lg",
                    },
                ],
            },
        }
        bubbles.append(first_bubble)

        # 第二個 bubble 顯示兩張照片和查看更多按鈕
        if len(camp["image_urls"]) > 2:  # 確保至少有3張照片（第一張在第一個bubble）
            # 獲取 ngrok 的 URL
            ngrok_url = os.environ.get("NGROK_URL", "")
            if not ngrok_url:
                logger.warning("未設置 NGROK_URL 環境變數")
                ngrok_url = request.host_url.rstrip("/")

            # 確保 _id 是字符串格式
            campsite_id = str(camp["_id"])
            logger.info(f"生成照片頁面 URL，營區ID: {campsite_id}")

            # 構建查看照片的 URL
            view_photos_url = f"{ngrok_url}/view_photos/{campsite_id}"
            logger.info(f"生成的照片頁面 URL: {view_photos_url}")

            second_bubble = {
                "type": "bubble",
                "size": "mega",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",  # 設置整體間距
                    "paddingAll": "0px",
                    "contents": [
                        {
                            "type": "image",
                            "url": camp["image_urls"][1],
                            "size": "full",
                            "aspectRatio": "3:2",
                            "aspectMode": "cover",
                            "margin": "none",
                        },
                        {
                            "type": "image",
                            "url": camp["image_urls"][2],
                            "size": "full",
                            "aspectRatio": "3:2",
                            "aspectMode": "cover",
                            "margin": "md",  # 添加上方間距
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "button",
                                    "style": "primary",
                                    "action": {
                                        "type": "uri",
                                        "label": "點我看更多照片",
                                        "uri": view_photos_url,
                                    },
                                    "color": "#1D7D81",
                                    "height": "md",
                                },
                            ],
                            "paddingAll": "xl",  # 添加按鈕周圍的內邊距
                        },
                    ],
                },
            }
            bubbles.append(second_bubble)

        flex_message = {
            "type": "flex",
            "altText": f"營區：{camp['name']}",
            "contents": {"type": "carousel", "contents": bubbles},
        }

        logger.info(
            f"準備發送的 Flex Message: {json.dumps(flex_message, ensure_ascii=False)}"
        )
        success = send_line_message(reply_token, flex_message)

        if success:
            logger.info("Flex Message 發送成功")
        else:
            logger.error("發送 Flex Message 失敗")
            send_line_message(
                reply_token,
                {
                    "type": "text",
                    "text": f"找到營區：{camp['name']}\n很抱歉，圖片顯示發生問題。",
                },
            )

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {str(e)}")
        try:
            send_line_message(
                reply_token, {"type": "text", "text": "系統發生錯誤，請稍後再試。"}
            )
        except Exception as reply_error:
            logger.error(f"發送錯誤訊息失敗: {str(reply_error)}")


@app.route("/")
def index():
    campsites = Campsite.get_all()
    return render_template("index.html", campsites=campsites)


@app.route("/add1", methods=["GET", "POST"])
def add_campsite():
    form = CampsiteForm()
    if form.validate_on_submit():
        campsite_data = {
            "name": form.name.data,
            "location": form.location.data,
            "altitude": form.altitude.data,
            "features": form.features.data,
            "WC": form.WC.data,
            "signal_strength": form.signal_strength.data,
            "pets": form.pets.data,
            "facilities": form.facilities.data,
            "sideservice": form.sideservice.data,
            "open_time": form.open_time.data,
            "parking": form.parking.data,
            "image_urls": form.image_urls.data,
            "booking_url": form.booking_url.data,
            "social_url": form.social_url.data,
        }
        Campsite.create(campsite_data)
        flash("營地已成功新增！", "success")
        return redirect(url_for("index"))
    return render_template("add.html", form=form)


@app.route("/edit/<id>", methods=["GET", "POST"])
def edit_campsite(id):
    try:
        object_id = ObjectId(id)
    except InvalidId:
        abort(404)

    campsite = Campsite.get_by_id(object_id)
    if not campsite:
        abort(404)

    form = CampsiteForm()
    if request.method == "GET":
        # 填充表單數據
        for field in form._fields:
            if field in campsite:
                form._fields[field].data = campsite[field]

    if form.validate_on_submit():
        campsite_data = {
            "name": form.name.data,
            "location": form.location.data,
            "altitude": form.altitude.data,
            "features": form.features.data,
            "WC": form.WC.data,
            "signal_strength": form.signal_strength.data,
            "pets": form.pets.data,
            "facilities": form.facilities.data,
            "sideservice": form.sideservice.data,
            "open_time": form.open_time.data,
            "parking": form.parking.data,
            "image_urls": form.image_urls.data,
            "booking_url": form.booking_url.data,
            "social_url": form.social_url.data,
        }
        Campsite.update(object_id, campsite_data)
        flash("營地資訊已更新！", "success")
        return redirect(url_for("index"))
    return render_template("edit.html", form=form, campsite=campsite)


@app.route("/scrape")
def scrape():
    save_campsite()  # 爬取並存入資料庫
    flash("營區爬取完成！", "success")
    return redirect(url_for("index"))


@app.route("/delete/<id>")
def delete_campsite(id):
    try:
        object_id = ObjectId(id)
        Campsite.delete(object_id)
        flash("營地已刪除！", "success")
    except InvalidId:
        flash("無效的營地ID！", "error")
    return redirect(url_for("index"))


@app.route("/image_proxy")
def image_proxy():
    image_url = request.args.get("url")
    if not image_url:
        return "缺少圖片 URL", 400

    # 向原始網站請求圖片
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(image_url, headers=headers, stream=True)

    # 如果請求成功，回傳圖片
    if response.status_code == 200:
        return Response(response.content, content_type=response.headers["Content-Type"])
    else:
        return "圖片無法載入", response.status_code


@app.route("/api/campsites", methods=["GET"])
def api_search_campsite():
    query = request.args.get("q", "")
    campsites = Campsite.search(query)
    return jsonify([{**c, "_id": str(c["_id"])} for c in campsites])


@app.route("/view_photos/<campsite_id>")
def view_photos(campsite_id):
    """顯示營區的所有照片"""
    try:
        logger.info(f"嘗試訪問營區照片頁面，ID: {campsite_id}")

        # 檢查 ID 格式
        if not ObjectId.is_valid(campsite_id):
            logger.error(f"無效的營區ID格式: {campsite_id}")
            flash("無效的營區ID", "error")
            return render_template("404.html"), 404

        # 轉換為 ObjectId
        object_id = ObjectId(campsite_id)
        logger.info(f"轉換後的 ObjectId: {object_id}")

        # 獲取營區資訊
        campsite = Campsite.get_by_id(object_id)
        if not campsite:
            logger.error(f"找不到營區，ID: {campsite_id}")
            flash("找不到指定的營區", "error")
            return render_template("404.html"), 404

        logger.info(
            f"成功找到營區: {campsite['name']}, 圖片數量: {len(campsite.get('image_urls', []))}"
        )

        # 檢查圖片 URLs
        image_urls = campsite.get("image_urls", [])
        if not image_urls:
            logger.warning(f"營區 {campsite['name']} 沒有圖片")
            flash("此營區目前沒有照片", "warning")
            return render_template("view_photos.html", campsite=campsite)

        # 驗證圖片 URLs
        valid_urls = []
        for url in image_urls:
            try:
                response = requests.head(url, timeout=2)
                if response.status_code == 200:
                    valid_urls.append(url)
                else:
                    logger.warning(
                        f"無效的圖片URL: {url}, 狀態碼: {response.status_code}"
                    )
            except Exception as e:
                logger.error(f"檢查圖片URL時發生錯誤: {url}, 錯誤: {str(e)}")

        if not valid_urls:
            logger.warning(f"營區 {campsite['name']} 沒有有效的圖片URL")
            flash("無法載入營區照片，請稍後再試", "error")
            campsite["image_urls"] = []
        else:
            campsite["image_urls"] = valid_urls
            logger.info(f"有效圖片數量: {len(valid_urls)}")

        return render_template("view_photos.html", campsite=campsite)

    except InvalidId as e:
        logger.error(f"無效的 ObjectId 格式: {str(e)}")
        flash("無效的營區ID", "error")
        return render_template("404.html"), 404
    except Exception as e:
        logger.error(f"查看照片時發生錯誤: {str(e)}")
        flash("系統發生錯誤，請稍後再試", "error")
        return render_template("500.html"), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    # 使用 0.0.0.0 讓外部可以訪問，並使用 port 3000
    app.run(host="0.0.0.0", port=3000, debug=True)
