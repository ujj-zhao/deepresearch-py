"""菜单模块业务逻辑。"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.modules.role.models import Role, RoleMenu
from ruoyi_fastapi.modules.user.models import UserRole

from .models import Menu
from .schemas import (
    MenuCreate,
    MenuResp,
    MenuTreeSelectResp,
    MenuUpdate,
    MetaResp,
    RoleMenuTreeResp,
    RouterResp,
)

# 路由组件常量（对齐若依 UserConstants）
LAYOUT = "Layout"  # 一级目录/一级菜单壳组件
PARENT_VIEW = "ParentView"  # 非顶级目录组件（Layout 内嵌套的子容器）
INNER_LINK = "InnerLink"  # 内链组件（iframe 打开 http 链接）
NO_FRAME = 1  # is_frame=1 表示非外链
TYPE_DIR = "M"  # 目录
TYPE_MENU = "C"  # 菜单
HTTP_PREFIXES = ("http://", "https://")


def get_routers(user_id: int, db: Session) -> list[RouterResp]:
    """获取前端路由配置（对应若依 SysLoginController.getRouters 调用链）。"""
    menus = select_menu_tree_by_user_id(user_id, db)  # ① 查：平铺列表
    tree = build_menu_tree(menus)  # ② 建树
    return build_routers(tree)  # ③ 组装 RouterVo


def select_menu_tree_by_user_id(user_id: int, db: Session) -> list[MenuResp]:
    """查询用户可见菜单（平铺），对应若依 selectMenuTreeAll / selectMenuTreeByUserId。

    超级管理员查全量，其他用户经 user_role → role_menu 联查。
    """
    stmt = select(Menu).where(
        Menu.menu_type.in_((TYPE_DIR, TYPE_MENU)),  # 按钮 F 不生成路由
        Menu.status == "0",
    )
    if user_id != 1:  # 非超级管理员追加角色联查
        stmt = (
            stmt.join(RoleMenu, Menu.menu_id == RoleMenu.menu_id)
            .join(UserRole, RoleMenu.role_id == UserRole.role_id)
            .join(Role, UserRole.role_id == Role.role_id)
            .where(UserRole.user_id == user_id, Role.status == "0")
        )
    rows = db.execute(stmt.order_by(Menu.parent_id, Menu.order_num)).scalars().all()
    # ORM 平铺 → MenuResp 平铺，children 留给 build_menu_tree 填充
    return [MenuResp.model_validate(m) for m in rows]


def select_perms_by_user_id(user_id: int, db: Session) -> set[str]:
    """查询用户菜单权限标识集合（对应若依 SysMenuMapper.selectMenuPermsByUserId）。

    四表联查 user → user_role → role_menu → menu；比若依原版多过滤了
    菜单/角色的停用状态（停用菜单的按钮权限不应继续生效）。
    """
    stmt = (
        select(Menu.perms)
        .join(RoleMenu, Menu.menu_id == RoleMenu.menu_id)
        .join(UserRole, RoleMenu.role_id == UserRole.role_id)
        .join(Role, UserRole.role_id == Role.role_id)
        .where(
            UserRole.user_id == user_id,
            Menu.status == "0",
            Role.status == "0",
            Role.del_flag == "0",
            Menu.perms != "",
        )
    )
    return set(db.execute(stmt).scalars().all())


def build_menu_tree(menus: list[MenuResp]) -> list[MenuResp]:
    """平铺菜单 → 树（对应若依 SysMenuServiceImpl.getChildPerms 递归建树）。

    按 parent_id 分组索引，一次遍历完成，避免逐层递归查找。
    """
    by_parent: dict[int, list[MenuResp]] = {}
    for m in menus:
        by_parent.setdefault(m.parent_id, []).append(m)

    def attach(node: MenuResp) -> MenuResp:
        node.children = by_parent.get(node.menu_id, [])
        for child in node.children:
            attach(child)
        return node

    return [attach(n) for n in by_parent.get(0, [])]


def _meta_link(menu: MenuResp) -> str | None:
    """内链地址（对齐若依 MetaVo 四参构造：仅 http(s) 开头才赋值，否则 None）。

    前端 AppMain 以 meta.link 是否非空决定渲染组件还是 iframe，
    普通菜单的相对路径（如 "user"）不能作为 link 返回。
    """
    path = menu.path or ""
    return path if path.startswith(HTTP_PREFIXES) else None


def build_routers(menus: list[MenuResp]) -> list[RouterResp]:
    """菜单树 → 前端路由配置树（对应若依 SysMenuServiceImpl.buildMenus）。"""
    routers: list[RouterResp] = []
    for menu in menus:
        router = RouterResp(
            name=_route_name(menu),
            path=_router_path(menu),
            component=_component(menu),
            hidden=menu.visible == "1",  # 语义反转：visible=0 显示
            query=menu.query,
            meta=MetaResp(
                title=menu.menu_name,
                icon=menu.icon,
                no_cache=menu.is_cache == "1",
                link=_meta_link(menu),
            ),
        )
        if menu.children and menu.menu_type == TYPE_DIR:
            # 目录：始终显示 + noRedirect，递归组装子路由
            router.always_show = True
            router.redirect = "noRedirect"
            router.children = build_routers(menu.children)
        elif _is_menu_frame(menu):
            # 一级菜单：Layout 框架必须有目录层，包壳后真实页面下沉到 children
            router.meta = None
            router.children = [
                RouterResp(
                    name=_capitalize(menu.path),
                    path=menu.path or "",
                    component=menu.component,
                    query=menu.query,
                    meta=MetaResp(
                        title=menu.menu_name,
                        icon=menu.icon,
                        no_cache=menu.is_cache == "1",
                        link=_meta_link(menu),
                    ),
                )
            ]
        elif menu.parent_id == 0 and _is_inner_link(menu):
            # 顶级内链：外壳指向 /，子路由用 InnerLink 组件打开
            router.meta = MetaResp(title=menu.menu_name, icon=menu.icon)
            router.path = "/"
            router.children = [
                RouterResp(
                    path=_inner_link_replace(menu.path),
                    component=INNER_LINK,
                    meta=MetaResp(title=menu.menu_name, icon=menu.icon, link=menu.path),
                )
            ]
        routers.append(router)
    return routers


def _is_menu_frame(menu: MenuResp) -> bool:
    """一级菜单（parent_id=0 且类型 C 且非外链），对应若依 SysMenu.isMenuFrame。"""
    return menu.parent_id == 0 and menu.menu_type == TYPE_MENU and menu.is_frame == NO_FRAME


def _is_inner_link(menu: MenuResp) -> bool:
    """内链：非外链方式且 path 以 http 开头（系统内 iframe 打开），对应 SysMenu.isInnerLink。"""
    return menu.is_frame == NO_FRAME and (menu.path or "").startswith(HTTP_PREFIXES)


def _is_parent_view(menu: MenuResp) -> bool:
    """非顶级目录 → ParentView，对应 SysMenu.isParentView。"""
    return menu.parent_id != 0 and menu.menu_type == TYPE_DIR


def _route_name(menu: MenuResp) -> str:
    """路由名：route_name 优先（内链除外），否则 path 首字母大写，对应 getRouteName。"""
    if menu.route_name and not _is_inner_link(menu):
        return menu.route_name
    return _capitalize(menu.path)


def _router_path(menu: MenuResp) -> str:
    """路由地址规则，对应 SysMenu.getRouterPath。"""
    router_path = menu.path or ""
    if menu.parent_id != 0 and _is_inner_link(menu):
        router_path = _inner_link_replace(router_path)
    if menu.parent_id == 0 and menu.menu_type == TYPE_DIR and menu.is_frame == NO_FRAME:
        router_path = "/" + router_path
    elif _is_menu_frame(menu):
        router_path = "/"
    return router_path


def _component(menu: MenuResp) -> str:
    """组件规则，对应 SysMenu.getComponent。"""
    if menu.component and not _is_menu_frame(menu):
        return menu.component
    if not menu.component and menu.parent_id != 0 and _is_inner_link(menu):
        return INNER_LINK
    if not menu.component and _is_parent_view(menu):
        return PARENT_VIEW
    return LAYOUT


def _inner_link_replace(path: str) -> str:
    """去掉 http:// 或 https:// 前缀，对应 SysMenu.innerLinkReplaceEach。"""
    for prefix in HTTP_PREFIXES:
        if path.startswith(prefix):
            return path[len(prefix):]
    return path


def _capitalize(s: str | None) -> str:
    """首字母大写（str.capitalize 会把其余字母变小写，故手动切片）。"""
    s = s or ""
    return s[:1].upper() + s[1:]


# ---------- 菜单管理（对应若依 SysMenuController / SysMenuServiceImpl） ----------


def select_menu_list(
    menu_name: str | None, status: str | None, user_id: int, db: Session
) -> list[MenuResp]:
    """菜单管理列表（对应若依 selectMenuList），平铺不分页。

    admin 查全量；其他用户仅能看到自己角色绑定的菜单（IN 子查询代替 DISTINCT 联查）。
    """
    stmt = select(Menu)
    if menu_name:
        stmt = stmt.where(Menu.menu_name.like(f"%{menu_name}%"))
    if status:
        stmt = stmt.where(Menu.status == status)
    if user_id != 1:  # 非超级管理员：可见范围收敛到角色绑定的菜单
        bound = (
            select(RoleMenu.menu_id)
            .join(UserRole, UserRole.role_id == RoleMenu.role_id)
            .where(UserRole.user_id == user_id)
        )
        stmt = stmt.where(Menu.menu_id.in_(bound))
    rows = db.scalars(stmt.order_by(Menu.parent_id, Menu.order_num, Menu.menu_id)).all()
    return [MenuResp.model_validate(m) for m in rows]


def get_menu_detail(menu_id: int, db: Session) -> MenuResp:
    """菜单详情（对应若依 selectMenuById）。"""
    menu = db.get(Menu, menu_id)
    if menu is None:
        raise ServiceException("菜单不存在", code=404)
    return MenuResp.model_validate(menu)


def _select_normal_menus(user_id: int, db: Session) -> list[MenuResp]:
    """树构建专用查询：仅正常状态（status=0）的目录/菜单，不含按钮。

    复用 getRouters 的可见性规则：admin 全量，其他用户按角色绑定。
    """
    stmt = select(Menu).where(
        Menu.menu_type.in_((TYPE_DIR, TYPE_MENU)),
        Menu.status == "0",
    )
    if user_id != 1:
        bound = (
            select(RoleMenu.menu_id)
            .join(UserRole, UserRole.role_id == RoleMenu.role_id)
            .where(UserRole.user_id == user_id)
        )
        stmt = stmt.where(Menu.menu_id.in_(bound))
    rows = db.scalars(stmt.order_by(Menu.parent_id, Menu.order_num, Menu.menu_id)).all()
    return [MenuResp.model_validate(m) for m in rows]


def build_menu_tree_select(menus: list[MenuResp]) -> list[MenuTreeSelectResp]:
    """菜单平铺列表 → 下拉树（对应若依 buildMenuTreeSelect），一次遍历按 parent_id 挂 children。"""
    node_map = {m.menu_id: MenuTreeSelectResp(id=m.menu_id, label=m.menu_name) for m in menus}
    roots: list[MenuTreeSelectResp] = []
    for m in menus:
        node = node_map[m.menu_id]
        parent_node = node_map.get(m.parent_id)
        if parent_node is None:
            roots.append(node)
        else:
            parent_node.children.append(node)
    return roots


def get_tree_select(user_id: int, db: Session) -> list[MenuTreeSelectResp]:
    """菜单下拉树（对应若依 treeselect：selectMenuTreeList + buildMenuTreeSelect）。"""
    return build_menu_tree_select(_select_normal_menus(user_id, db))


def role_menu_tree_select(role_id: int, user_id: int, db: Session) -> RoleMenuTreeResp:
    """角色菜单树 + 勾选回显（对应若依 roleMenuTreeselect）。

    勾选列表按若依原版语义：仅返回"叶子勾选"——若某菜单的子菜单也被勾选，
    该父菜单 ID 不下发，由前端树控件联动出半选状态。
    """
    tree = get_tree_select(user_id, db)
    bound = set(db.scalars(select(RoleMenu.menu_id).where(RoleMenu.role_id == role_id)).all())
    # 被勾选菜单的父 ID 集合：命中者从勾选列表剔除，交给前端联动
    parent_ids = set(db.scalars(select(Menu.parent_id).where(Menu.menu_id.in_(bound))).all())
    checked = sorted(bound - parent_ids)
    return RoleMenuTreeResp(checked_keys=checked, menus=tree)


def add_menu(req: MenuCreate, db: Session) -> bool:
    """新增菜单（对应若依 insertMenu）。"""
    _check_path_and_parent(req.parent_id, req.is_frame, req.path, db)
    if not check_menu_name_unique(req.menu_name, req.parent_id, None, db):
        raise ServiceException(f"新增菜单'{req.menu_name}'失败，菜单名称已存在")

    db.add(Menu(**req.model_dump()))
    db.commit()
    return True


def update_menu(req: MenuUpdate, db: Session) -> bool:
    """修改菜单（对应若依 updateMenu）。"""
    menu = db.get(Menu, req.menu_id)
    if menu is None:
        raise ServiceException("菜单不存在", code=404)
    _check_path_and_parent(req.parent_id, req.is_frame, req.path, db)
    if not check_menu_name_unique(req.menu_name, req.parent_id, req.menu_id, db):
        raise ServiceException(f"修改菜单'{req.menu_name}'失败，菜单名称已存在")
    if req.parent_id == req.menu_id:
        raise ServiceException("修改菜单失败，上级菜单不能选择自己")
    if _is_descendant(req.parent_id, req.menu_id, db):
        raise ServiceException("修改菜单失败，上级菜单不能选择自己的子菜单")

    for key, value in req.model_dump().items():
        setattr(menu, key, value)
    db.commit()
    return True


def delete_menu(menu_id: int, db: Session) -> bool:
    """删除菜单（对应若依 deleteMenuById，sys_menu 无 del_flag，物理删除）。"""
    if db.scalar(select(func.count()).select_from(Menu).where(Menu.parent_id == menu_id)):
        raise ServiceException("存在子菜单,不允许删除")
    if db.scalar(select(func.count()).select_from(RoleMenu).where(RoleMenu.menu_id == menu_id)):
        raise ServiceException("菜单已分配,不允许删除")

    db.execute(delete(Menu).where(Menu.menu_id == menu_id))
    db.commit()
    return True


def check_menu_name_unique(
    menu_name: str, parent_id: int, menu_id: int | None, db: Session
) -> bool:
    """同级菜单名称唯一性校验（对应若依 checkMenuNameUnique）。返回 True 表示可用。"""
    stmt = select(func.count()).select_from(Menu).where(
        Menu.menu_name == menu_name,
        Menu.parent_id == parent_id,
    )
    if menu_id is not None:
        stmt = stmt.where(Menu.menu_id != menu_id)
    return not db.scalar(stmt)


def _check_path_and_parent(parent_id: int, is_frame: int, path: str | None, db: Session) -> None:
    """公共校验：上级菜单存在 + 外链地址必须以 http(s):// 开头（对应若依 insertMenu 前置校验）。"""
    if parent_id != 0 and db.get(Menu, parent_id) is None:
        raise ServiceException("上级菜单不存在")
    if is_frame == 0 and not (path or "").startswith(HTTP_PREFIXES):
        raise ServiceException("地址必须以 http(s):// 开头")


def _is_descendant(candidate_parent_id: int, menu_id: int, db: Session) -> bool:
    """判断候选上级是否为当前菜单的子孙（沿父链向上走，走到自己即命中）。

    sys_menu 无 ancestors 祖链列，逐层上溯是唯一途径；树的深度有限，循环安全。
    """
    current_id: int | None = candidate_parent_id
    while current_id and current_id != 0:
        if current_id == menu_id:
            return True
        current_id = db.scalar(select(Menu.parent_id).where(Menu.menu_id == current_id))
    return False
