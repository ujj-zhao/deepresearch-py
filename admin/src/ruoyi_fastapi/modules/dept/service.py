"""部门业务逻辑（对应若依 SysDeptServiceImpl）。"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.modules.role.models import RoleDept
from ruoyi_fastapi.modules.user.models import SysUser

from .models import Dept
from .schemas import DeptAddReq, DeptResp, DeptUpdateReq, RoleDeptTreeResp, TreeSelectResp


def _base_query() -> select:
    """公共查询：过滤已删除，按 父id + 显示顺序 排序（前端组树依赖稳定排序）。"""
    return (
        select(Dept)
        .where(Dept.del_flag == "0")
        .order_by(Dept.parent_id, Dept.order_num, Dept.dept_id)
    )


def get_dept_list(
    db: Session,
    *,
    dept_name: str | None = None,
    status: str | None = None,
    exclude_dept_id: int | None = None,
) -> list[DeptResp]:
    """部门列表（对应 selectDeptList）。

    exclude_dept_id 非 None 时排除该部门及其整个子树
    （find_in_set 精确匹配祖级链，避免 LIKE 子串误伤 101/1011）。
    """
    stmt = _base_query()
    if dept_name:
        stmt = stmt.where(Dept.dept_name.like(f"%{dept_name}%"))
    if status:
        stmt = stmt.where(Dept.status == status)
    if exclude_dept_id is not None:
        stmt = stmt.where(
            Dept.dept_id != exclude_dept_id,
            func.find_in_set(exclude_dept_id, Dept.ancestors) == 0,
        )
    return [DeptResp.model_validate(d) for d in db.scalars(stmt).all()]


def build_tree_select(depts: list[DeptResp]) -> list[TreeSelectResp]:
    """内存组树：一次遍历按 parent_id 挂 children，无 N+1（对应 buildDeptTreeSelect）。"""
    node_map = {d.dept_id: TreeSelectResp(id=d.dept_id, label=d.dept_name) for d in depts}
    roots: list[TreeSelectResp] = []
    for d in depts:
        node = node_map[d.dept_id]
        parent_node = node_map.get(d.parent_id)
        if parent_node is None:
            roots.append(node)
        else:
            parent_node.children.append(node)
    return roots


def get_tree_select(db: Session) -> list[TreeSelectResp]:
    """下拉部门树：仅正常状态（对应 selectDeptTreeList）。"""
    return build_tree_select(get_dept_list(db, status="0"))


def get_role_dept_tree(db: Session, role_id: int) -> RoleDeptTreeResp:
    """角色部门树 + 已勾选部门（对应 roleDeptTreeselect）。

    树含停用部门（勾选回显需要完整树），勾选列表来自 sys_role_dept。
    """
    tree = build_tree_select(get_dept_list(db))
    checked = list(db.scalars(select(RoleDept.dept_id).where(RoleDept.role_id == role_id)).all())
    return RoleDeptTreeResp(checked_keys=checked, depts=tree)


def get_dept_detail(db: Session, dept_id: int) -> DeptResp:
    """部门详情，按父链补父部门名称（对应 selectDeptById）。"""
    dept = _require_dept(db, dept_id)
    resp = DeptResp.model_validate(dept)
    parent = db.get(Dept, dept.parent_id) if dept.parent_id else None
    if parent is not None:
        resp.parent_name = parent.dept_name
    return resp


def _require_dept(db: Session, dept_id: int) -> Dept:
    dept = db.get(Dept, dept_id)
    if dept is None or dept.del_flag != "0":
        raise ServiceException("部门不存在")
    return dept


def _require_parent(db: Session, parent_id: int) -> Dept:
    """上级部门必须存在且为正常状态。"""
    parent = db.get(Dept, parent_id)
    if parent is None or parent.del_flag != "0":
        raise ServiceException("上级部门不存在")
    if parent.status != "0":
        raise ServiceException("上级部门已停用,不允许新增/调整")
    return parent


def _check_name_unique(
    db: Session, parent_id: int, dept_name: str, exclude_id: int | None = None
) -> None:
    """同级部门名称唯一校验（对应 checkDeptNameUnique）。"""
    stmt = (
        select(func.count())
        .select_from(Dept)
        .where(Dept.parent_id == parent_id, Dept.dept_name == dept_name, Dept.del_flag == "0")
    )
    if exclude_id is not None:
        stmt = stmt.where(Dept.dept_id != exclude_id)
    if db.scalar(stmt):
        raise ServiceException(f"同级下已存在名称为「{dept_name}」的部门")


def add_dept(db: Session, req: DeptAddReq) -> None:
    """新增部门：父部门正常 + 同级唯一，ancestors 续接父链（对应 insertDept）。"""
    parent = _require_parent(db, req.parent_id)
    _check_name_unique(db, req.parent_id, req.dept_name)
    dept = Dept(
        parent_id=req.parent_id,
        ancestors=f"{parent.ancestors},{parent.dept_id}",
        dept_name=req.dept_name,
        order_num=req.order_num,
        leader=req.leader,
        phone=req.phone,
        email=req.email,
        status=req.status,
        del_flag="0",
    )
    db.add(dept)
    db.commit()


def update_dept(db: Session, req: DeptUpdateReq) -> None:
    """修改部门：防环 + 同级唯一 + 停用校验 + ancestors 级联更新（对应 updateDept）。"""
    dept = _require_dept(db, req.dept_id)
    if req.dept_id == req.parent_id:
        raise ServiceException("修改部门失败,上级部门不能是自己")
    new_parent = _require_parent(db, req.parent_id)
    if str(req.dept_id) in (new_parent.ancestors or "").split(","):
        raise ServiceException("修改部门失败,上级部门不能选择自己的子部门")
    _check_name_unique(db, req.parent_id, req.dept_name, exclude_id=req.dept_id)
    if req.status == "1" and dept.status == "0":
        normal_children = db.scalar(
            select(func.count())
            .select_from(Dept)
            .where(Dept.parent_id == req.dept_id, Dept.status == "0", Dept.del_flag == "0")
        )
        if normal_children:
            raise ServiceException("修改部门失败,该部门包含未停用的子部门")

    old_ancestors = dept.ancestors or ""
    new_ancestors = f"{new_parent.ancestors},{new_parent.dept_id}"
    dept.parent_id = req.parent_id
    dept.ancestors = new_ancestors
    dept.dept_name = req.dept_name
    dept.order_num = req.order_num
    dept.leader = req.leader
    dept.phone = req.phone
    dept.email = req.email
    dept.status = req.status
    db.commit()

    if old_ancestors != new_ancestors:
        # 换父后级联修正所有子孙的祖级链（对应 updateDeptChildren 的 replace 语义）
        db.execute(
            update(Dept)
            .where(func.find_in_set(req.dept_id, Dept.ancestors))
            .values(ancestors=func.replace(Dept.ancestors, old_ancestors, new_ancestors))
        )
        db.commit()


def delete_dept(db: Session, dept_id: int) -> None:
    """删除部门：逻辑删除（del_flag='2'）；有子部门或挂有用户则拒绝（对应 deleteDeptById）。"""
    if db.scalar(
        select(func.count())
        .select_from(Dept)
        .where(Dept.parent_id == dept_id, Dept.del_flag == "0")
    ):
        raise ServiceException("存在下级部门,不允许删除")
    if db.scalar(
        select(func.count())
        .select_from(SysUser)
        .where(SysUser.dept_id == dept_id, SysUser.del_flag == "0")
    ):
        raise ServiceException("部门下存在用户,不允许删除")
    db.execute(update(Dept).where(Dept.dept_id == dept_id).values(del_flag="2"))
    db.commit()
