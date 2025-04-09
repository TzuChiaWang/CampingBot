# Gunicorn 配置
bind = "0.0.0.0:$PORT"  # Render 會自動設置 $PORT 環境變數
workers = 4  # 建議的工作進程數
worker_class = 'sync'  # 工作進程類型
timeout = 120  # 請求超時時間
