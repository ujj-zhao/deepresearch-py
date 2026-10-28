from ruoyi_fastapi.core.config import settings
import bcrypt
import jwt

def hash_password(password: str) -> str:
    """哈希密码。
    
    用于存储用户密码时，将明文密码转换为哈希值，避免直接存储明文密码。
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password:str, hashed_password:str) -> bool:
    """验证密码是否匹配。
    
    用于登录时，验证用户输入的明文密码是否与数据库中存储的哈希值匹配。
    """
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

# -------------------
# JWT 令牌
# -------------------
def decode_access_token(token: str) -> dict | None:
    """解析并校验令牌。

    签名错误、格式非法或已过期等任何无效情况统一返回 None。
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# -------------------
# 登录会话令牌（对应若依 TokenService：JWT 只携带 Redis 会话键，用户信息在会话里）
# -------------------
# JWT 中携带 Redis 会话键的 claim 名（对应若依 JwtConstants.LOGIN_USER_KEY）
LOGIN_USER_KEY = "login_user_key"

def create_login_token(user_key: str) -> str:
    """根据 Redis 会话键生成登录 JWT（对应若依 TokenService.createToken）。

    对齐若依：JWT 只携带会话键 claim，不设 exp/iat——
    过期完全由 Redis 会话 TTL 控制，配合滑动续期时同一 JWT 可长期使用。
    """
    payload = {LOGIN_USER_KEY: user_key}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def get_login_user_key(token: str) -> str | None:
    """从 JWT 解出 Redis 会话键（对应若依 TokenService.getLoginUser 的解析段）。

    令牌无效/过期返回 None。
    """
    payload = decode_access_token(token)
    return None if payload is None else payload.get(LOGIN_USER_KEY)