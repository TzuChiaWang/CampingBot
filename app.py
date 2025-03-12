from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    Response,
)

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from forms import CampsiteForm
from models import db, Campsite
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import json

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///campsites.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "your_secret_key"

db.init_app(app)
csrf = CSRFProtect(app)

# LINE Bot 設定
LINE_BOT_ACCESS_TOKEN = "YOUR_CHANNEL_ACCESS_TOKEN"
LINE_BOT_SECRET = "YOUR_CHANNEL_SECRET"
line_bot_api = LineBotApi(LINE_BOT_ACCESS_TOKEN)
handler = WebhookHandler(LINE_BOT_SECRET)

BASE_URL = [
    "https://www.easycamp.com.tw/Store_2051.html",
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

        # 營地名稱
        name_tag = soup.find("h1")
        if name_tag:
            # 先取得 h1 內的所有文字
            name_text = name_tag.get_text(strip=True, separator=" ")

            # 移除 <a> 內的內容
            for a_tag in name_tag.find_all("a"):
                a_tag.extract()  # 移除 <a> 標籤

            # 重新取得純粹的營區名稱
            name = name_tag.get_text(strip=True)
        else:
            name = "未知營區"

        # 營地圖片

        img_tags = soup.find_all("img")

        image_urls = []
        for img in img_tags:
            img_src = img.get("src") or img.get("data-src")  # 有些網站使用 data-src
            if img_src:
                full_url = urljoin(base_url, img_src)  # 確保相對路徑轉為完整 URL

                # **🚨 過濾掉 Logo、Icon、Banner 等無關圖片**
            if any(
                keyword in full_url.lower()
                for keyword in ["logo", "icon", "banner", "facebook"]
            ):
                continue  # 跳過這些圖片

            image_urls.append(full_url)

        """print(type(image_urls), image_urls)"""

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
            "image_urls": image_urls,
            "booking_url": base_url,
            "social_url": social_url["href"] if social_url else "",
        }

        all_campsites.append(campsite_data)  # 加入到列表

    return all_campsites  # 回傳所有營區資訊


def save_campsite():
    """將爬取的營區資訊存入資料庫"""
    campsites = scrape_campsite()

    for data in campsites:
        if not Campsite.query.filter_by(name=data["name"]).first():
            db.session.add(Campsite(**data))

    db.session.commit()  # 一次提交所有新增的營區資料


@app.route("/")
def index():
    query = request.args.get("q")

    campsites = Campsite.query

    if query:
        campsites = campsites.filter(
            (Campsite.name.ilike(f"%{query}%"))
            | (Campsite.location.ilike(f"%{query}%"))
            | (Campsite.features.ilike(f"%{query}%"))
        )

    return render_template("index.html", campsites=campsites.all())


@app.route("/add1", methods=["GET", "POST"])
def add_campsite():
    form = CampsiteForm()
    if form.validate_on_submit():
        campsite = Campsite(
            id=form.id.data,
            name=form.name.data,
            location=form.location.data,
            altitude=form.altitude.data,
            features=form.features.data,
            WC=form.WC.data,
            signal_strength=form.signal.data,
            pets=form.pets.data,
            facilities=form.facilities.data,
            sideservice=form.sideservice.data,
            open_time=form.open_time.data,
            parking=form.parking.data,
            image_url=form.image_url.data,
            booking_url=form.booking_url.data,
            social_url=form.social_url.data,
        )
        db.session.begin_nested()
        db.session.add(campsite)
        db.session.commit()
        flash("營區已新增！", "success")
        return redirect(url_for("index"))
    return render_template("add.html", form=form)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_campsite(id):
    campsite = Campsite.query.get_or_404(id)
    form = CampsiteForm(obj=campsite)
    if form.validate_on_submit():
        form.populate_obj(campsite)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("edit.html", form=form)


@app.route("/scrape")
def scrape():
    save_campsite()  # 爬取並存入資料庫
    flash("營區爬取完成！", "success")
    return redirect(url_for("index"))


@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    campsite = Campsite.query.filter(Campsite.name.ilike(f"%{text}%")).first()
    if campsite:
        reply_text = (
            f"{campsite.name}\n📍 {campsite.location}\n🔗 {campsite.booking_url}"
        )
    else:
        reply_text = "找不到相關營區 😢"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))


@app.route("/delete/<int:id>")
def delete_campsite(id):
    campsite = Campsite.query.get_or_404(id)
    db.session.delete(campsite)
    db.session.commit()
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


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
