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
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from bson import ObjectId
from bson.errors import InvalidId
import json
import os
import logging
import hmac
import hashlib
import base64
from dotenv import load_dotenv

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


BASE_URL = [
    "https://www.easycamp.com.tw/Store_624.html",
    "https://www.easycamp.com.tw/Store_2551.html",
    "https://www.easycamp.com.tw/Store_2602.html",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}


def scrape_campsite():
    """爬取多個 EasyCamp 營區詳細資訊"""
    all_campsites = []  # 存放所有營地資料

    for base_url in BASE_URL:
        try:
            response = requests.get(base_url, headers=HEADERS)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ 無法取得網頁 {base_url}：{e}")
            continue  # 跳過錯誤網址

        soup = BeautifulSoup(response.text, "html.parser")

        # 營地名稱 - 改善名稱處理邏輯
        name_tag = soup.find("h1")
        if name_tag:
            # 取得文字內容
            full_name = name_tag.get_text(strip=True)
            # 如果包含空格，只取第一個空格前的內容（通常是營區名）
            name = full_name.split("(")[0].split("（")[0].strip()
            logger.info(f"處理後的營區名稱: {name}")
        else:
            name = "未知營區"
            logger.warning("找不到營區名稱標籤")

        # 營地圖片 - 改善圖片獲取邏輯
        image_urls = []

        # 要過濾的關鍵字列表
        filtered_keywords = [
            "logo",
            "icon",
            "banner",
            "facebook",
            "button",
            "loading",
            "ajax-loader",
        ]

        # 優先從輪播圖獲取圖片
        carousel_images = soup.select("#myCarousel .carousel-inner img, .carousel img")
        if carousel_images:
            for img in carousel_images:
                img_src = img.get("src") or img.get("data-src")
                if img_src:
                    full_url = urljoin(base_url, img_src)
                    # 檢查是否包含任何需要過濾的關鍵字
                    if not any(
                        keyword in full_url.lower() for keyword in filtered_keywords
                    ):
                        if not full_url.lower().endswith(".gif"):
                            image_urls.append(full_url)
                            logger.info(f"從輪播找到圖片: {full_url}")

        # 如果輪播圖沒有圖片，嘗試獲取其他圖片
        if not image_urls:
            # 擴大搜索範圍
            content_images = soup.select(
                ".content img, .camp-info img, .camp-detail img, .camp-pic img, #camp-detail img"
            )
            for img in content_images:
                img_src = img.get("src") or img.get("data-src")
                if img_src:
                    full_url = urljoin(base_url, img_src)
                    # 檢查是否包含任何需要過濾的關鍵字
                    if not any(
                        keyword in full_url.lower() for keyword in filtered_keywords
                    ):
                        if not full_url.lower().endswith(".gif"):
                            image_urls.append(full_url)
                            logger.info(f"從內容區找到圖片: {full_url}")

        # 如果還是沒有圖片，嘗試獲取所有圖片
        if not image_urls:
            all_images = soup.select(
                "img[src*='upload'], img[src*='photo'], img[src*='image']"
            )
            for img in all_images:
                img_src = img.get("src") or img.get("data-src")
                if img_src:
                    full_url = urljoin(base_url, img_src)
                    # 檢查是否包含任何需要過濾的關鍵字
                    if not any(
                        keyword in full_url.lower() for keyword in filtered_keywords
                    ):
                        if not full_url.lower().endswith(".gif"):
                            image_urls.append(full_url)
                            logger.info(f"從其他區域找到圖片: {full_url}")

        # 確保圖片URL是有效的
        valid_image_urls = []
        for url in image_urls:
            try:
                img_response = requests.head(url, headers=HEADERS, timeout=5)
                if (
                    img_response.status_code == 200
                    and "image" in img_response.headers.get("content-type", "")
                ):
                    if not url.lower().endswith(".gif"):
                        valid_image_urls.append(url)
                        logger.info(f"驗證有效的圖片URL: {url}")
            except Exception as e:
                logger.error(f"檢查圖片URL時發生錯誤: {url}, 錯誤: {str(e)}")
                continue

        # 如果沒有有效圖片，使用預設圖片
        if not valid_image_urls:
            valid_image_urls = ["https://via.placeholder.com/1024x768"]
            logger.info("使用預設圖片")

        # 營區屬性
        details = {
            item.select_one(".title").text.strip(): item.select_one("li").text.strip()
            for item in soup.select(".classify")
        }

        # 無線通訊資訊
        signal_tag = soup.select_one(".classify .title:contains('無線通訊') + ul")
        signal = (
            ", ".join([li.text.strip() for li in signal_tag.select("li")])
            if signal_tag
            else "未知"
        )

        # 取得特定欄位
        location_tag = soup.select_one(".camp-add")
        location = location_tag.text.strip() if location_tag else "未知"
        altitude = details.get("海拔", "未知")
        features = details.get("營區特色", "未知")
        WC = details.get("衛浴配置", "未知")
        pets = details.get("攜帶寵物規定", "未知")
        facilities = details.get("附屬設施", "未知")
        sideservice = details.get("附屬服務", "未知")
        open_time = details.get("營業時間", "未知")
        parking = details.get("停車方式", "未知")

        # 訂位網址 & 社群網址
        booking_url = soup.select_one("a[href*='booking']")
        social_url = soup.select_one("a[href*='facebook']")

        campsite_data = {
            "name": name,
            "location": location,
            "altitude": altitude,
            "features": features,
            "WC": WC,
            "signal_strength": signal,
            "pets": pets,
            "facilities": facilities,
            "sideservice": sideservice,
            "open_time": open_time,
            "parking": parking,
            "image_urls": valid_image_urls,  # 使用驗證過的圖片URL列表
            "booking_url": base_url,
            "social_url": social_url["href"] if social_url else "",
        }

        all_campsites.append(campsite_data)

    return all_campsites


def save_campsite():
    """將爬取的營區資訊存入資料庫"""
    campsites = scrape_campsite()

    for data in campsites:
        if not Campsite.get_by_name(data["name"]):
            Campsite.create(data)


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
