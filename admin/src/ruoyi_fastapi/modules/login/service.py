"""用户登录业务逻辑。"""

from datetime import datetime
from time import time
from uuid import uuid4

from fastapi import Request
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.config import settings
from ruoyi_fastapi.core.constant import (
    CAPTCHA_CODE_KEY,
    LOGIN_FAIL,
    LOGIN_SUCCESS,
    LOGIN_TOKEN_KEY,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PWD_ERR_CNT_KEY,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.core.ip_utils import get_client_ip, get_real_address_by_ip
from ruoyi_fastapi.core.redis import redis_client
from ruoyi_fastapi.core.security import create_login_token, get_login_user_key, verify_password
from ruoyi_fastapi.modules.log.service import record_logininfor

from ..config.service import select_captcha_enabled, select_config_by_key
from ..menu.service import select_perms_by_user_id
from ..role.service import select_roles_by_user_id
from ..user.schemas import UserDTO
from ..user.service import select_user_by_username
from .schemas import GetInfoResp, LoginUser, RoleDTO


def login(username: str, password: str, code: str, uuid: str, request: Request, db: Session) -> str:
    """用户登录（对应若依 SysLoginService.login）。"""
    try:
        # 验证码校验
        _verify_captcha(uuid, code, db)
        # 登录前置校验
        _login_pre_check(username, password, request, db)
        # 用户验证：查用户 + 密码锁定/比对
        login_user = _authenticate(username, password, request, db)
        # 生成 token：LoginUser 存 Redis 会话，JWT 只携带会话键
        token = _create_token(login_user, request)
    except ServiceException as e:
        # 失败分支统一记录登录日志（对齐若依：每个失败点都 recordLogininfor 后再抛）
        record_logininfor(username, LOGIN_FAIL, e.msg, request)
        raise
    # 登录成功日志（对应若依 recordLogininfor(LOGIN_SUCCESS)）
    record_logininfor(username, LOGIN_SUCCESS, "登录成功", request)
    return token


def _verify_captcha(uuid: str, code: str, db: Session) -> None:
    """验证码校验（对应若依 SysLoginService.validateCaptcha）。"""
    # 验证码开关关闭时跳过校验（卫语句提前返回，少一层嵌套）
    if not select_captcha_enabled(db):
        return

    verify_key = CAPTCHA_CODE_KEY.format(uuid or "")
    # getdel：取值并删除一条命令原子完成，验证码一次性消费，防止同码重复尝试
    captcha = redis_client.getdel(verify_key)
    if captcha is None:
        raise ServiceException("验证码已失效", code=400)
    if (code or "").lower() != captcha.lower():
        raise ServiceException("验证码错误", code=400)


def _login_pre_check(username: str, password: str, request: Request, db: Session) -> None:
    """登录前置校验（对应若依 SysLoginService.preLogin）。"""
    if not username or not password:
        raise ServiceException("用户名/密码不能为空", code=400)

    if len(password) < PASSWORD_MIN_LENGTH or len(password) > PASSWORD_MAX_LENGTH:
        raise ServiceException(
            f"密码长度须在 {PASSWORD_MIN_LENGTH}~{PASSWORD_MAX_LENGTH} 位之间", code=400
        )
    if len(username) < USERNAME_MIN_LENGTH or len(username) > USERNAME_MAX_LENGTH:
        raise ServiceException(
            f"用户名长度须在 {USERNAME_MIN_LENGTH}~{USERNAME_MAX_LENGTH} 位之间", code=400
        )

    # IP 黑名单：客户端 IP 命中 sys.login.blackIPList（逗号分隔）即拒绝
    black_str = select_config_by_key("sys.login.blackIPList", db)
    if black_str:
        client_ip = get_client_ip(request)
        black_list = {item.strip() for item in black_str.split(",") if item.strip()}
        if client_ip in black_list:
            raise ServiceException(f"很抱歉，您的IP：{client_ip}已被列入系统黑名单", code=400)


def _authenticate(username: str, password: str, request: Request, db: Session) -> LoginUser:
    """用户认证（对应若依 AuthenticationManager.authenticate + SysPasswordService）。"""
    # 根据 username 查询用户（对应 UserDetailsServiceImpl.loadUserByUsername）
    user = select_user_by_username(username, db)
    if user is None:
        raise ServiceException("登录用户不存在", code=400)

    # 密码错误次数超限锁定（对应 SysPasswordService.validate）
    pwd_err_cnt_key = PWD_ERR_CNT_KEY.format(username)
    pwd_err_cnt = redis_client.get(pwd_err_cnt_key)
    if pwd_err_cnt and int(pwd_err_cnt) >= settings.PWD_ERR_MAX:
        raise ServiceException(
            f"密码输入错误{settings.PWD_ERR_MAX}次，帐户锁定{settings.PWD_LOCK_TIME}分钟", code=400
        )

    # BCrypt 密码比对（对应 DaoAuthenticationProvider）
    if not verify_password(password, user.password or ""):
        # 错误计数 +1 并刷新锁定窗口
        redis_client.incr(pwd_err_cnt_key)
        redis_client.expire(pwd_err_cnt_key, settings.PWD_LOCK_TIME * 60)
        raise ServiceException("用户不存在/密码错误", code=400)

    # 登录成功：清空错误计数 + 更新登录 IP/时间（对应若依 recordLoginInfo）
    redis_client.delete(pwd_err_cnt_key)
    user.login_ip = get_client_ip(request)[:128]
    user.login_date = datetime.now()
    db.commit()

    # SysUser(ORM) → LoginUser(会话对象)：user 字段经 UserDTO 脱敏转换（不含 password）
    # roles/permissions 权限快照（对应若依 SysPermissionService.getRolePermission/getMenuPermission）
    # ipaddr/login_location/token 等会话属性由 _create_token 填充（对齐若依 TokenService.createToken）
    if user.user_id == 1:  # 超级管理员（对应若依 SysUser.isAdmin）
        role_list = [RoleDTO(role_id=1, role_key="admin", data_scope="1")]
        permissions = {"*:*:*"}
    else:
        role_list = select_roles_by_user_id(user.user_id, db)
        permissions = select_perms_by_user_id(user.user_id, db)
    return LoginUser(
        user_id=user.user_id,
        dept_id=user.dept_id,
        user=UserDTO.model_validate(user),
        roles=role_list,
        permissions=permissions,
    )


def _create_token(login_user: LoginUser, request: Request) -> str:
    """生成登录令牌（对应若依 TokenService.createToken + refreshToken）。"""
    # 会话键用随机 uuid（对齐若依 IdUtils.fastSimpleUUID()）
    user_key = uuid4().hex
    now = int(time() * 1000)
    login_user.token = user_key
    login_user.ipaddr = get_client_ip(request)
    login_user.login_location = get_real_address_by_ip(login_user.ipaddr)
    login_user.login_time = now
    login_user.expire_time = now + settings.TOKEN_EXPIRE_MINUTES * 60 * 1000
    # LoginUser 序列化存 Redis，过期与会话对齐
    redis_client.set(
        LOGIN_TOKEN_KEY.format(user_key),
        login_user.model_dump_json(),
        ex=settings.TOKEN_EXPIRE_MINUTES * 60,
    )
    return create_login_token(user_key)


def logout(request: Request) -> None:
    """退出登录（对应若依 SysLogoutService.logout）。

    JWT 无状态无法主动作废，删除其指向的 Redis 会话后令牌即失效：
    后续请求解析出的会话键在 Redis 中查不到，鉴权自然失败。
    """
    auth = request.headers.get(settings.TOKEN_HEADER, "")
    prefix = settings.TOKEN_PREFIX
    if not auth.startswith(prefix):
        return  # 未携带令牌的登出直接忽略
    user_key = get_login_user_key(auth[len(prefix):].strip())
    if not user_key:
        return

    session_key = LOGIN_TOKEN_KEY.format(user_key)
    login_user_json = redis_client.get(session_key)
    redis_client.delete(session_key)
    if login_user_json:
        login_user = LoginUser.model_validate_json(login_user_json)
        record_logininfor(login_user.user.user_name, LOGIN_SUCCESS, "退出成功", request)


def get_login_user(request: Request) -> LoginUser:
    """解析当前登录会话（对应若依 TokenService.getLoginUser + SecurityUtils.getLoginUser）。

    令牌缺失/无效/会话过期统一抛 401；受保护接口可将其作为 FastAPI 依赖复用。
    """
    auth = request.headers.get(settings.TOKEN_HEADER, "")
    prefix = settings.TOKEN_PREFIX
    if not auth.startswith(prefix):
        raise ServiceException("登录状态已过期", code=401)
    user_key = get_login_user_key(auth[len(prefix):].strip())
    session_json = redis_client.get(LOGIN_TOKEN_KEY.format(user_key)) if user_key else None
    if session_json is None:
        raise ServiceException("登录状态已过期", code=401)
    return LoginUser.model_validate_json(session_json)


def get_info(request: Request) -> GetInfoResp:
    """获取当前用户信息（对应若依 SysLoginController.getInfo）。

    roles/permissions 直接取自会话快照（登录时由 _authenticate 装配），
    admin 特判也在装配层完成，此处无需重复处理。
    """
    login_user = get_login_user(request)
    role_keys = [r.role_key for r in (login_user.roles or [])]
    return GetInfoResp(
        user=login_user.user,
        roles=role_keys,
        permissions=login_user.permissions or set(),
    )
