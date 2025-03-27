from pymongo import MongoClient
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 連接到 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["CampingBot"]
collection = db["CampArea"]

try:
    # 檢查連接
    client.admin.command("ping")
    logger.info("成功連接到 MongoDB")

    # 獲取文檔數量
    count = collection.count_documents({})
    logger.info(f"CampArea 集合中有 {count} 個文檔")

    # 獲取一個示例文檔
    if count > 0:
        sample = collection.find_one()
        logger.info(
            f"示例文檔：\n名稱：{sample.get('name')}\n位置：{sample.get('location')}\n圖片數量：{len(sample.get('image_urls', []))}"
        )

except Exception as e:
    logger.error(f"發生錯誤：{str(e)}")
finally:
    client.close()
    logger.info("關閉 MongoDB 連接")
