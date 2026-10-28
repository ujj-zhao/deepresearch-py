"""岗位模块业务逻辑（对应若依 SysPostServiceImpl）。"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.exception import ServiceException

from ..user.models import UserPost  # sys_user_post 关联表（在 user 模块）
from .models import Post
from .schemas import PostCreate, PostPageQuery, PostResp, PostUpdate


def _base_query() -> select:
    """公共查询：按显示顺序稳定排序（post_sort 相同时再按主键，保证分页翻页不乱序）。"""
    return select(Post).order_by(Post.post_sort, Post.post_id)


def get_post_list(
    query: PostPageQuery,
    db: Session,
) -> tuple[list[PostResp], int]:
    """分页查询岗位列表（对应若依 SysPostMapper.selectPostList）。

    两条 SQL：先 COUNT 总条数，再 LIMIT/OFFSET 取当前页。
    条件：岗位名称模糊 / 岗位编码精确 / 状态精确。
    """
    stmt = _base_query()
    if query.post_name:
        stmt = stmt.where(Post.post_name.like(f"%{query.post_name}%"))
    if query.post_code:
        stmt = stmt.where(Post.post_code == query.post_code)
    if query.status:
        stmt = stmt.where(Post.status == query.status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.limit(query.page_size).offset((query.page_num - 1) * query.page_size)
    ).all()
    return [PostResp.model_validate(p) for p in rows], total


def get_post_detail(post_id: int, db: Session) -> PostResp:
    """岗位详情（主键直查）。"""
    post = db.get(Post, post_id)
    if post is None:
        raise ServiceException("岗位不存在", code=404)
    return PostResp.model_validate(post)


def add_post(post: PostCreate, db: Session) -> bool:
    """新增岗位（对应若依 insertPost：名称/编码唯一性校验通过后插入）。"""
    if not check_post_name_unique(post.post_name, None, db):
        raise ServiceException(f"新增岗位'{post.post_name}'失败，岗位名称已存在")
    if not check_post_code_unique(post.post_code, None, db):
        raise ServiceException(f"新增岗位'{post.post_name}'失败，岗位编码已存在")

    db.add(Post(**post.model_dump()))
    db.commit()
    return True


def update_post(post: PostUpdate, db: Session) -> bool:
    """修改岗位（对应若依 updatePost：唯一性校验排除自身，工作单元模式提交）。"""
    if not check_post_name_unique(post.post_name, post.post_id, db):
        raise ServiceException(f"修改岗位'{post.post_name}'失败，岗位名称已存在")
    if not check_post_code_unique(post.post_code, post.post_id, db):
        raise ServiceException(f"修改岗位'{post.post_name}'失败，岗位编码已存在")

    db_post = db.get(Post, post.post_id)
    if db_post is None:
        raise ServiceException("岗位不存在", code=404)

    # 加载托管实体 → 改属性 → commit，由框架脏检查生成 UPDATE
    db_post.post_code = post.post_code
    db_post.post_name = post.post_name
    db_post.post_sort = post.post_sort
    db_post.status = post.status
    db_post.remark = post.remark
    db.commit()
    return True


def delete_post(post_ids: list[int], db: Session) -> bool:
    """批量删除岗位（对应若依 deletePostByIds：物理删除）。

    任一岗位已分配用户（sys_user_post 存在绑定）则整体失败，
    对齐若依"岗位已分配，不能删除"语义，不做部分删除。
    """
    if not post_ids:
        return True

    # 一条 IN 查询拿全部已分配的岗位，任一命中即抛异常
    bound_ids = db.scalars(
        select(UserPost.post_id).where(UserPost.post_id.in_(post_ids))
    ).all()
    if bound_ids:
        raise ServiceException("岗位已分配用户，不能删除")

    # sys_post 无 del_flag 列，走物理删除：一条 DELETE ... WHERE post_id IN (...)
    db.execute(delete(Post).where(Post.post_id.in_(post_ids)))
    db.commit()
    return True


def get_post_options(user_id: int | None, db: Session) -> list[PostResp]:
    """岗位下拉框选项（对应若依 optionselect）。

    不带 userId 查全部岗位；带 userId 查该用户已绑定岗位（用户管理编辑弹窗回显）。
    """
    stmt = _base_query()
    if user_id is not None:
        stmt = stmt.join(UserPost, UserPost.post_id == Post.post_id).where(
            UserPost.user_id == user_id
        )
    return [PostResp.model_validate(p) for p in db.scalars(stmt).all()]


def check_post_name_unique(post_name: str, post_id: int | None, db: Session) -> bool:
    """岗位名称唯一性校验（对应若依 checkPostNameUnique）。返回 True 表示可用。

    查到同名记录时：post_id 为 None（新增）不唯一；等于自身（修改）视为唯一。
    """
    post = db.scalars(select(Post).where(Post.post_name == post_name)).first()
    return post is None or post.post_id == post_id


def check_post_code_unique(post_code: str, post_id: int | None, db: Session) -> bool:
    """岗位编码唯一性校验（对应若依 checkPostCodeUnique）。返回 True 表示可用。"""
    post = db.scalars(select(Post).where(Post.post_code == post_code)).first()
    return post is None or post.post_id == post_id


def export(db: Session, query: PostPageQuery) -> bool:
    """导出岗位列表（对应若依 export）。

    TODO: 按条件查全量后生成 Excel（后续引入 openpyxl/pandas）。
    """
    raise NotImplementedError("TODO: 实现导出")
