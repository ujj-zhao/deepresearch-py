"""认证模块路由。"""

from fastapi import APIRouter

from ruoyi_fastapi.core.response import R

from . import service as captcha_service
from .schemas import CaptchaResponse, VerifyCaptchaRequest

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/captchaImage", response_model=R[CaptchaResponse], response_model_by_alias=True)
def get_captcha_image():
    """获取验证码图片。"""
    return R.ok(captcha_service.create_captcha())


@router.post("/verifyCaptcha", response_model=R[dict], response_model_by_alias=True)
def verify_captcha(body: VerifyCaptchaRequest):
    """验证验证码（校验失败抛 ServiceException，由全局处理器转统一响应）。"""
    captcha_service.validate_captcha(body.uuid, body.code)
    return R.ok({"success": True})
