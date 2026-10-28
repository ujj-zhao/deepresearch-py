"""数据权限的结构化范围对象与查询过滤工具。

对应若依 DataScopeAspect 切面 + @DataScope 注解：
若依通过 AOP 拼接 SQL 片段进 XML 的 ${params.dataScope}；
Python 版改为「结构化范围对象 + FastAPI 依赖注入」：
- DataScope/apply_scope 在本模块（纯对象，无任何模块依赖，避免循环导入）
- get_data_scope 依赖在 core/permissions.py（需要解析登录会话）
"""

from dataclasses import dataclass, field

from sqlalchemy import literal, or_


@dataclass
class DataScope:
    """结构化数据范围（替代若依拼接的 SQL 片段）。

    多角色语义 = 集合并集；all=True 短路（对齐若依 data_scope=1 后 break）；
    两集合全空且非 all → service 侧应返回空结果（对齐若依"不查询任何数据"兜底）。
    """

    all: bool = False                                 # data_scope=1：全量，无需过滤
    dept_ids: set[int] = field(default_factory=set)   # 允许看到的部门集合
    user_ids: set[int] = field(default_factory=set)   # 额外允许的用户集合


def apply_scope(stmt, scope: DataScope, dept_column=None, user_column=None):
    """把数据范围条件应用到查询语句（对应若依 XML 中 ${params.dataScope} 的展开动作）。

    dept_column: 业务表的部门外键列（如 SysUser.dept_id）
    user_column: 业务表的用户主键列（仅本人范围用，如 SysUser.user_id）
    列对象天然绑定所属表，无需若依 XML 里的字符串表别名。
    """
    if scope.all:
        return stmt                                    # 全量：不加条件
    conds = []
    if scope.dept_ids and dept_column is not None:
        conds.append(dept_column.in_(scope.dept_ids))
    if scope.user_ids and user_column is not None:
        conds.append(user_column.in_(scope.user_ids))
    if not conds:
        return stmt.where(literal(False))              # 空范围：不查询任何数据（对齐若依兜底）
    return stmt.where(or_(*conds))                     # 部门 ∪ 用户 取并集
