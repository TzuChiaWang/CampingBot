import multiprocessing

# 綁定的 IP 和端口
bind = "0.0.0.0:3000"

# 工作進程數
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超時時間
timeout = 120

# 是否守護進程
daemon = False

# 日誌級別
loglevel = "info"

# 訪問日誌格式
accesslog = "-"  # "-" 表示標準輸出
errorlog = "-"   # "-" 表示標準輸出

# 進程名稱
proc_name = "camping_bot"

# 最大客戶端並發數量
worker_connections = 1000

# 限制每個工作進程處理的請求數
max_requests = 2000
max_requests_jitter = 400

# 優雅的工作模式
graceful_timeout = 30

# 預加載應用
preload_app = True
