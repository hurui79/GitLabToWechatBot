import os

# 服务端口
PORT = int(os.environ.get('PORT', 5000))

# 数据库路径
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'data', 'webhooks.db'))

# 日志保留天数
LOG_RETAIN_DAYS = int(os.environ.get('LOG_RETAIN_DAYS', 30))
