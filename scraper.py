from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging
import requests
import json
import time
from models import Campsite

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 圖片驗證設定
FILTERED_KEYWORDS = ["banner", "logo", "icon", "button", "ad", "advertisement"]
MIN_IMAGE_SIZE = 50 * 1024  # 50KB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
VALID_IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]

# HTML 分頁的 URL
PAGE_URLS = [
    # 新北市
    "https://www.easycamp.com.tw/Push_Camp_1_2_0.html",
    # 桃園市
    "https://www.easycamp.com.tw/Push_Camp_1_4_0.html",
    "https://www.easycamp.com.tw/Push_Camp_1_4_1.html",
    "https://www.easycamp.com.tw/Push_Camp_1_4_2.html",
    # 新竹縣
    "https://www.easycamp.com.tw/Push_Camp_1_5_0.html",
    "https://www.easycamp.com.tw/Push_Camp_1_5_1.html",
    "https://www.easycamp.com.tw/Push_Camp_1_5_2.html",
    "https://www.easycamp.com.tw/Push_Camp_1_5_3.html",
    "https://www.easycamp.com.tw/Push_Camp_1_5_4.html",
    # 新竹市
    "https://www.easycamp.com.tw/Push_Camp_1_20_0.html",
    "https://www.easycamp.com.tw/Push_Camp_1_20_1.html",
    "https://www.easycamp.com.tw/Push_Camp_1_20_2.html",
    # 苗栗縣
    "https://www.easycamp.com.tw/Push_Camp_2_7_0.html",
    "https://www.easycamp.com.tw/Push_Camp_2_7_1.html",
    "https://www.easycamp.com.tw/Push_Camp_2_7_2.html",
    "https://www.easycamp.com.tw/Push_Camp_2_7_3.html",
    # 台中市
    "https://www.easycamp.com.tw/Push_Camp_2_9_0.html",
    # 南投縣
    "https://www.easycamp.com.tw/Push_Camp_2_11_0.html",
    "https://www.easycamp.com.tw/Push_Camp_2_11_1.html",
    "https://www.easycamp.com.tw/Push_Camp_2_11_2.html",
    "https://www.easycamp.com.tw/Push_Camp_2_11_3.html",
    # 彰化縣
    "https://www.easycamp.com.tw/Push_Camp_2_12_0.html",
    # 雲林縣
    "https://www.easycamp.com.tw/Push_Camp_3_13_0.html",
    "https://www.easycamp.com.tw/Push_Camp_3_13_1.html",
    "https://www.easycamp.com.tw/Push_Camp_3_13_2.html",
    # 嘉義縣
    "https://www.easycamp.com.tw/Push_Camp_3_16_0.html",
    # 台南市
    "https://www.easycamp.com.tw/Push_Camp_3_18_0.html",
    # 高雄市
    "https://www.easycamp.com.tw/Push_Camp_4_21_0.html",
    # 屏東縣
    "https://www.easycamp.com.tw/Push_Camp_4_22_0.html"
]

# API 分頁的 URL
API_URLS = [
    "https://www.easycamp.com.tw/store/push_store_list/1/4/0/4/%5B%22default%22%5D/0/2",
    "https://www.easycamp.com.tw/store/push_store_list/1/5/0/4/%5B%22default%22%5D/0/2",
    "https://www.easycamp.com.tw/store/push_store_list/1/5/0/4/%5B%22default%22%5D/0/3",
    "https://www.easycamp.com.tw/store/push_store_list/1/5/0/4/%5B%22default%22%5D/0/4",
    "https://www.easycamp.com.tw/store/push_store_list/1/20/0/4/%5B%22default%22%5D/0/2",
    "https://www.easycamp.com.tw/store/push_store_list/2/7/0/4/%5B%22default%22%5D/0/2",
    "https://www.easycamp.com.tw/store/push_store_list/2/7/0/4/%5B%22default%22%5D/0/3",
    "https://www.easycamp.com.tw/store/push_store_list/2/11/0/4/%5B%22default%22%5D/0/2",
    "https://www.easycamp.com.tw/store/push_store_list/2/11/0/4/%5B%22default%22%5D/0/3",
    "https://www.easycamp.com.tw/store/push_store_list/3/13/0/4/%5B%22default%22%5D/0/2"
]

# HTTP 請求標頭
HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.easycamp.com.tw/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1"
}

API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.easycamp.com.tw/",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin"
}

def get_campsite_urls_from_html():
    """從 HTML 頁面獲取營區的 URL"""
    campsite_urls = []
    
    for url in PAGE_URLS:
        logger.info(f"正在處理 HTML 頁面: {url}")
        
        try:
            response = requests.get(url, headers=HTML_HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 找到所有營區連結
            campsite_links = soup.select("a[href*='Store_']")
            
            if not campsite_links:
                logger.warning(f"頁面 {url} 沒有找到營區連結")
                continue
                
            for link in campsite_links:
                campsite_url = urljoin("https://www.easycamp.com.tw/", link["href"])
                if campsite_url not in campsite_urls:
                    campsite_urls.append(campsite_url)
                    logger.info(f"從 HTML 找到營區連結: {campsite_url}")
            
            time.sleep(1)
            
        except requests.RequestException as e:
            logger.error(f"獲取 HTML 營區列表時發生錯誤: {str(e)}")
            continue
            
    return campsite_urls

def get_campsite_urls_from_api():
    """從 API 獲取營區的 URL"""
    campsite_urls = []
    
    for url in API_URLS:
        logger.info(f"正在處理 API: {url}")
        
        try:
            response = requests.get(url, headers=API_HEADERS)
            response.raise_for_status()
            
            # 檢查內容類型
            content_type = response.headers.get('content-type', '')
            logger.info(f"API 回應內容類型: {content_type}")
            
            # 如果是 JSON，嘗試解析
            if 'application/json' in content_type:
                try:
                    data = response.json()
                    if data and "data" in data:
                        for item in data["data"]:
                            store_id = item.get("store_id")
                            if store_id:
                                campsite_url = f"https://www.easycamp.com.tw/Store_{store_id}.html"
                                if campsite_url not in campsite_urls:
                                    campsite_urls.append(campsite_url)
                                    logger.info(f"從 API JSON 找到營區連結: {campsite_url}")
                except json.JSONDecodeError as e:
                    logger.error(f"解析 JSON 時發生錯誤: {str(e)}")
                    logger.error(f"回應內容: {response.text[:200]}...")
            
            # 如果是 HTML，使用 BeautifulSoup 解析
            elif 'text/html' in content_type:
                logger.info("收到 HTML 回應，改用 BeautifulSoup 解析")
                soup = BeautifulSoup(response.text, "html.parser")
                campsite_links = soup.select("a[href*='Store_']")
                
                if not campsite_links:
                    logger.warning(f"API 頁面 {url} 沒有找到營區連結")
                    continue
                    
                for link in campsite_links:
                    campsite_url = urljoin("https://www.easycamp.com.tw/", link["href"])
                    if campsite_url not in campsite_urls:
                        campsite_urls.append(campsite_url)
                        logger.info(f"從 API HTML 找到營區連結: {campsite_url}")
            
            time.sleep(1)
            
        except requests.RequestException as e:
            logger.error(f"從 API 獲取營區列表時發生錯誤: {str(e)}")
            if 'response' in locals():
                logger.error(f"錯誤回應內容: {response.text[:200]}...")
            continue
            
    return campsite_urls

def scrape_campsite():
    """爬取所有營區詳細資訊"""
    all_campsites = []
    all_campsite_urls = []
    
    # 從 HTML 頁面獲取營區 URL
    logger.info("開始從 HTML 頁面獲取營區 URL")
    html_urls = get_campsite_urls_from_html()
    all_campsite_urls.extend(html_urls)
    
    # 從 API 獲取營區 URL
    logger.info("開始從 API 獲取營區 URL")
    api_urls = get_campsite_urls_from_api()
    all_campsite_urls.extend(api_urls)
    
    # 移除重複的 URL
    all_campsite_urls = list(set(all_campsite_urls))
    logger.info(f"總共找到 {len(all_campsite_urls)} 個不重複的營區")

    for base_url in all_campsite_urls:
        try:
            response = requests.get(base_url, headers=HTML_HEADERS)
            response.raise_for_status()
        except requests.RequestException as e:
            pass  # 靜默處理錯誤
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
            # 檢查是否包含過濾關鍵字
            if any(keyword in url.lower() for keyword in FILTERED_KEYWORDS):
                logger.info(f"圖片URL包含過濾關鍵字，跳過: {url}")
                return False

            try:
                # 先用 HEAD 請求檢查檔案類型和大小
                head_response = requests.head(url, headers=HTML_HEADERS, timeout=5)
                if head_response.status_code != 200:
                    logger.info(f"圖片URL無法訪問，跳過: {url}")
                    return False

                content_type = head_response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.info(f"非圖片類型，跳過: {url}")
                    return False

                # 檢查檔案大小（如果有提供）
                content_length = int(head_response.headers.get("content-length", 0))
                if content_length > 0:  # 只有當有提供檔案大小時才檢查
                    if content_length < MIN_IMAGE_SIZE:
                        logger.info(f"圖片太小，跳過: {url}")
                        return False
                    if content_length > MAX_IMAGE_SIZE:
                        logger.info(f"圖片太大，跳過: {url}")
                        return False

                # 如果通過所有檢查，添加到有效圖片列表
                if url not in valid_image_urls:  # 避免重複添加
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
