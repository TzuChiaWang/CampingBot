import os
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv()

def keep_alive():
    """定期訪問應用以保持服務運行"""
    app_url = os.getenv("APP_URL", "https://your-app-url.onrender.com")
    health_endpoint = f"{app_url}/health"
    
    while True:
        try:
            # 發送請求到健康檢查端點
            response = requests.get(health_endpoint)
            if response.status_code == 200:
                logger.info(f"健康檢查成功 - {datetime.now().isoformat()}")
            else:
                logger.warning(f"健康檢查失敗 - 狀態碼: {response.status_code}")
        except Exception as e:
            logger.error(f"健康檢查出錯: {str(e)}")
        
        # 每 10 分鐘檢查一次
        time.sleep(600)

if __name__ == "__main__":
    keep_alive()
