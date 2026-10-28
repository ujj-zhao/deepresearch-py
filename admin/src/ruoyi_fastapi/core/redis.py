from ruoyi_fastapi.core.config import settings
from redis import Redis
from redis.connection import ConnectionPool

# 全局唯一连接池：进程内共享，禁止多处重复创建
redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    encoding="utf-8",
    max_connections=50,        # 最大连接数，超过后等待连接池回收
    health_check_interval=30,          # 空闲连接保活探测，等价于 db.py pool_pre_ping
    socket_connect_timeout = 3,         # 连接超时时间，单位秒
    socket_timeout = 3,             # 读写超时时间，单位秒
)

# 全局唯一客户端：构造时不建连，第一条命令才真正连接
redis_client = Redis(connection_pool=redis_pool)