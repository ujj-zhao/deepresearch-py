"""应用配置。

使用 pydantic-settings 从环境变量或 `.env` 文件加载配置。
对应若依 Java 版 application.yml。
"""

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置。所有字段从 .env 读取，缺省值见默认。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # 应用
    APP_NAME: str = "RuoYi-FastAPI"
    DEBUG: bool = True

    # MySQL
    MYSQL_DRIVER: str = "pymysql"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "ruoyi_fastapi"
    MYSQL_CHARSET: str = "utf8mb4"

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # IP 归属地查询（对应若依 ruoyi.addressEnabled）
    ADDRESS_ENABLED: bool = True

    # JWT / Token（鉴权层用，第 07 章）
    TOKEN_HEADER: str = "Authorization"
    TOKEN_PREFIX: str = "Bearer "
    # secrets.token_urlsafe(64) 生成，须 >= 64 字节（RFC 7518 HS512 要求）
    JWT_SECRET_KEY: str = "qCXqEMjHifMGssH59mVQaXFjdqnvLq1QLOpHDX34CIjWebVWcWIFSdiY6z8rbgeLE71QDKqHJGH8r2UrFugDwA"
    JWT_ALGORITHM: str = "HS512"  # 对齐若依 SignatureAlgorithm.HS512
    TOKEN_EXPIRE_MINUTES: int = 30  # Redis 登录会话有效期（分钟），对齐若依 token.expireTime

    # 验证码（第 08 章）
    CAPTCHA_TYPE: str = "math"  # math 算术 / char 字符
    CAPTCHA_EXPIRE: int = 120   # 验证码有效期（秒）
    CAPTCHA_CODE_KEY: str = "captcha_codes:{}"
    # 验证码校验通过标记（独立校验接口与登录之间的衔接），值为 "1"
    CAPTCHA_PASSED_KEY: str = "captcha_passed:{}"

    # 密码错误限制（第 09 章）
    PWD_ERR_MAX: int = 5      # 最大错误次数
    PWD_LOCK_TIME: int = 10   # 锁定时间（分钟）

    # CORS / 防盗链（第 23 章）
    CORS_ORIGINS: list[str] = ["*"]
    REFERER_ENABLED: bool = False
    REFERER_ALLOWED_DOMAINS: list[str] = ["localhost", "127.0.0.1"]

    # 文件上传（第 21 章）
    UPLOAD_PATH: str = "/tmp/ruoyi/upload"
    UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_ALLOWED_EXT: list[str] = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".txt", ".md"]

    @property
    def mysql_url(self) -> str:
        """生成 SQLAlchemy 可用的 MySQL 连接串。"""
        return (
            f"mysql+{self.MYSQL_DRIVER}://{quote_plus(self.MYSQL_USER)}:"
            f"{quote_plus(self.MYSQL_PASSWORD)}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/"
            f"{self.MYSQL_DB}?charset={self.MYSQL_CHARSET}"
        )

    @property
    def redis_url(self) -> str:
        """生成 redis-py 可用的 Redis 连接串。"""
        auth = f":{quote_plus(self.REDIS_PASSWORD)}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
