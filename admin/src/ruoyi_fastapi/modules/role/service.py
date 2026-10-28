"""角色模块业务逻辑（对应若依 SysRoleServiceImpl）。"""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.data_scope import DataScope, apply_scope
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.modules.dept.models import Dept
from ruoyi_fastapi.modules.login.schemas import RoleDTO
from ruoyi_fastapi.modules.user.models import SysUser, UserRole
from ruoyi_fastapi.modules.user.schemas import UserListResp

from .models import Role, RoleDept, RoleMenu
from .schemas import (
    RoleAuthUserPageQuery,
    RoleChangeStatusReq,
    RoleCreate,
    RoleDataScopeReq,
    RolePageQuery,
    RoleResp,
    RoleUpdate,
)

ADMIN_ROLE_ID = 1  # 超级管理员角色（对应若依 SysRole.isAdmin）


def select_roles_by_user_id(user_id: int, db: Session) -> list[RoleDTO]:
    """查询用户启用中的角色列表（对应若依 SysRoleMapper.selectRolePermissionByUserId）。

    过滤停用/已删角色，按显示顺序排序；供登录装配（会话快照）与数据权限计算使用。
    """
    stmt = (
        select(Role)
        .join(UserRole, Role.role_id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            Role.status == "0",
            Role.del_flag == "0",
        )
        .order_by(Role.role_sort)
    )
    return [RoleDTO.model_validate(r) for r in db.execute(stmt).scalars().all()]


# ---------- 角色管理（对应若依 SysRoleController / SysRoleServiceImpl） ----------


def _base_query() -> select:
    """公共查询：过滤已删，按显示顺序稳定排序（role_sort 相同再按主键，保证翻页不乱序）。"""
    return select(Role).where(Role.del_flag == "0").order_by(Role.role_sort, Role.role_id)


def get_role_list(query: RolePageQuery, db: Session) -> tuple[list[RoleResp], int]:
    """分页查询角色列表（对应若依 selectRoleList）。

    两条 SQL：先 COUNT 总条数，再 LIMIT/OFFSET 取当前页。
    """
    stmt = _base_query()
    if query.role_name:
        stmt = stmt.where(Role.role_name.like(f"%{query.role_name}%"))
    if query.role_key:
        stmt = stmt.where(Role.role_key.like(f"%{query.role_key}%"))
    if query.status:
        stmt = stmt.where(Role.status == query.status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.limit(query.page_size).offset((query.page_num - 1) * query.page_size)
    ).all()
    return [RoleResp.model_validate(r) for r in rows], total


def get_role_detail(role_id: int, db: Session) -> RoleResp:
    """角色详情（主键直查）。"""
    role = _require_role(db, role_id)
    return RoleResp.model_validate(role)


def get_role_options(db: Session) -> list[RoleResp]:
    """角色下拉框（对应若依 optionselect：全部未删角色）。"""
    return [RoleResp.model_validate(r) for r in db.scalars(_base_query()).all()]


def add_role(req: RoleCreate, db: Session) -> bool:
    """新增角色（对应若依 insertRole：唯一性校验 + 插入 + 批量绑定菜单）。"""
    if not check_role_name_unique(req.role_name, None, db):
        raise ServiceException(f"新增角色'{req.role_name}'失败，角色名称已存在")
    if not check_role_key_unique(req.role_key, None, db):
        raise ServiceException(f"新增角色'{req.role_name}'失败，角色权限已存在")

    role = Role(**req.model_dump(exclude={"menu_ids"}), del_flag="0")
    db.add(role)
    db.flush()  # 先拿到自增 role_id 再绑菜单
    _insert_role_menus(role.role_id, req.menu_ids, db)
    db.commit()
    return True


def update_role(req: RoleUpdate, db: Session) -> bool:
    """修改角色（对应若依 updateRole：校验 + 更新 + 重建角色-菜单关联）。

    修改后在线用户的权限会话不会自动刷新，需重新登录生效
    （若依新版会在此时踢掉在线会话，待接入会话管理后补齐）。
    """
    role = _require_role(db, req.role_id)
    _check_allowed(req.role_id)
    if not check_role_name_unique(req.role_name, req.role_id, db):
        raise ServiceException(f"修改角色'{req.role_name}'失败，角色名称已存在")
    if not check_role_key_unique(req.role_key, req.role_id, db):
        raise ServiceException(f"修改角色'{req.role_name}'失败，角色权限已存在")

    for key, value in req.model_dump(exclude={"role_id", "menu_ids"}).items():
        setattr(role, key, value)
    db.execute(delete(RoleMenu).where(RoleMenu.role_id == req.role_id))
    _insert_role_menus(req.role_id, req.menu_ids, db)
    db.commit()
    return True


def update_role_status(req: RoleChangeStatusReq, db: Session) -> bool:
    """角色启停（对应若依 changeStatus）。"""
    _require_role(db, req.role_id)
    _check_allowed(req.role_id)
    db.execute(
        update(Role).where(Role.role_id == req.role_id).values(status=req.status)
    )
    db.commit()
    return True


def update_role_data_scope(req: RoleDataScopeReq, db: Session) -> bool:
    """修改角色数据权限（对应若依 dataScope：更新范围 + 重建自定部门绑定）。"""
    _require_role(db, req.role_id)
    _check_allowed(req.role_id)
    db.execute(
        update(Role)
        .where(Role.role_id == req.role_id)
        .values(data_scope=req.data_scope)
    )
    db.execute(delete(RoleDept).where(RoleDept.role_id == req.role_id))
    db.add_all([RoleDept(role_id=req.role_id, dept_id=d) for d in req.dept_ids])
    db.commit()
    return True


def delete_role_by_ids(role_ids: list[int], db: Session) -> bool:
    """批量删除角色（对应若依 deleteRoleByIds，逻辑删除 del_flag='2'）。

    admin 角色不可删；已分配用户的角色不可删（对齐若依"角色已分配,不能删除"）。
    """
    for role_id in role_ids:
        _require_role(db, role_id)
        _check_allowed(role_id)
        if check_role_exist_user(role_id, db):
            raise ServiceException(f"角色{role_id}已分配用户,不能删除")

    db.execute(
        update(Role).where(Role.role_id.in_(role_ids)).values(del_flag="2")
    )
    db.commit()
    return True


def check_role_name_unique(role_name: str, role_id: int | None, db: Session) -> bool:
    """角色名称唯一性校验（对应若依 checkRoleNameUnique）。返回 True 表示可用。"""
    stmt = select(Role).where(
        Role.role_name == role_name, Role.del_flag == "0"
    )
    if role_id is not None:
        stmt = stmt.where(Role.role_id != role_id)
    return db.scalars(stmt).first() is None


def check_role_key_unique(role_key: str, role_id: int | None, db: Session) -> bool:
    """角色权限字符串唯一性校验（对应若依 checkRoleKeyUnique）。返回 True 表示可用。"""
    stmt = select(Role).where(Role.role_key == role_key, Role.del_flag == "0")
    if role_id is not None:
        stmt = stmt.where(Role.role_id != role_id)
    return db.scalars(stmt).first() is None


def check_role_exist_user(role_id: int, db: Session) -> bool:
    """角色是否已分配用户（对应若依 countUserRoleByRoleIds）。"""
    return db.scalar(
        select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
    ) > 0


def _require_role(db: Session, role_id: int) -> Role:
    role = db.get(Role, role_id)
    if role is None or role.del_flag != "0":
        raise ServiceException("角色不存在", code=404)
    return role


def _check_allowed(role_id: int) -> None:
    """操作允许性校验（对应若依 checkRoleAllowed）：不允许操作超级管理员角色。"""
    if role_id == ADMIN_ROLE_ID:
        raise ServiceException("不允许操作超级管理员角色")


def _insert_role_menus(role_id: int, menu_ids: list[int], db: Session) -> None:
    """批量绑定角色-菜单关联（对应若依 insertRoleMenu）。"""
    db.add_all([RoleMenu(role_id=role_id, menu_id=m) for m in menu_ids])


# ---------- 角色关联用户（对应若依 SysRoleController authUser 系列） ----------


def _user_rows_stmt() -> select:
    """用户行公共查询：JOIN 部门取部门名（对应 selectAllocatedList 的联查部分）。"""
    return (
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
            Dept.dept_name.label("dept_name"),
        )
        .join(Dept, SysUser.dept_id == Dept.dept_id, isouter=True)
        .where(SysUser.del_flag == "0")
    )


def select_allocated_users(
    query: RoleAuthUserPageQuery, scope: DataScope, db: Session
) -> tuple[list[UserListResp], int]:
    """已分配该角色的用户分页列表（对应若依 authUser/allocatedList，带数据权限）。"""
    stmt = _user_rows_stmt().join(
        UserRole, UserRole.user_id == SysUser.user_id
    ).where(UserRole.role_id == query.role_id)
    return _page_user_rows(stmt, query, scope, db)


def select_unallocated_users(
    query: RoleAuthUserPageQuery, scope: DataScope, db: Session
) -> tuple[list[UserListResp], int]:
    """未分配该角色的用户分页列表（对应若依 authUser/unallocatedList）。"""
    bound = select(UserRole.user_id).where(UserRole.role_id == query.role_id)
    stmt = _user_rows_stmt().where(SysUser.user_id.not_in(bound))
    return _page_user_rows(stmt, query, scope, db)


def _page_user_rows(
    stmt, query: RoleAuthUserPageQuery, scope: DataScope, db: Session
) -> tuple[list[UserListResp], int]:
    """用户行查询的公共收尾：条件过滤 + 数据权限 + 两段式分页。"""
    if query.user_name:
        stmt = stmt.where(SysUser.user_name.like(f"%{query.user_name}%"))
    if query.phonenumber:
        stmt = stmt.where(SysUser.phonenumber.like(f"%{query.phonenumber}%"))
    stmt = apply_scope(stmt, scope, dept_column=SysUser.dept_id, user_column=SysUser.user_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(SysUser.user_id)
        .limit(query.page_size)
        .offset((query.page_num - 1) * query.page_size)
    ).mappings().all()
    return [UserListResp.model_validate(r) for r in rows], total


def cancel_auth_user(role_id: int, user_id: int, db: Session) -> bool:
    """取消单个用户的角色授权（对应若依 authUser/cancel）。"""
    db.execute(
        delete(UserRole).where(UserRole.role_id == role_id, UserRole.user_id == user_id)
    )
    db.commit()
    return True


def cancel_auth_users(role_id: int, user_ids: list[int], db: Session) -> bool:
    """批量取消用户的角色授权（对应若依 authUser/cancelAll）。"""
    if not user_ids:
        return True
    db.execute(
        delete(UserRole).where(UserRole.role_id == role_id, UserRole.user_id.in_(user_ids))
    )
    db.commit()
    return True


def insert_auth_users(role_id: int, user_ids: list[int], db: Session) -> bool:
    """批量授权用户角色（对应若依 authUser/insertAll）。

    过滤已绑定用户后再插入，避免主键冲突导致整批失败。
    """
    if not user_ids:
        return True
    existing = set(
        db.scalars(
            select(UserRole.user_id).where(
                UserRole.role_id == role_id, UserRole.user_id.in_(user_ids)
            )
        ).all()
    )
    db.add_all(
        [UserRole(role_id=role_id, user_id=u) for u in user_ids if u not in existing]
    )
    db.commit()
    return True
