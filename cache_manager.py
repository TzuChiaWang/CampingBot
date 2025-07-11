"""
快取管理工具
提供快取統計和管理功能
"""

from models import cache
import time

class CacheManager:
    @staticmethod
    def get_cache_stats():
        """獲取快取統計資訊"""
        total_keys = len(cache.cache)
        expired_keys = 0
        current_time = time.time()
        
        for key, (value, expiry) in cache.cache.items():
            if current_time >= expiry:
                expired_keys += 1
        
        return {
            'total_keys': total_keys,
            'active_keys': total_keys - expired_keys,
            'expired_keys': expired_keys,
            'cache_size': len(str(cache.cache))
        }
    
    @staticmethod
    def clear_expired():
        """清除過期的快取項目"""
        current_time = time.time()
        expired_keys = []
        
        for key, (value, expiry) in cache.cache.items():
            if current_time >= expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            del cache.cache[key]
        
        return len(expired_keys)
    
    @staticmethod
    def warm_up_cache():
        """預熱快取 - 預先載入常用資料"""
        from models import Campsite
        
        # 預載入第一頁資料
        Campsite.get_all_paginated(1, 12)
        
        # 預載入總數
        Campsite.get_total_count()
        
        return "快取預熱完成"

if __name__ == "__main__":
    # 測試快取管理功能
    manager = CacheManager()
    print("快取統計:", manager.get_cache_stats())
    print("清除過期項目:", manager.clear_expired())
    print("預熱快取:", manager.warm_up_cache())