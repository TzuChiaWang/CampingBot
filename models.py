from pymongo import MongoClient
import re
from typing import List, Dict, Any
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 連接到 MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))
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

        for keyword in keyword_list:
            regex = re.compile(keyword, re.IGNORECASE)
            condition = {
                "$or": [
                    {"name": regex},
                    {"location": regex},
                    {"features": regex},
                    {"altitude": regex},
                    {"WC": regex},
                    {"signal_strength": regex},
                    {"pets": regex},
                    {"facilities": regex},
                    {"sideservice": regex},
                ]
            }
            search_conditions.append(condition)

        # 如果有多個關鍵字，使用 $and 組合條件
        if len(search_conditions) > 1:
            query = {"$and": search_conditions}
        else:
            query = search_conditions[0]

        # 返回所有匹配的結果
        results = list(collection.find(query))

        # 確保每個結果都包含其獨特的圖片URLs
        for result in results:
            if "image_urls" not in result:
                result["image_urls"] = ["https://via.placeholder.com/1024x768"]

        return results
