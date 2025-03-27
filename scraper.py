from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import logging
from models import Campsite

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        valid_image_urls = []  # 移到這裡

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

        def validate_and_add_image(url):
            """驗證並添加圖片URL"""
            if any(keyword in url.lower() for keyword in filtered_keywords):
                return False
            if url.lower().endswith(".gif"):
                return False
            try:
                img_response = requests.head(url, headers=HEADERS, timeout=5)
                if (
                    img_response.status_code == 200
                    and "image" in img_response.headers.get("content-type", "")
                ):
                    valid_image_urls.append(url)
                    logger.info(f"驗證有效的圖片URL: {url}")
                    return True
            except Exception as e:
                logger.error(f"檢查圖片URL時發生錯誤: {url}, 錯誤: {str(e)}")
            return False

        # 優先從輪播圖獲取圖片
        carousel_images = soup.select("#myCarousel .carousel-inner img, .carousel img")
        for img in carousel_images:
            img_src = img.get("src") or img.get("data-src")
            if img_src:
                full_url = urljoin(base_url, img_src)
                if validate_and_add_image(full_url):
                    break

        # 如果輪播圖沒有圖片，嘗試獲取其他圖片
        if not valid_image_urls:
            content_images = soup.select(
                ".content img, .camp-info img, .camp-detail img, .camp-pic img, #camp-detail img"
            )
            for img in content_images:
                img_src = img.get("src") or img.get("data-src")
                if img_src:
                    full_url = urljoin(base_url, img_src)
                    if validate_and_add_image(full_url):
                        break

        # 如果還是沒有圖片，嘗試獲取所有圖片
        if not valid_image_urls:
            all_images = soup.select(
                "img[src*='upload'], img[src*='photo'], img[src*='image']"
            )
            for img in all_images:
                img_src = img.get("src") or img.get("data-src")
                if img_src:
                    full_url = urljoin(base_url, img_src)
                    if validate_and_add_image(full_url):
                        break

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


if __name__ == "__main__":
    # 當直接執行此檔案時，執行爬蟲並儲存資料
    save_campsite()
