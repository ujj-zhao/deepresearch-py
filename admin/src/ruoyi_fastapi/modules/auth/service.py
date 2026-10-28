"""认证模块业务逻辑：验证码生成与校验。

验证码是带 TTL 的临时数据，只存 Redis，不落数据库：
- 生成时：答案写入 captcha_codes:{uuid}，图片直接返回前端
- 校验时：getdel 原子取出并删除（一次性使用），通过后写校验通过标记
"""

import base64
import random
import string
from uuid import uuid4
from captcha.image import ImageCaptcha
from ruoyi_fastapi.core.config import settings
from ruoyi_fastapi.core.constant import CAPTCHA_CODE_KEY, CAPTCHA_PASSED_KEY, CAPTCHA_EXPIRE
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.core.redis import redis_client
from .schemas import CaptchaResponse

# 图片生成器（进程内复用即可，无状态）
_image_captcha = ImageCaptcha(width=160, height=60)

# 字符验证码候选集：去掉易混淆的 0/O/1/l/I
_CHAR_POOL = string.ascii_uppercase + string.digits
_CHAR_POOL = "".join(c for c in _CHAR_POOL if c not in "0O1lI")


def is_captcha_enabled() -> bool:
    """验证码开关。

    TODO: sys_config 模块完成后改为读取 sys.account.captchaEnabled。
    """
    return True


def _generate_math() -> tuple[str, str]:
    """算术验证码：返回 (算式文本, 答案)。图片画算式，Redis 存答案。"""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    op = random.choice("+-*")
    answer = {"+": a + b, "-": a - b, "*": a * b}[op]
    return f"{a}{op}{b}=?", str(answer)


def _generate_char() -> tuple[str, str]:
    """字符验证码：返回 (文本, 文本)，画图与存储同值。"""
    text = "".join(random.choices(_CHAR_POOL, k=4))
    return text, text


def create_captcha() -> CaptchaResponse:
    """生成验证码：答案存 Redis，返回 uuid 与 base64 图片。"""
    if not is_captcha_enabled():
        return CaptchaResponse(captcha_enabled=False, uuid="", img="")

    code_uuid = str(uuid4())
    if settings.CAPTCHA_TYPE == "math":
        draw_text, answer = _generate_math()
    else:
        draw_text, answer = _generate_char()

    # 画图（画的是算式/字符，不是答案）→ base64
    buf = _image_captcha.generate(draw_text)
    img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    redis_client.setex(
        settings.CAPTCHA_CODE_KEY.format(code_uuid),
        settings.CAPTCHA_EXPIRE,
        answer,
    )
    return CaptchaResponse(captcha_enabled=True, uuid=code_uuid, img=img_b64)


def validate_captcha(code_uuid: str, code: str) -> None:
    """校验验证码（一次性使用）。

    Raises:
        ServiceException: 验证码已失效或校验错误
    """
    # getdel：取值并删除，一条命令原子完成，防止并发重复使用
    answer = redis_client.getdel(CAPTCHA_CODE_KEY.format(code_uuid))
    if answer is None:
        raise ServiceException("验证码已失效", code=400)
    if answer.lower() != code.lower():
        raise ServiceException("验证码错误", code=400)

    # 独立校验接口与登录之间的衔接标记，登录时消费（第 07 章）
    redis_client.setex(
        settings.CAPTCHA_PASSED_KEY.format(code_uuid),
        settings.CAPTCHA_EXPIRE,
        "1",
    )
