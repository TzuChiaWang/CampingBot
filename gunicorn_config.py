import multiprocessing

# 綁定的 IP 和端口
bind = "0.0.0.0:3000"

# 減少工作進程數，使用固定數量而不是基於 CPU
workers = 2

# 工作模式改為更輕量的 gthread
worker_class = "gthread"
threads = 4

# 增加超時時間
timeout = 300

# 不使用守護進程
daemon = False

# 日誌級別
loglevel = "info"

# 日誌輸出到標準輸出
accesslog = "-"
errorlog = "-"

# 進程名稱
proc_name = "camping-bot"

# 降低並發連接數
worker_connections = 500

# 降低每個工作進程的最大請求數
max_requests = 1000
max_requests_jitter = 200

# 優雅關閉時間
graceful_timeout = 60

# 不預加載應用以節省內存
preload_app = False

# 限制緩衝區大小
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
