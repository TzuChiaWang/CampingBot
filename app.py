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
from dotenv import load_dotenv
from scraper import scrape_campsite, save_campsite
from line_bot import verify_signature, handle_message, send_line_message, handle_postback

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "your_secret_key")

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
