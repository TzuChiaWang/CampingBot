"""
LINE Bot 優化功能模組
包含快取、批次處理、錯誤恢復等功能
"""

import json
import logging
from typing import List, Dict, Any
from functools import wraps
import time

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay=1):
    """重試裝飾器 - 用於 LINE API 調用失敗時重試"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"函數 {func.__name__} 在 {max_retries} 次嘗試後仍然失敗: {e}")
                        raise
                    logger.warning(f"函數 {func.__name__} 第 {attempt + 1} 次嘗試失敗，{delay} 秒後重試: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def validate_flex_message(message: Dict[str, Any]) -> bool:
    """驗證 Flex Message 格式是否正確"""
    try:
        if not isinstance(message, dict):
            return False
        
        if message.get('type') != 'flex':
            return False
        
        contents = message.get('contents')
        if not contents:
            return False
        
        # 檢查 bubble 或 carousel 格式
        if contents.get('type') in ['bubble', 'carousel']:
            return True
        
        return False
    except Exception:
        return False

def optimize_image_urls(camp_data: Dict[str, Any]) -> Dict[str, Any]:
    """優化營地圖片 URL，確保可用性"""
    if not camp_data.get('image_urls'):
        camp_data['image_urls'] = ['https://via.placeholder.com/800x600?text=No+Image']
        return camp_data
    
    # 確保至少有一個有效的圖片 URL
    valid_urls = []
    for url in camp_data['image_urls']:
        if url and isinstance(url, str) and url.startswith(('http://', 'https://')):
            valid_urls.append(url)
    
    if not valid_urls:
        valid_urls = ['https://via.placeholder.com/800x600?text=No+Image']
    
    camp_data['image_urls'] = valid_urls
    return camp_data

def create_error_message(error_type: str = "general") -> Dict[str, Any]:
    """創建標準化的錯誤訊息"""
    error_messages = {
        "search_failed": "🔍 搜尋時發生問題，請稍後再試或重新開始搜尋。",
        "no_results": "😅 找不到符合條件的營地，請嘗試調整搜尋條件。",
        "network_error": "🌐 網路連線有問題，請稍後再試。",
        "general": "😵 系統暫時有點忙，請稍後再試。"
    }
    
    return {
        "type": "text",
        "text": error_messages.get(error_type, error_messages["general"])
    }

def batch_process_campsites(campsites: List[Dict[str, Any]], batch_size: int = 10) -> List[List[Dict[str, Any]]]:
    """將營地列表分批處理，避免一次處理太多資料"""
    batches = []
    for i in range(0, len(campsites), batch_size):
        batch = campsites[i:i + batch_size]
        batches.append(batch)
    return batches

class MessageQueue:
    """訊息佇列管理器 - 避免訊息發送過於頻繁"""
    def __init__(self, max_size=100):
        self.queue = []
        self.max_size = max_size
        self.last_send_time = {}
        self.min_interval = 1  # 最小發送間隔（秒）
    
    def can_send(self, user_id: str) -> bool:
        """檢查是否可以向用戶發送訊息"""
        current_time = time.time()
        last_time = self.last_send_time.get(user_id, 0)
        return current_time - last_time >= self.min_interval
    
    def mark_sent(self, user_id: str):
        """標記已向用戶發送訊息"""
        self.last_send_time[user_id] = time.time()
    
    def add_message(self, user_id: str, reply_token: str, messages: List[Dict[str, Any]]):
        """添加訊息到佇列"""
        if len(self.queue) >= self.max_size:
            self.queue.pop(0)  # 移除最舊的訊息
        
        self.queue.append({
            'user_id': user_id,
            'reply_token': reply_token,
            'messages': messages,
            'timestamp': time.time()
        })

# 全域訊息佇列實例
message_queue = MessageQueue()

def log_user_interaction(user_id: str, action: str, details: str = ""):
    """記錄用戶互動日誌（用於分析和優化）"""
    logger.info(f"用戶互動 - ID: {user_id[:8]}..., 動作: {action}, 詳情: {details}")

def get_popular_searches() -> List[str]:
    """獲取熱門搜尋關鍵字（可用於推薦）"""
    # 這裡可以從資料庫或快取中獲取熱門搜尋
    return ["台中", "高海拔", "可帶寵物", "車停營位旁", "北部"]

if __name__ == "__main__":
    # 測試優化功能
    print("LINE Bot 優化模組載入完成")
    print("熱門搜尋:", get_popular_searches())