from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ruoyi_fastapi.core.response import R
from ruoyi_fastapi.core.dependencies import get_db
from . import service as login_service
from .schemas import GetInfoResp, LoginRequest, LoginResponse


router = APIRouter(prefix="/login", tags=["用户登录"])


"""登陆接口"""
@router.post(
    "",
    response_model = R[LoginResponse],
    description = "用户登录接口",
    )
def login(request: LoginRequest, http_request: Request, db: Session = Depends(get_db)) -> R[LoginResponse]:
    token = login_service.login(request.username, request.password, request.code, request.uuid, http_request, db)
    return R.ok(LoginResponse(token=token))

"""登出接口"""
@router.post(
    "/logout",
    summary = "退出登录",
    )
def logout(request: Request) -> R[None]:
    login_service.logout(request)
    return R.ok()

"""获取当前用户信息"""
@router.get(
    "/getInfo",
    response_model = R[GetInfoResp],
    summary = "获取当前用户信息",
    )
def get_info(request: Request) -> R[GetInfoResp]:
    return R.ok(login_service.get_info(request))

