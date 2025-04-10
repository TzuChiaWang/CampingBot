from pymongo import MongoClient
import re
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

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

        # 定義通訊服務對應關係
        signal_mapping = {
            "中華": "中華電信",
            "遠傳": "遠傳",
            "台哥大": "台哥大",
            "亞太": "亞太",
            "wifi": "WIFI",
            "WIFI": "WIFI",
            "網路": "WIFI",
            "無資訊": "無資訊"
        }

        # 定義停車方式對應關係
        parking_mapping = {
            "車邊": "車停營位旁",
            "營位旁": "車停營位旁",
            "集中": "集中停車",
            "停車場": "集中停車"
        }

        for keyword in keyword_list:
            # 處理海拔相關的關鍵字
            if keyword in ["海拔高", "高海拔"]:
                altitude_filter = {"altitude": {"$regex": r"\d+", "$exists": True}}
                continue
            elif keyword in ["海拔低", "低海拔"]:
                altitude_filter = {"altitude": {"$regex": r"\d+", "$exists": True}}
                continue
            # 處理寵物相關的關鍵字
            elif keyword in ["可帶寵物", "寵物可", "可攜帶寵物"]:
                pet_filter = {"pets": "自搭帳可帶寵物"}
                continue
            elif keyword in ["不可帶寵物", "寵物不可", "不可攜帶寵物"]:
                pet_filter = {"pets": "全區不可帶寵物"}
                continue
            # 處理通訊相關的關鍵字
            elif keyword in signal_mapping:
                signal_filter = {"signal_strength": signal_mapping[keyword]}
                continue
            # 處理停車相關的關鍵字
            elif keyword in parking_mapping:
                parking_filter = {"parking": parking_mapping[keyword]}
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
