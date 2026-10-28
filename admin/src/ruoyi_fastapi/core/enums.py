"""操作日志相关枚举（对应若依 BusinessType / OperatorType 枚举）。

枚举值为 int，直接写入 sys_oper_log 的 business_type / operator_type 列。
"""

from enum import IntEnum


class BusinessType(IntEnum):
    """业务类型（对应 sys_oper_log.business_type 列）。"""

    OTHER = 0      # 其它
    INSERT = 1     # 新增
    UPDATE = 2     # 修改
    DELETE = 3     # 删除
    GRANT = 4      # 授权
    EXPORT = 5     # 导出
    IMPORT = 6     # 导入
    FORCE = 7      # 强退
    GENCODE = 8    # 生成代码
    CLEAN = 9      # 清空数据


class OperatorType(IntEnum):
    """操作类别（对应 sys_oper_log.operator_type 列）。"""

    OTHER = 0    # 其它
    MANAGE = 1   # 后台用户
    MOBILE = 2   # 手机端用户
