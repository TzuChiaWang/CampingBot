from pymongo import MongoClient
import re
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import time
from functools import wraps
import hashlib
import json

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

# 簡單的記憶體快取實作
class SimpleCache:
    def __init__(self, default_timeout=300):  # 5分鐘預設過期時間
        self.cache = {}
        self.default_timeout = default_timeout
    
    def get(self, key):
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value, timeout=None):
        if timeout is None:
            timeout = self.default_timeout
        expiry = time.time() + timeout
        self.cache[key] = (value, expiry)
    
    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        self.cache.clear()

# 全域快取實例
cache = SimpleCache()

# 快取裝飾器
def cached(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = f"{func.__name__}:{hashlib.md5(str(args + tuple(sorted(kwargs.items()))).encode()).hexdigest()}"
            
            # 嘗試從快取獲取
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # 執行函數並快取結果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator

# 建立索引
def create_indexes():
    """建立資料庫索引以提升查詢效能"""
    try:
        # 為常用查詢欄位建立索引
        collection.create_index("name")
        collection.create_index("location")
        collection.create_index("altitude")
        collection.create_index("pets")
        collection.create_index("parking")
        collection.create_index("signal_strength")
        
        # 建立複合索引
        collection.create_index([("location", 1), ("pets", 1)])
        collection.create_index([("name", "text"), ("location", "text"), ("features", "text")])
        
        # 用戶集合索引
        users.create_index("username", unique=True)
        
        print("✅ 資料庫索引建立完成")
    except Exception as e:
        print(f"⚠️ 索引建立警告: {e}")

# 初始化時建立索引
create_indexes()

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
    @cached(timeout=600)  # 快取10分鐘
    def get_all() -> List[Dict[str, Any]]:
        """獲取所有營地"""
        return list(collection.find())

    @staticmethod
    @cached(timeout=1800)  # 快取30分鐘
    def get_all_paginated(page: int = 1, per_page: int = 12) -> Dict[str, Any]:
        """分頁獲取營地資料"""
        skip = (page - 1) * per_page
        
        # 使用 MongoDB 的分頁查詢
        campsites = list(collection.find().skip(skip).limit(per_page))
        total = collection.count_documents({})
        
        return {
            'campsites': campsites,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

    @staticmethod
    @cached(timeout=1800)  # 快取30分鐘
    def get_by_id(id) -> Dict[str, Any]:
        """根據ID獲取營地"""
        return collection.find_one({"_id": id})

    @staticmethod
    @cached(timeout=1800)  # 快取30分鐘
    def get_by_name(name: str) -> Dict[str, Any]:
        """根據名稱獲取營地"""
        return collection.find_one({"name": name})

    @staticmethod
    def create(data: Dict[str, Any]) -> None:
        """創建新的營地記錄"""
        result = collection.insert_one(data)
        # 清除相關快取
        cache.clear()
        return result

    @staticmethod
    def update(id, data: Dict[str, Any]) -> None:
        """更新營地資訊"""
        result = collection.update_one({"_id": id}, {"$set": data})
        # 清除相關快取
        cache.clear()
        return result

    @staticmethod
    def delete(id) -> None:
        """刪除營地"""
        result = collection.delete_one({"_id": id})
        # 清除相關快取
        cache.clear()
        return result

    @staticmethod
    def get_total_count() -> int:
        """獲取營地總數"""
        return collection.count_documents({})


    @staticmethod
    @cached(timeout=300)  # 快取5分鐘
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
            "集中停車": ["集中停車", "集中", "停車場","可下裝備後，集中停車"]
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
                altitude_filter = {
                    "$or": [
                        {"altitude": {"$gt": 1000}},  # 超過1000公尺視為高海拔
                        {"name": {"$regex": ".*高海拔.*", "$options": "i"}},
                        {"description": {"$regex": ".*高海拔.*", "$options": "i"}}
                    ]
                }
                continue
            elif keyword in ["海拔低", "低海拔"]:
                altitude_filter = {
                    "$or": [
                        {"altitude": {"$lt": 1000}},  # 低於1000公尺視為低海拔
                        {"name": {"$regex": ".*低海拔.*", "$options": "i"}},
                        {"description": {"$regex": ".*低海拔.*", "$options": "i"}}
                    ]
                }
                continue
            # 處理寵物相關的關鍵字
            elif keyword in ["可帶寵物", "寵物可", "可攜帶寵物", "可寵物"]:
                pet_filter = {
                    "$or": [
                        {"pets": "自搭帳可帶寵物"},
                        {"description": {"$regex": ".*可帶寵物.*", "$options": "i"}}
                    ]
                }
                continue
            elif keyword in ["不可帶寵物", "寵物不可", "不可攜帶寵物", "不可寵物"]:
                pet_filter = {
                    "$or": [
                        {"pets": "全區不可帶寵物"},
                        {"description": {"$regex": ".*不可帶寵物.*", "$options": "i"}}
                    ]
                }
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
                    parking_filter = {
                        "$or": [
                            {"parking": parking_type},
                            {"parking": {"$regex": f".*{keyword}.*", "$options": "i"}},
                            {"description": {"$regex": f".*{keyword}.*", "$options": "i"}}
                        ]
                    }
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
