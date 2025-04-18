from pymongo import MongoClient
import re
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 載入環境變數
load_dotenv()

# 連接到 MongoDB
client = MongoClient(
    os.getenv("MONGODB_URI"),
    tls=True,
    tlsAllowInvalidCertificates=True,
    retryWrites=True,
    w="majority"
)
db = client[os.getenv("MONGODB_DB")]
collection = db[os.getenv("MONGODB_COLLECTION")]
users = db['users']  # 新增用戶集合

class User(UserMixin):
    def __init__(self, username):
        self.username = username
        self.id = username

    @staticmethod
    def get(username):
        user_data = users.find_one({"username": username})
        if not user_data:
            return None
        return User(username=user_data['username'])

    @staticmethod
    def create(username, password_hash):
        if users.find_one({"username": username}):
            return False
        users.insert_one({
            "username": username,
            "password": password_hash
        })
        return True

    def check_password(self, password):
        user_data = users.find_one({"username": self.username})
        if not user_data:
            return False
        return check_password_hash(user_data['password'], password)


class Campsite:
    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """獲取所有營地"""
        return list(collection.find())

    @staticmethod
    def get_by_id(id) -> Dict[str, Any]:
        """根據ID獲取營地"""
        return collection.find_one({"_id": id})

    @staticmethod
    def get_by_name(name: str) -> Dict[str, Any]:
        """根據名稱獲取營地"""
        return collection.find_one({"name": name})

    @staticmethod
    def create(data: Dict[str, Any]) -> None:
        """創建新的營地記錄"""
        collection.insert_one(data)

    @staticmethod
    def update(id, data: Dict[str, Any]) -> None:
        """更新營地資訊"""
        collection.update_one({"_id": id}, {"$set": data})

    @staticmethod
    def delete(id) -> None:
        """刪除營地"""
        collection.delete_one({"_id": id})

    @staticmethod
    def search(query: str) -> List[Dict[str, Any]]:
        """搜索營地"""
        if not query:
            return list(collection.find())

        # 建立搜索條件
        regex = re.compile(query, re.IGNORECASE)
        search_conditions = {
            "$or": [
                {"name": regex},
                {"location": regex},
                {"features": regex},
                {"altitude": regex},
                {"WC": regex},
                {"facilities": regex},
                {"sideservice": regex},
            ]
        }
        return list(collection.find(search_conditions))

    @staticmethod
    def search_by_keywords(keywords: str) -> List[Dict[str, Any]]:
        """根據關鍵字搜索營地"""
        if not keywords:
            return []

        # 將關鍵字分割並建立搜索條件
        keyword_list = keywords.split()
        search_conditions = []
        altitude_filter = None
        pet_filter = None
        signal_filter = None
        parking_filter = None
        region_filter = None

        # 定義各區域包含的城市
        region_cities = {
            "北部": ["臺北", "台北", "新北", "基隆", "新竹", "桃園", "宜蘭"],
            "中部": ["臺中", "台中", "苗栗", "彰化", "南投", "雲林"],
            "南部": ["高雄", "臺南", "台南", "嘉義", "屏東", "澎湖"],
            "東部": ["花蓮", "臺東", "台東"]
        }

        # 定義通訊服務對應關係
        signal_keywords = {
            "中華電信有訊號": ["中華", "中華電信"],
            "中華電信": ["中華", "中華電信"],
            "遠傳有訊號": ["遠傳", "遠傳電信"],
            "遠傳": ["遠傳", "遠傳電信"],
            "台哥大有訊號": ["台哥大", "台哥大電信"],
            "台哥大": ["台哥大", "台哥大電信"],
            "亞太有訊號": ["亞太", "亞太電信"],
            "亞太": ["亞太", "亞太電信"],
            "WIFI": ["WIFI", "有網路", "wifi"],
            "wifi": ["WIFI", "有網路", "wifi"],
            "有wifi": ["WIFI", "有網路", "wifi"],
            "有WIFI": ["WIFI", "有網路", "wifi"],
            "無資訊": ["無資訊"]
        }

        # 定義停車方式對應關係
        parking_keywords = {
            "車停營位旁": ["車邊", "營位旁", "車停營位旁", "車停帳邊"],
            "集中停車": ["集中停車", "集中", "停車場"]
        }

        for keyword in keyword_list:
            # 處理區域關鍵字
            if keyword in region_cities:
                city_patterns = [f".*{city}.*" for city in region_cities[keyword]]
                region_filter = {
                    "location": {
                        "$regex": f"({'|'.join(city_patterns)})",
                        "$options": "i"
                    }
                }
                continue
            # 處理海拔相關的關鍵字
            elif keyword in ["海拔高", "高海拔"]:
                altitude_filter = {"altitude": {"$regex": r"\d+", "$exists": True}}
                continue
            elif keyword in ["海拔低", "低海拔"]:
                altitude_filter = {"altitude": {"$regex": r"\d+", "$exists": True}}
                continue
            # 處理寵物相關的關鍵字
            elif keyword in ["可帶寵物", "寵物可", "可攜帶寵物", "可寵物"]:
                pet_filter = {"pets": "自搭帳可帶寵物"}
                continue
            elif keyword in ["不可帶寵物", "寵物不可", "不可攜帶寵物", "不可寵物"]:
                pet_filter = {"pets": "全區不可帶寵物"}
                continue
            # 處理通訊相關的關鍵字
            signal_match = False
            for signal_type, keywords in signal_keywords.items():
                if keyword in keywords:
                    # 使用正則表達式來匹配逗號分隔的字串中的值
                    signal_filter = {
                        "signal_strength": {
                            "$regex": f".*{signal_type}.*",
                            "$options": "i"
                        }
                    }
                    signal_match = True
                    break
            if signal_match:
                continue
            # 處理停車相關的關鍵字
            parking_match = False
            for parking_type, keywords in parking_keywords.items():
                if keyword in keywords:
                    parking_filter = {"parking": parking_type}
                    parking_match = True
                    break
            if parking_match:
                continue

            regex = re.compile(keyword, re.IGNORECASE)
            condition = {
                "$or": [
                    {"name": regex},
                    {"location": regex},
                    {"features": regex},
                    {"altitude": regex},
                    {"WC": regex},
                    {"facilities": regex},
                    {"sideservice": regex},
                ]
            }
            search_conditions.append(condition)

        # 建立基本查詢條件
        if len(search_conditions) > 1:
            query = {"$and": search_conditions}
        elif len(search_conditions) == 1:
            query = search_conditions[0]
        else:
            query = {}

        # 添加區域過濾條件
        if region_filter:
            if query:
                query = {"$and": [query, region_filter]}
            else:
                query = region_filter

        # 添加寵物過濾條件
        if pet_filter:
            if query:
                query = {"$and": [query, pet_filter]}
            else:
                query = pet_filter

        # 添加通訊過濾條件
        if signal_filter:
            if query:
                query = {"$and": [query, signal_filter]}
            else:
                query = signal_filter

        # 添加停車過濾條件
        if parking_filter:
            if query:
                query = {"$and": [query, parking_filter]}
            else:
                query = parking_filter

        # 獲取初步結果
        results = list(collection.find(query))

        # 處理海拔過濾
        if altitude_filter is not None:
            filtered_results = []
            for result in results:
                try:
                    # 從海拔字串中提取數字
                    altitude_str = result.get("altitude", "0")
                    altitude_match = re.search(r'(\d+)', altitude_str)
                    if altitude_match:
                        altitude = int(altitude_match.group(1))
                        # 根據高低海拔條件過濾
                        if ("海拔高" in keyword_list or "高海拔" in keyword_list) and altitude >= 1000:
                            filtered_results.append(result)
                        elif ("海拔低" in keyword_list or "低海拔" in keyword_list) and altitude < 1000:
                            filtered_results.append(result)
                except (ValueError, TypeError):
                    continue
            results = filtered_results

        # 確保每個結果都包含其獨特的圖片URLs
        for result in results:
            if "image_urls" not in result:
                result["image_urls"] = ["https://via.placeholder.com/1024x768"]

        return results
