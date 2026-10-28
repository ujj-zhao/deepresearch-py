"""security.py 本地验证脚本（开发调试用，不属于生产代码）。

覆盖 BCrypt 密码哈希与 JWT 令牌的正常路径与异常路径。
全部断言通过时退出码为 0，否则为 1。

运行：
    uv run python scripts/security_demo.py
"""

from datetime import datetime, timedelta, timezone

import jwt

from ruoyi_fastapi.core.config import settings
from ruoyi_fastapi.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

_results: list[bool] = []


def check(label: str, actual: object, expected: object) -> None:
    """比对实际值与期望值，打印并累计结果。"""
    ok = actual == expected
    _results.append(ok)
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"         期望: {expected!r}")
        print(f"         实际: {actual!r}")


def demo_hash() -> None:
    """BCrypt 密码哈希。"""
    print("\n=== 1. 密码哈希（BCrypt）===")

    plain = "admin123"
    h1 = hash_password(plain)
    h2 = hash_password(plain)

    print(f"  哈希串: {h1}")

    check("哈希串以 $2b$ 开头（BCrypt 标识）", h1.startswith("$2b$"), True)
    check("哈希串长度为 60（BCrypt 固定输出长度）", len(h1), 60)
    check("同一密码两次哈希结果不同（盐随机）", h1 != h2, True)
    check("正确密码校验通过", verify_password(plain, h1), True)
    check("错误密码校验失败", verify_password("admin124", h1), False)
    check("空密码不会误判为通过", verify_password("", h1), False)
    check(
        "非法哈希串（脏数据）返回 False 而不抛异常",
        verify_password(plain, "not-a-valid-hash"),
        False,
    )


def demo_token() -> None:
    """JWT 正常签发与解析。"""
    print("\n=== 2. JWT 令牌签发与解析 ===")

    token = create_access_token(user_id=1, username="admin")
    print(f"  令牌: {token}")

    payload = decode_access_token(token)
    print(f"  payload: {payload}")

    check("令牌由三段组成（header.payload.signature）", len(token.split(".")), 3)
    check("解析成功（非 None）", payload is not None, True)
    check("sub 为字符串 '1'（JWT 规范要求）", payload["sub"], "1")
    check("username 正确", payload["username"], "admin")
    check("包含 iat 与 exp 声明", {"iat", "exp"} <= set(payload), True)
    check(
        f"有效期与配置一致（{settings.JWT_EXPIRE_MINUTES} 分钟）",
        payload["exp"] - payload["iat"],
        settings.JWT_EXPIRE_MINUTES * 60,
    )


def demo_token_failures() -> None:
    """JWT 异常路径。"""
    print("\n=== 3. JWT 异常路径 ===")

    now = datetime.now(timezone.utc)

    # 已过期：exp 早于当前时间
    expired = jwt.encode(
        {
            "sub": "1",
            "username": "admin",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    check("过期令牌解析结果为 None", decode_access_token(expired), None)

    # 签名被篡改
    head, body, _ = create_access_token(1, "admin").split(".")
    check(
        "签名被篡改后解析结果为 None",
        decode_access_token(f"{head}.{body}.{'x' * 32}"),
        None,
    )

    # 用其他密钥签发（模拟伪造）
    forged = jwt.encode(
        {"sub": "1", "exp": now + timedelta(minutes=5)},
        "wrong-secret-key",
        algorithm=settings.JWT_ALGORITHM,
    )
    check("其他密钥签发的令牌解析结果为 None", decode_access_token(forged), None)

    # 非法字符串
    check("非 JWT 字符串解析结果为 None", decode_access_token("garbage"), None)


def main() -> int:
    print("=== 配置 ===")
    print(f"  JWT_ALGORITHM : {settings.JWT_ALGORITHM}")
    print(f"  JWT 有效期    : {settings.JWT_EXPIRE_MINUTES} 分钟")
    print(
        "  JWT_SECRET_KEY: "
        + ("已配置" if settings.JWT_SECRET_KEY else "缺失")
        + "（生产必须替换为强随机值）"
    )

    demo_hash()
    demo_token()
    demo_token_failures()

    passed = sum(_results)
    total = len(_results)
    print(f"\n=== 结果: {passed}/{total} 通过 ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())