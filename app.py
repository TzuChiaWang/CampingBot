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
import logging
from dotenv import load_dotenv
from line_bot import verify_signature, handle_message, handle_postback
from bson import ObjectId
from bson.errors import InvalidId
import secrets
import os
from scraper import save_campsite

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = secrets.token_hex(32)  # 每次啟動時生成新的 64 字符密鑰

@app.route("/callback", methods=["POST"])
def callback():
    """處理來自 LINE 的 webhook 請求"""
    # 取得 X-Line-Signature header 值
    signature = request.headers["X-Line-Signature"]

    # 取得請求內容
    body = request.get_data(as_text=True)
    logger.info("Request body: " + body)

    try:
        # 驗證簽名
        if not verify_signature(body.encode("utf-8"), signature):
            abort(400)

        # 解析事件
        events = json.loads(body)["events"]
        for event in events:
            if event["type"] == "message" and event["message"]["type"] == "text":
                handle_message(event, Campsite)
            elif event["type"] == "postback":
                handle_postback(event, Campsite)

        return "OK"
    except Exception as e:
        logger.error(f"處理 webhook 請求時發生錯誤: {str(e)}")
        abort(500)


@app.route("/")
def index():
    query = request.args.get("q", "")
    if query:
        campsites = Campsite.search(query)
    else:
        campsites = Campsite.get_all()
    return render_template("index.html", campsites=campsites)


@app.route("/add", methods=["GET", "POST"])
def add_campsite():
    form = CampsiteForm()
    if form.validate_on_submit():
        # 將圖片 URL 字串分割為列表
        image_urls = [url.strip() for url in form.image_url.data.split(',') if url.strip()] if form.image_url.data else []
        
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
            "image_urls": image_urls,  # 使用處理後的圖片 URL 列表
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
            if field == "image_url" and "image_urls" in campsite:
                # 將圖片URL列表轉換為逗號分隔的字符串
                form._fields[field].data = ", ".join(campsite["image_urls"])
            elif field in campsite:
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
            "image_urls": [url.strip() for url in form.image_url.data.split(',') if url.strip()] if form.image_url.data else [],
            "booking_url": form.booking_url.data,
            "social_url": form.social_url.data,
        }
        Campsite.update(object_id, campsite_data)
        flash("營地資訊已更新！", "success")
        return redirect(url_for("index"))
    return render_template("edit.html", form=form, campsite=campsite)


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


@app.route("/update_data")
def update_data():
    """更新營區資料"""
    try:
        save_campsite()  # 執行爬蟲並儲存資料
        flash("營區資料已更新！", "success")
    except Exception as e:
        logger.error(f"更新營區資料時發生錯誤: {str(e)}")
        flash("更新資料時發生錯誤，請稍後再試", "error")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    # 只在本地開發環境使用 Flask 開發服務器
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 3000)), debug=True)
