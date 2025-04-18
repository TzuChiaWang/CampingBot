import multiprocessing

# 綁定的 IP 和端口
bind = "0.0.0.0:13215"

# 使用單一工作進程以減少資源使用
workers = 1

# 工作模式改為更輕量的 gthread
worker_class = "gthread"
threads = 2

# 增加超時時間但不要太長
timeout = 30

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
worker_connections = 100

# 降低每個工作進程的最大請求數
max_requests = 500
max_requests_jitter = 100

# 優雅關閉時間
graceful_timeout = 30

# 不預加載應用以節省內存
preload_app = False

# 限制緩衝區大小
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 健康檢查相關
keepalive = 2                    # 保持連接時間
worker_tmp_dir = "/dev/shm"      # 使用內存作為臨時目錄
forwarded_allow_ips = "*"        # 允許所有轉發的 IP
