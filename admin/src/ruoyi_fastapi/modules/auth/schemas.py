"""认证模块的 Pydantic 请求/响应模型。"""

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel


class CaptchaResponse(CamelModel):
    """验证码响应（对齐若依 AjaxResult 中 captchaImage 的 data 结构）。"""

    captcha_enabled: bool = Field(description="是否开启验证码")
    uuid: str = Field(default="", description="验证码唯一标识")
    img: str = Field(default="", description="验证码图片（base64，不含 data: 前缀）")


class VerifyCaptchaRequest(CamelModel):
    """验证码校验请求。"""

    uuid: str = Field(description="验证码唯一标识")
    code: str = Field(description="用户输入的验证码")
