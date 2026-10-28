"""岗位路由（对齐若依 SysPostController，前缀 /system/post）。

静态路由（/list、/export、/optionselect）必须注册在 /{postId} 动态路由之前，
否则会被路径参数提前匹配吞掉。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.dependencies import get_db
from ruoyi_fastapi.core.enums import BusinessType
from ruoyi_fastapi.core.permissions import get_current_login_user, has_perms
from ruoyi_fastapi.core.response import PageResult, R
from ruoyi_fastapi.modules.login.schemas import LoginUser

from ..log.service import log
from . import service as post_service
from .schemas import PostCreate, PostPageQuery, PostResp, PostUpdate

router = APIRouter(prefix="/system/post", tags=["岗位管理"])


@router.get(
    "/list",
    response_model=PageResult[PostResp],
    response_model_by_alias=True,
    summary="查询岗位列表",
    dependencies=[Depends(has_perms("system:post:list"))],
)
def get_post_list(
    query: PostPageQuery = Depends(),
    db: Session = Depends(get_db),
) -> PageResult[PostResp]:
    """分页查询岗位列表（岗位名称模糊 / 岗位编码精确 / 状态过滤）。"""
    rows, total = post_service.get_post_list(query, db)
    return PageResult.of(rows=rows, total=total)


@router.post(
    "/export",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="导出岗位列表",
)
@log(title="岗位管理", business_type=BusinessType.EXPORT)
def export_post(
    query: PostPageQuery,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:post:export")),
) -> R[bool]:
    """导出岗位数据（Excel 生成待接入，当前占位）。"""
    return R.ok(post_service.export(db, query))


@router.get(
    "/optionselect",
    response_model=R[list[PostResp]],
    response_model_by_alias=True,
    summary="岗位下拉框列表",
    dependencies=[Depends(get_current_login_user)],  # 登录即可，无独立权限点
)
def get_post_options(
    userId: int | None = None,
    db: Session = Depends(get_db),
) -> R[list[PostResp]]:
    """岗位下拉框：不带 userId 查全部；带 userId 查该用户已绑定岗位。"""
    return R.ok(post_service.get_post_options(userId, db))


@router.get(
    "/{postId}",
    response_model=R[PostResp],
    response_model_by_alias=True,
    summary="岗位详情",
)
def get_post_detail(
    postId: int,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:post:query")),
) -> R[PostResp]:
    """根据岗位 ID 查询详情。"""
    return R.ok(post_service.get_post_detail(postId, db))


@router.post(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="新增岗位",
)
@log(title="岗位管理", business_type=BusinessType.INSERT)
def add_post(
    post: PostCreate,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:post:add")),
) -> R[bool]:
    """新增岗位（名称/编码唯一性校验）。"""
    return R.ok(post_service.add_post(post, db))


@router.put(
    "",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="修改岗位",
)
@log(title="岗位管理", business_type=BusinessType.UPDATE)
def update_post(
    post: PostUpdate,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:post:edit")),
) -> R[bool]:
    """修改岗位（唯一性校验排除自身）。"""
    return R.ok(post_service.update_post(post, db))


@router.delete(
    "/{postIds}",
    response_model=R[bool],
    response_model_by_alias=True,
    summary="删除岗位",
)
@log(title="岗位管理", business_type=BusinessType.DELETE)
def delete_post(
    postIds: str,
    db: Session = Depends(get_db),
    login_user: LoginUser = Depends(has_perms("system:post:remove")),
) -> R[bool]:
    """批量删除岗位（逗号分隔 ID，任一已分配用户则整体拒绝）。"""
    post_ids = [int(x) for x in postIds.split(",") if x.strip()]
    return R.ok(post_service.delete_post(post_ids, db))
