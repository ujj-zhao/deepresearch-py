from datetime import datetime

from pydantic import Field

from ruoyi_fastapi.core.schemas import CamelModel

class SysLogininfoQuery(CamelModel):
    """登录日志列表查询参数（对应若依 SysLogininfor 的查询条件）。"""

    user_name: str | None = Field(default=None, max_length=50, description="用户账号")
    ipaddr: str | None = Field(default=None, max_length=128, description="登录IP地址")
    status: str | None = Field(default=None, max_length=1, description="登录状态（0成功 1失败）")
    begin_time: datetime | None = Field(default=None, description="登录时间起")
    end_time: datetime | None = Field(default=None, description="登录时间止")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")

class SysOperLogQuery(CamelModel):
    """操作日志列表查询参数（对应若依 SysOperLog 的查询条件 + 分页）。"""

    title: str | None = Field(default=None, max_length=50, description="操作模块（模糊查询）")
    oper_name: str | None = Field(default=None, max_length=50, description="操作人员（模糊查询）")
    business_type: int | None = Field(
        default=None,
        description="业务类型（0其它 1新增 2修改 3删除 4授权 5导出 6导入 7强退 8生成代码 9清空数据）",
    )
    status: int | None = Field(default=None, description="操作状态（0正常 1异常）")
    oper_ip: str | None = Field(default=None, max_length=128, description="操作地址")
    begin_time: datetime | None = Field(default=None, description="操作时间起")
    end_time: datetime | None = Field(default=None, description="操作时间止")
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页条数")


class SysOperLogVO(CamelModel):
    """操作日志列表视图模型（对应 sys_oper_log 表的查询条件）。"""

    oper_id: int = Field(description="操作序号")
    title: str | None = Field(default=None, description="操作模块")
    business_type: int | None = Field(
        default=None,
        description="业务类型（0其它 1新增 2修改 3删除 4授权 5导出 6导入 7强退 8生成代码 9清空数据）",
    )
    business_types: list[int] | None = Field(
        default=None,
        description="业务类型数组",
    )
    method: str | None = Field(default=None, description="请求方法")
    request_method: str | None = Field(default=None, description="请求方式")
    operator_type: int | None = Field(
        default=None, description="操作类别（0其它 1后台用户 2手机端用户）"
    )
    oper_name: str | None = Field(default=None, description="操作人员")
    dept_name: str | None = Field(default=None, description="部门名称")
    oper_url: str | None = Field(default=None, description="请求地址")
    oper_ip: str | None = Field(default=None, description="操作地址")
    oper_location: str | None = Field(default=None, description="操作地点")
    oper_param: str | None = Field(default=None, description="请求参数")
    json_result: str | None = Field(default=None, description="返回参数")
    status: int | None = Field(default=None, description="操作状态（0正常 1异常）")
    error_msg: str | None = Field(default=None, description="错误消息")
    oper_time: datetime | None = Field(default=None, description="操作时间")
    cost_time: int | None = Field(default=None, description="消耗时间（毫秒）")

# ------------------ 响应参数 ------------------
class SysLogininfoResp(CamelModel):
    """登录日志响应模型（对应 sys_logininfor 表）。"""

    info_id: int = Field(description="访问ID")
    user_name: str | None = Field(default=None, description="用户账号")
    ipaddr: str | None = Field(default=None, description="登录IP地址")
    login_location: str | None = Field(default=None, description="登录地点")
    browser: str | None = Field(default=None, description="浏览器类型")
    os: str | None = Field(default=None, description="操作系统")
    status: str | None = Field(default=None, description="登录状态（0成功 1失败）")
    msg: str | None = Field(default=None, description="提示消息")
    login_time: datetime | None = Field(default=None, description="访问时间")


class SysOnlineUser(CamelModel):
    """在线用户响应模型（对应若依 SysUserOnline）。"""

    token_id: str = Field(description="会话编号")
    dept_name: str | None = Field(default=None, description="部门名称")
    user_name: str | None = Field(default=None, description="用户名称")
    ipaddr: str | None = Field(default=None, description="登录IP地址")
    login_location: str | None = Field(default=None, description="登录地址")
    browser: str | None = Field(default=None, description="浏览器类型")
    os: str | None = Field(default=None, description="操作系统")
    login_time: int | None = Field(default=None, description="登录时间（毫秒时间戳）")


