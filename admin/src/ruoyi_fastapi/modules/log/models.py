"""日志模块 ORM 模型（对应若依 SysLogininfor / SysOperLog 实体）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ruoyi_fastapi.core.db import Base


class SysLogininfor(Base):
    """登录日志（sys_logininfor）。"""

    __tablename__ = "sys_logininfor"

    info_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(50), default="")
    ipaddr: Mapped[str] = mapped_column(String(128), default="")
    login_location: Mapped[str] = mapped_column(String(255), default="")
    browser: Mapped[str] = mapped_column(String(50), default="Unknown")
    os: Mapped[str] = mapped_column(String(50), default="Unknown")
    status: Mapped[str] = mapped_column(String(1), default="0")
    msg: Mapped[str] = mapped_column(String(255), default="")
    login_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SysOperLog(Base):
    """操作日志（sys_oper_log）。"""

    __tablename__ = "sys_oper_log"

    oper_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(50), default="")
    # 业务类型（0其它 1新增 2修改 3删除 4授权 5导出 6导入 7强退 8生成代码 9清空数据）
    business_type: Mapped[int] = mapped_column(default=0)
    # 方法全名（module.qualname，对应若依 ClassName.methodName）
    method: Mapped[str] = mapped_column(String(200), default="")
    request_method: Mapped[str] = mapped_column(String(10), default="")
    # 操作类别（0其它 1后台用户 2手机端用户）
    operator_type: Mapped[int] = mapped_column(default=0)
    oper_name: Mapped[str] = mapped_column(String(50), default="")
    dept_name: Mapped[str] = mapped_column(String(50), default="")
    oper_url: Mapped[str] = mapped_column(String(255), default="")
    oper_ip: Mapped[str] = mapped_column(String(128), default="")
    oper_location: Mapped[str] = mapped_column(String(255), default="")
    # 请求参数 / 返回参数（JSON 字符串，超长截断到列宽）
    oper_param: Mapped[str] = mapped_column(String(2000), default="")
    json_result: Mapped[str] = mapped_column(String(2000), default="")
    # 操作状态（0正常 1异常）
    status: Mapped[int] = mapped_column(default=0)
    error_msg: Mapped[str] = mapped_column(String(2000), default="")
    oper_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    # 消耗时间（毫秒）
    cost_time: Mapped[int] = mapped_column(default=0)
