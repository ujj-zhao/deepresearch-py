"""用户模块业务逻辑（对应若依 SysUserServiceImpl）。"""

from datetime import datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.data_scope import DataScope, apply_scope
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.core.security import hash_password
from ruoyi_fastapi.modules.dept.models import Dept
from ruoyi_fastapi.modules.post.models import Post
from ruoyi_fastapi.modules.post.schemas import PostResp
from ruoyi_fastapi.modules.role.models import Role
from ruoyi_fastapi.modules.role.schemas import RoleResp
from ruoyi_fastapi.modules.user.schemas import (
    ResetPwdReq,
    UserAuthRoleResp,
    UserChangeStatusReq,
    UserCreate,
    UserDTO,
    UserInfoResp,
    UserListResp,
    UserPageQuery,
    UserUpdate,
)

from .models import SysUser, UserPost, UserRole

ADMIN_USER_ID = 1  # 超级管理员用户（对应若依 SysUser.isAdmin）


def select_user_by_username(username: str, db: Session) -> SysUser | None:
    """根据用户名查询用户（对应若依 SysUserMapper.selectUserByUserName）。"""
    return db.execute(
        select(SysUser).where(SysUser.user_name == username)
    ).scalars().first()


def select_user_list(
    query: UserPageQuery, scope: DataScope, db: Session
) -> tuple[list[UserListResp], int]:
    """分页查询用户列表（对应若依 SysUserMapper.selectUserList），带数据权限过滤。

    多表部分字段聚合成扁平 DTO：select 部分列 + .mappings() + model_validate。
    """
    stmt = (
        select(
            SysUser.user_id,
            SysUser.dept_id,
            SysUser.user_name,
            SysUser.nick_name,
            SysUser.email,
            SysUser.phonenumber,
            SysUser.sex,
            SysUser.status,
            SysUser.login_ip,
            SysUser.login_date,
            SysUser.create_time,
            Dept.dept_name.label("dept_name"),  # label 显式命名联查列
        )
        .join(Dept, SysUser.dept_id == Dept.dept_id, isouter=True)  # left join：未挂部门也显示
        .where(SysUser.del_flag == "0")
    )
    if query.user_name:
        stmt = stmt.where(SysUser.user_name.like(f"%{query.user_name}%"))
    if query.phonenumber:
        stmt = stmt.where(SysUser.phonenumber.like(f"%{query.phonenumber}%"))
    if query.status:
        stmt = stmt.where(SysUser.status == query.status)
    if query.dept_id is not None:
        # 点击部门节点查该部门及其子树用户（对应若依 XML 的 find_in_set 子查询）
        subtree = select(Dept.dept_id).where(
            func.find_in_set(query.dept_id, Dept.ancestors)
        )
        stmt = stmt.where(
            or_(SysUser.dept_id == query.dept_id, SysUser.dept_id.in_(subtree))
        )

    # 数据权限过滤（对应若依 @DataScope + ${params.dataScope}）
    stmt = apply_scope(stmt, scope, dept_column=SysUser.dept_id, user_column=SysUser.user_id)

    # 两条 SQL：先 COUNT 总数，再取当前页
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(SysUser.user_id)
        .limit(query.page_size)
        .offset((query.page_num - 1) * query.page_size)
    ).mappings().all()
    return [UserListResp.model_validate(r) for r in rows], total


# ---------- 用户新增/修改页回显（对应若依 getInfo 的 GET / 与 GET /{userId}） ----------


def get_user_form_init(db: Session) -> UserInfoResp:
    """新增页初始化：返回全部角色与岗位（对应若依 getInfo 无 userId 分支）。"""
    return UserInfoResp(roles=_select_all_roles(db), posts=_select_all_posts(db))


def get_user_detail(user_id: int, db: Session) -> UserInfoResp:
    """修改页详情：用户 + 角色/岗位全量 + 已绑定 ID 回显（对应若依 getInfo 带 userId 分支）。

    非 admin 目标用户的角色列表过滤掉 admin 角色（对齐若依 isAdmin 分支判断）。
    """
    user = _require_user(db, user_id)
    roles = _select_all_roles(db)
    if user_id != ADMIN_USER_ID:
        roles = [r for r in roles if r.role_id != ADMIN_USER_ID]
    return UserInfoResp(
        user=UserDTO.model_validate(user),
        roles=roles,
        posts=_select_all_posts(db),
        role_ids=list(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id)).all()),
        post_ids=list(db.scalars(select(UserPost.post_id).where(UserPost.user_id == user_id)).all()),
    )


def _select_all_roles(db: Session) -> list[RoleResp]:
    """全部未删角色，按显示顺序排序。"""
    rows = db.scalars(
        select(Role).where(Role.del_flag == "0").order_by(Role.role_sort, Role.role_id)
    ).all()
    return [RoleResp.model_validate(r) for r in rows]


def _select_all_posts(db: Session) -> list[PostResp]:
    """全部岗位，按显示顺序排序。"""
    rows = db.scalars(select(Post).order_by(Post.post_sort, Post.post_id)).all()
    return [PostResp.model_validate(p) for p in rows]


# ---------- 增删改（对应若依 insertUser / updateUser / deleteUserByIds） ----------


def add_user(body: UserCreate, db: Session) -> bool:
    """新增用户（对应若依 insertUser：唯一性校验 + 密码哈希 + 关联绑定）。"""
    if not check_user_name_unique(body.user_name, None, db):
        raise ServiceException(f"新增用户'{body.user_name}'失败，登录账号已存在")
    if body.phonenumber and not check_phone_unique(body.phonenumber, None, db):
        raise ServiceException(f"新增用户'{body.user_name}'失败，手机号码已存在")
    if body.email and not check_email_unique(body.email, None, db):
        raise ServiceException(f"新增用户'{body.user_name}'失败，邮箱账号已存在")

    user = SysUser(**body.model_dump(exclude={"role_ids", "post_ids"}))
    user.password = hash_password(body.password)
    db.add(user)
    db.flush()  # 先拿到自增 user_id 再绑关联
    _insert_user_roles(user.user_id, body.role_ids, db)
    _insert_user_posts(user.user_id, body.post_ids, db)
    db.commit()
    return True


def update_user(body: UserUpdate, db: Session) -> bool:
    """修改用户（对应若依 updateUser：校验 + 更新字段 + 重建角色/岗位关联）。"""
    user = _require_user(db, body.user_id)
    _check_allowed(body.user_id)
    if body.phonenumber and not check_phone_unique(body.phonenumber, body.user_id, db):
        raise ServiceException(f"修改用户'{body.nick_name}'失败，手机号码已存在")
    if body.email and not check_email_unique(body.email, body.user_id, db):
        raise ServiceException(f"修改用户'{body.nick_name}'失败，邮箱账号已存在")

    for key, value in body.model_dump(exclude={"user_id", "role_ids", "post_ids"}).items():
        setattr(user, key, value)
    db.execute(delete(UserRole).where(UserRole.user_id == body.user_id))
    _insert_user_roles(body.user_id, body.role_ids, db)
    db.execute(delete(UserPost).where(UserPost.user_id == body.user_id))
    _insert_user_posts(body.user_id, body.post_ids, db)
    db.commit()
    return True


def delete_user_by_ids(user_ids: list[int], current_user_id: int, db: Session) -> bool:
    """批量删除用户（对应若依 deleteUserByIds，逻辑删除 del_flag='2'）。

    admin 用户不可删；当前登录用户不可删自己。
    """
    if ADMIN_USER_ID in user_ids:
        raise ServiceException("不允许操作超级管理员用户")
    if current_user_id in user_ids:
        raise ServiceException("当前用户不能删除")

    db.execute(update(SysUser).where(SysUser.user_id.in_(user_ids)).values(del_flag="2"))
    db.commit()
    return True


# ---------- 密码 / 状态 / 分配角色 ----------


def reset_pwd(body: ResetPwdReq, db: Session) -> bool:
    """重置用户密码（对应若依 resetPwd，BCrypt 哈希后落库）。"""
    _require_user(db, body.user_id)
    _check_allowed(body.user_id)
    db.execute(
        update(SysUser)
        .where(SysUser.user_id == body.user_id)
        .values(password=hash_password(body.password), pwd_update_date=datetime.now())
    )
    db.commit()
    return True


def change_status(body: UserChangeStatusReq, db: Session) -> bool:
    """账号启停（对应若依 changeStatus）。"""
    _require_user(db, body.user_id)
    _check_allowed(body.user_id)
    db.execute(
        update(SysUser).where(SysUser.user_id == body.user_id).values(status=body.status)
    )
    db.commit()
    return True


def get_user_auth_role(user_id: int, db: Session) -> UserAuthRoleResp:
    """分配角色页回显：用户 + 已绑定角色（对应若依 authRole 的 GET 接口）。"""
    user = _require_user(db, user_id)
    roles = db.scalars(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.role_id)
        .where(UserRole.user_id == user_id, Role.del_flag == "0")
        .order_by(Role.role_sort, Role.role_id)
    ).all()
    return UserAuthRoleResp(
        user=UserDTO.model_validate(user),
        roles=[RoleResp.model_validate(r) for r in roles],
    )


def insert_user_auth(user_id: int, role_ids: list[int], db: Session) -> bool:
    """执行用户分配角色（对应若依 authRole 的 PUT 接口：清空旧绑定后重建）。"""
    _require_user(db, user_id)
    db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    _insert_user_roles(user_id, role_ids, db)
    db.commit()
    return True


# ---------- 唯一性校验（对应若依 checkUnique 系列，均过滤已删记录） ----------


def check_user_name_unique(user_name: str, user_id: int | None, db: Session) -> bool:
    """登录账号唯一性校验。返回 True 表示可用。"""
    user = _find_by_unique(SysUser.user_name == user_name, user_id, db)
    return user is None


def check_phone_unique(phonenumber: str, user_id: int | None, db: Session) -> bool:
    """手机号唯一性校验（对应若依 checkPhoneUnique）。返回 True 表示可用。"""
    return _find_by_unique(SysUser.phonenumber == phonenumber, user_id, db) is None


def check_email_unique(email: str, user_id: int | None, db: Session) -> bool:
    """邮箱唯一性校验（对应若依 checkEmailUnique）。返回 True 表示可用。"""
    return _find_by_unique(SysUser.email == email, user_id, db) is None


def _find_by_unique(cond, user_id: int | None, db: Session) -> SysUser | None:
    """按唯一列查询未删用户，排除自身（修改场景）。"""
    stmt = select(SysUser).where(cond, SysUser.del_flag == "0")
    if user_id is not None:
        stmt = stmt.where(SysUser.user_id != user_id)
    return db.scalars(stmt).first()


# ---------- 内部辅助 ----------


def _require_user(db: Session, user_id: int) -> SysUser:
    user = db.get(SysUser, user_id)
    if user is None or user.del_flag != "0":
        raise ServiceException("用户不存在", code=404)
    return user


def _check_allowed(user_id: int) -> None:
    """操作允许性校验（对应若依 checkUserAllowed）：不允许操作超级管理员用户。"""
    if user_id == ADMIN_USER_ID:
        raise ServiceException("不允许操作超级管理员用户")


def _insert_user_roles(user_id: int, role_ids: list[int], db: Session) -> None:
    """批量绑定用户-角色关联（对应若依 insertUserRole）。"""
    db.add_all([UserRole(user_id=user_id, role_id=r) for r in role_ids])


def _insert_user_posts(user_id: int, post_ids: list[int], db: Session) -> None:
    """批量绑定用户-岗位关联（对应若依 insertUserPost）。"""
    db.add_all([UserPost(user_id=user_id, post_id=p) for p in post_ids])
