# RuoYi-FastAPI 开发文档

> 把若依 Java 版用 Python 重写。本文档覆盖**你自己实现**的三大块：鉴权层 + 核心业务 + 工具类。
> 参考手册式风格——每章直接给方案和关键代码，遇到 Python 新概念在边学边讲处简注。
> 配套阅读：[ROADMAP.md](./ROADMAP.md) — 章节总览与依赖关系。

## 目录

- [第一部分 · 鉴权层](#第一部分--鉴权层)
  - [01 Redis 客户端封装](#01-redis-客户端封装)
  - [02 密码哈希](#02-密码哈希)
  - [03 JWT 编解码](#03-jwt-编解码)
  - [04 验证码生成与校验](#04-验证码生成与校验)
  - [05 登录流程实现](#05-登录流程实现)
  - [06 权限依赖](#06-权限依赖)
  - [07 数据权限 @DataScope 等价物](#07-数据权限-datascope-等价物)
- [第二部分 · 核心业务模块](#第二部分--核心业务模块)
  - [08 部门管理 dept](#08-部门管理-dept)
  - [09 岗位管理 post](#09-岗位管理-post)
  - [10 菜单管理 menu](#10-菜单管理-menu)
  - [11 角色管理 role](#11-角色管理-role)
  - [12 用户管理 user](#12-用户管理-user)
- [第三部分 · 工具类](#第三部分--工具类)
  - [13 操作日志（@Log 装饰器）](#13-操作日志log-装饰器)
  - [14 登录日志 logininfor](#14-登录日志-logininfor)
  - [15 在线用户](#15-在线用户)
  - [16 Excel 导入导出](#16-excel-导入导出)
  - [17 文件上传](#17-文件上传)
  - [18 限流](#18-限流)

---

## 第一部分 · 鉴权层

> 这是整个项目的难点，做完才能做业务。参考 Java 实现：`ruoyi-framework/.../security/`、`ruoyi-framework/.../web/service/{SysLoginService, TokenService, SysPermissionService}.java`

### 01 Redis 客户端封装

**学习目标**：掌握 `redis-py` 异步客户端的连接池、序列化、键命名规范。

**Java 原版位置**：`ruoyi-framework/.../config/RedisConfig.java`、`ruoyi-common/.../core/redis/RedisCache.java`

**Python 实现方案**：
- 用 `redis.asyncio` 异步客户端（与 FastAPI 一致）
- 序列化：`orjson` 替代 FastJSON2 的 `WriteClassName` 模式
- 键命名规范（对应若依 `CacheConstants`）：
  - `login_tokens:{uuid}` — 登录 token
  - `captcha_codes:{uuid}` — 验证码
  - `sys_config:{config_key}` — 参数配置缓存
  - `pwd_err_cnt:{username}` — 密码错误计数
  - `repeat_submit:{url}_{token}` — 防重提交

**关键代码**：[待填充]

**设计权衡与坑点**：
- Java `FastJson2JsonRedisSerializer` 写入 `@class` 类型信息，反序列化时按类型反射重建；Python 用 `orjson.dumps(obj, default=...)` + 显式 `type` 字段更安全（避免任意类反序列化攻击）
- 同步 `redis` 还是 `redis.asyncio`：因为 main.py 已经是 async，建议全异步
- 全局单例：用模块级 `redis_client = Redis.from_url(settings.redis_url)` 即可，不需要 Spring `@Bean`

---

### 02 密码哈希

**学习目标**：理解 BCrypt 算法；保证 Python 哈希结果与 Java `BCryptPasswordEncoder` 互通（旧用户密码可登录）。

**Java 原版位置**：`ruoyi-framework/.../config/SecurityConfig.java`（`BCryptPasswordEncoder` Bean）、`ruoyi-common/.../utils/SignUtils.java`

**Python 实现方案**：
- 用 `passlib[bcrypt]`，与 Java `BCryptPasswordEncoder` 完全兼容
- 实现两个函数：`hash_password(plain) -> str`、`verify_password(plain, hashed) -> bool`

**关键代码**：[待填充]

**设计权衡与坑点**：
- 必须用 `$2a$` / `$2b$` 前缀的 BCrypt，与 Spring Security 默认一致
- 不要用 `hashlib.sha256` 等其他算法——会与旧用户数据不兼容
- `passlib` 在新版本会警告 BCrypt 4.x 兼容性问题，可忽略或显式指定 `CryptContext(schemes=["bcrypt"], deprecated="auto")`

---

### 03 JWT 编解码

**学习目标**：掌握 `python-jose` 的 token 编解码；理解若依的"JWT 不带用户信息、只作为 Redis key 索引"模式。

**Java 原版位置**：`ruoyi-framework/.../web/service/TokenService.java`

**Python 实现方案**：
- 用 `python-jose[cryptography]`（或 `PyJWT`，二选一）
- token 是一个 UUID（不携带用户信息），JWT claims 里只放 `login_user_key`，Redis 存完整 `LoginUser`
- 实现：
  - `create_token(login_user: LoginUser) -> str` — 生成 UUID + 写 Redis + 签 JWT
  - `parse_token(token: str) -> str | None` — 解 JWT 拿 `login_user_key`
  - `get_login_user(uuid: str) -> LoginUser | None` — 从 Redis 反查

**关键代码**：[待填充]

**设计权衡与坑点**：
- 与传统 JWT（claims 直接放用户信息）不同，若依把用户信息存 Redis，token 只是 Redis key——好处是随时能让 token 失效（强退在线用户）
- `LoginUser` 需要定义 Pydantic 模型，含 `user_id` / `user` / `roles` / `permissions` / `token` / `login_time` / `expire_time` / `dept_id`
- token 过期刷新：每次 `get_login_user` 时检查剩余时间，若小于 1/5 则续期

---

### 04 验证码生成与校验

**学习目标**：实现若依 `math`（算术）和 `char`（字符）两种验证码。

**Java 原版位置**：`ruoyi-admin/.../web/controller/common/CaptchaController.java`、`ruoyi-framework/.../config/CaptchaConfig.java`（Kaptcha）

**Python 实现方案**：
- 用 `captcha.image.ImageCaptcha` 生成图片，或用 Pillow 自绘
- math 模式：生成 `1+2=?@3` 字符串，存 Redis `captcha_codes:{uuid}` -> `{code: "3", expire: 120s}`
- char 模式：随机 4 位字符
- 接口：`GET /captchaImage` 返回 `{code, uuid, img}`（img 是 base64）

**关键代码**：[待填充]

**设计权衡与坑点**：
- Kaptcha 的算术验证码会返回 base64 图片 + uuid，前端把 uuid 和用户答案一起提交
- Redis key 一次性用后删除（防重放）
- 开关：`sys_config` 表里 `sys.account.captchaEnabled` 控制是否开启验证码

---

### 05 登录流程实现

**学习目标**：把前面 4 章串起来，实现完整的登录闭环。

**Java 原版位置**：`ruoyi-admin/.../web/controller/system/SysLoginController.java`、`ruoyi-framework/.../web/service/SysLoginService.java`、`ruoyi-framework/.../web/service/SysPermissionService.java`

**Python 实现方案**：
- `POST /login`：校验验证码 -> 校验用户名密码 -> 生成 token -> 写 Redis -> 返回 `{token}`
- `GET /getInfo`：从 token 反查 `LoginUser`，返回 `{user, roles, permissions}`
- `GET /getRouters`：根据用户角色构建菜单树，返回前端可渲染的 router 配置
- `POST /logout`：从 Redis 删除 token

**关键代码**：[待填充]

**设计权衡与坑点**：
- 登录失败次数限制：Redis `pwd_err_cnt:{username}` 累计，超过 5 次锁定 10 分钟
- 菜单构建是难点，Java `SysMenuServiceImpl.buildMenus` 递归树，Python 用 `anytree` 或自己写递归
- `/getInfo` 必须返回 `roles`（角色 key 列表）和 `permissions`（权限标识列表，如 `["system:user:list", ...]`），前端用这个做按钮级权限控制

---

### 06 权限依赖

**学习目标**：实现 FastAPI 版的 `@PreAuthorize("@ss.hasPermi('system:user:list')")`。

**Java 原版位置**：`ruoyi-framework/.../web/service/PermissionService.java`、`@PreAuthorize` 注解

**Python 实现方案**：
- 实现 `get_current_user` 依赖：解析 Authorization header -> Redis 查 LoginUser -> 注入到路由
- 实现 `require_perm(perms: str)` / `require_role(role: str)` 工厂依赖：基于 `get_current_user` 二次校验
- 路由用法：

```python
@router.get("/list",
            dependencies=[Depends(require_perm("system:user:list"))])
def list_users(...): ...
```

**关键代码**：[待填充]

**设计权衡与坑点**：
- FastAPI `Depends` 可以嵌套：`require_perm` 内部 `Depends(get_current_user)`
- 管理员（`admin` 角色）绕过所有权限检查，与 Java 一致
- 权限标识字符串必须与前端按钮权限一致（如 `system:user:list`）
- 推荐用 `dependencies=[Depends(...)]` 而不是默认参数，避免污染路由函数签名

---

### 07 数据权限 @DataScope 等价物

**学习目标**：实现若依最有特色也最容易踩坑的 `@DataScope` AOP——按当前用户角色范围过滤查询。

**Java 原版位置**：`ruoyi-common/.../annotation/DataScope.java`、`ruoyi-framework/.../aspectj/DataScopeAspect.java`

**Python 实现方案**：
- 不能照搬 Java 的"改写 SQL 字符串拼接"——会引入 SQL 注入
- 用 SQLAlchemy 2.0 的 `with_loader_criteria` 或在 repository 层根据当前用户的 `dept_id` + 角色范围（`data_scope` 字段）追加 filter：
  - `1` 全部数据 — 不追加 filter
  - `2` 自定义 — `dept_id IN (角色关联的部门列表)`
  - `3` 本部门 — `dept_id == user.dept_id`
  - `4` 本部门及以下 — `dept_id IN (本部门 + 子部门)`（用 `ancestors LIKE` 或递归）
  - `5` 仅本人 — `create_by == user.user_name`
- 实现 `apply_data_scope(stmt, user, dept_alias="d") -> stmt` 函数

**关键代码**：[待填充]

**设计权衡与坑点**：
- Java 用 `${params.dataScope}` 字符串拼接到 XML SQL；Python 必须在 ORM query 层做
- 自定义数据范围（`data_scope=2`）：需要查 `sys_role_dept` 拿到角色关联的部门列表，再用 `dept_id IN (...)` 过滤
- 本部门及以下（`data_scope=4`）：递归查 `sys_dept` 的 `ancestors` 字段（已存路径，如 `0,100,101`），用 `FIND_IN_SET(user_dept_id, ancestors) OR dept_id = user_dept_id`
- 一个用户多个角色时取并集（最宽松的 data_scope 生效）

---

## 第二部分 · 核心业务模块

> 按"被依赖的先做"顺序：dept -> post -> menu -> role -> user

### 08 部门管理 dept

**学习目标**：实现树形 CRUD；掌握 SQLAlchemy 自引用关系（`parent_id` / `ancestors` 路径）。

**Java 原版位置**：`ruoyi-system/.../service/impl/SysDeptServiceImpl.java`、`ruoyi-system/.../mapper/SysDeptMapper.java`

**Python 实现方案**：
- `models.py` 已有（`SysDept` 表结构对齐）
- 补 `schemas.py`：`DeptDTO` / `DeptCreate` / `DeptUpdate` / `DeptTreeVO`
- 补 `service.py`：
  - `list_depts(query)` — 列表（不分页，返回全部，前端自己渲染树）
  - `build_dept_tree(depts)` — 平铺 list 转 tree
  - `create_dept(dto)` — 创建 + 自动填充 `ancestors`（父级的 `ancestors` + 父 ID）
  - `update_dept(id, dto)` — 更新；若 `parent_id` 变了要级联更新子部门的 `ancestors`
  - `delete_dept(id)` — 删除前校验：是否有子部门、是否有用户
- 补 `router.py`：5 个标准接口 + `/treeselect`（部门树下拉） + `/roleDeptTreeselect/{role_id}`（角色已分配的部门树）

**关键代码**：[待填充]

**设计权衡与坑点**：
- 不用 SQLAlchemy 的 `relationship` 自引用——若依用 `ancestors` 路径字符串，更直观
- `ancestors` 维护成本：父部门变更时，所有子部门的 `ancestors` 都要重算（递归更新）
- 删除部门前要校验：是否有子部门（`parent_id = 当前id`）、是否有用户（`sys_user.dept_id = 当前id`）

---

### 09 岗位管理 post

**学习目标**：完成一个标准 CRUD 闭环（list / detail / create / update / delete），作为后续模块的模板。

**Java 原版位置**：`ruoyi-system/.../service/impl/SysPostServiceImpl.java`

**Python 实现方案**：
- `models.py` 已有
- 补 `schemas.py`：`PostDTO` / `PostCreate` / `PostUpdate` / `PostPageQuery`
- 补 `service.py`：CRUD + `post_code` 唯一性校验
- 补 `router.py`：5 个标准接口 + `/export`（导出，第 16 章会用到）

**关键代码**：[待填充]

**设计权衡与坑点**：
- 这是最简单的模块，做完后把代码作为其他业务模块的复制起点
- 唯一性校验：`post_code` 不能重复（查询时排除自身 ID）
- 分页用 `PageResult[T]`：先 `count(*)` 拿 total，再 `limit/offset` 拿 rows

---

### 10 菜单管理 menu

**学习目标**：实现菜单树 + 路由构建（给前端 `getRouters` 用的 router 配置）。

**Java 原版位置**：`ruoyi-system/.../service/impl/SysMenuServiceImpl.java`、`ruoyi-system/.../domain/vo/RouterVo.java`、`ruoyi-system/.../domain/vo/MetaVo.java`

**Python 实现方案**：
- `models.py` 已有（`SysMenu` 表结构对齐，含 `menu_type` M目录/C菜单/F按钮）
- 补 `schemas.py`：
  - `MenuDTO` / `MenuCreate` / `MenuUpdate` / `MenuTreeVO`
  - `RouterVO` — 给前端的路由结构：`{name, path, hidden, redirect, component, alwaysShow, meta, children}`
  - `MetaVO` — `{title, icon, noCache, link}`
- 关键函数：
  - `select_menu_list(user)` — 普通用户只查自己角色关联的菜单；管理员查全部
  - `build_menus(menus)` — 把平铺 list 转 router 树，按 `menu_type` 决定结构
  - `get_router_tree(user)` — 综合调用，给 `/getRouters` 用
- 权限标识 `perms` 字段：如 `system:user:list`，给第 06 章用

**关键代码**：[待填充]

**设计权衡与坑点**：
- 路由构建逻辑复杂：
  - `menu_type=M` 是目录（`component=null`，`path` 是路由前缀，`redirect` 指向第一个子菜单）
  - `menu_type=C` 是菜单（`component` 是 Vue 页面路径，如 `system/user/index`）
  - `menu_type=F` 是按钮（不参与路由，只用于权限标识）
- `meta` 字段含 `title` / `icon` / `noCache` / `link` / `activePath`，与 Vue 前端约定一致
- `is_frame=1`（外链）：`path` 直接是 URL，前端用 `<iframe>` 嵌入
- `is_outer=1`（内嵌）：`component` 用 `InnerLink`，前端通过 `<iframe>` 加载 `meta.link`

---

### 11 角色管理 role

**学习目标**：实现角色-菜单授权、角色-数据范围分配。

**Java 原版位置**：`ruoyi-system/.../service/impl/SysRoleServiceImpl.java`、`ruoyi-system/.../mapper/SysRoleMenuMapper.java`

**Python 实现方案**：
- `models.py` 已有（`SysRole` + `SysRoleMenu` + `SysRoleDept`）
- 补 schemas/service/router
- 关键方法：
  - `assign_menus(role_id, menu_ids)` — 删旧 `sys_role_menu` + 批量插新（事务）
  - `change_data_scope(role_id, data_scope, dept_ids)` — 更新 `sys_role.data_scope` + 删插 `sys_role_dept`（仅 `data_scope=2` 时需要）
  - `get_role_menu_ids(role_id)` — 查角色已分配的菜单 ID 列表（给前端回显用）

**关键代码**：[待填充]

**设计权衡与坑点**：
- 角色-菜单授权必须事务：先 `DELETE FROM sys_role_menu WHERE role_id=?`，再批量 `INSERT`
- `admin` 角色（`role_id=1` 或 `role_key='admin'`）特殊处理，绕过所有权限
- `data_scope` 修改会影响所有该角色用户的数据可见性，需在第 07 章的 `apply_data_scope` 中读取最新值

---

### 12 用户管理 user

**学习目标**：整合前面所有章节，实现完整用户管理（最复杂的模块）。

**Java 原版位置**：`ruoyi-system/.../service/impl/SysUserServiceImpl.java`、`ruoyi-admin/.../web/controller/system/SysUserController.java`

**Python 实现方案**：
- `models.py` / `schemas.py` 已有
- 补 `service.py`（当前空）：
  - `list_users(query, current_user)` — 列表查询 + 数据权限过滤（第 07 章）+ join `sys_dept` 拿部门名
  - `get_user(id)` — 详情 + 角色 ID 列表 + 岗位 ID 列表
  - `create_user(dto)` — 创建 + 关联角色/岗位（事务）+ 密码哈希（第 02 章）
  - `update_user(id, dto)` — 更新 + 重新关联角色/岗位
  - `delete_user(ids)` — 软删除（`del_flag='2'`）+ 校验不允许删除 admin
  - `reset_pwd(id, password)` — 重置密码（哈希后写）
  - `change_status(id, status)` — 切换账号状态
- `router.py` 现有 3 个示例接口需重写为完整 8 个接口：
  - `GET /list` `GET /{id}` `POST /` `PUT /` `DELETE /{ids}` `PUT /resetPwd` `PUT /changeStatus` `GET /deptTree`

**关键代码**：[待填充]

**设计权衡与坑点**：
- 用户-角色-岗位关联表更新必须事务：先 DELETE，再 INSERT
- 列表查询要 join `sys_dept` 拿部门名，且按数据权限过滤（不同角色看到不同范围）
- 不允许删除 admin 用户（`user_id=1`）和当前登录用户
- `import` 导入用户：第 16 章实现 ExcelUtil 后接入

---

## 第三部分 · 工具类

### 13 操作日志（@Log 装饰器）

**学习目标**：实现 FastAPI 版的 AOP——用装饰器拦截路由记录操作日志。

**Java 原版位置**：`ruoyi-common/.../annotation/Log.java`、`ruoyi-framework/.../aspectj/LogAspect.java`、`ruoyi-system/.../domain/SysOperLog.java`

**Python 实现方案**：
- 定义装饰器：`@log(title="用户管理", business_type=BusinessType.INSERT)`
- 装饰器内：
  - 记录请求方法 / URL / 入参 / 调用者 IP / UA / 调用者用户名
  - 调用原函数
  - 异常时也要记录（`status=1`）
  - 异步写入 `sys_oper_log`（用 `BackgroundTasks` 或 `asyncio.create_task`）
- `BusinessType` 枚举：OTHER / INSERT / UPDATE / DELETE / GRANT / EXPORT / IMPORT / FORCE / GENCODE / CLEAN

**关键代码**：[待填充]

**设计权衡与坑点**：
- Java 用 AOP 拦截 `@Log`；Python 用装饰器，但要注意 `functools.wraps` 保留函数签名（FastAPI 依赖签名生成 OpenAPI）
- 异步写入必须保证失败不影响主请求；用 `BackgroundTasks` 比 `asyncio.create_task` 更稳（FastAPI 会等 BackgroundTasks 但不阻塞响应）
- 入参序列化：`request.body()` 读取后要还原给后续 handler，需要 `request._body` 缓存或用 `BaseHTTPMiddleware`

---

### 14 登录日志 logininfor

**学习目标**：记录登录成功/失败日志。

**Java 原版位置**：`ruoyi-system/.../domain/SysLogininfor.java`、`ruoyi-framework/.../web/service/SysLoginService.java`（`recordLogininfor` 调用）、`ruoyi-admin/.../web/controller/monitor/SysLogininforController.java`

**Python 实现方案**：
- `models.py` 已有（`sys_logininfor` 表结构）
- 在第 05 章登录流程的入口/出口插入 `record_login_log(username, status, msg, request)`
  - `status=0` 成功，`status=1` 失败
- 接口：`GET /logininfor/list`（分页查询）、`DELETE /{ids}`（批量删除）、`DELETE /clean`（清空）、`GET /unlockUser/{username}`（解锁）

**关键代码**：[待填充]

**设计权衡与坑点**：
- 登录日志量大，需要按时间分区或定期清理（`sys_config` 配置保留天数）
- 异步写入，不阻塞登录响应
- 解锁用户：删除 Redis `pwd_err_cnt:{username}` key

---

### 15 在线用户

**学习目标**：基于 Redis token 实现在线用户列表与强退。

**Java 原版位置**：`ruoyi-admin/.../web/controller/monitor/SysUserOnlineController.java`、`ruoyi-common/.../core/domain/entity/SysUserOnline.java`

**Python 实现方案**：
- 在线列表：扫描 Redis `login_tokens:*` key，反查 `LoginUser`，组装 `OnlineUserDTO`（`tokenId / userName / ipaddr / loginTime`）
- 接口：`GET /online/list`（分页）、`DELETE /{token_id}`（强制下线 = 删除 Redis key）
- 强退：`DELETE login_tokens:{uuid}`，下次请求 token 失效

**关键代码**：[待填充]

**设计权衡与坑点**：
- `KEYS login_tokens:*` 在生产会阻塞，用 `SCAN` 代替
- 在线状态判定：token 未过期 + Redis key 存在
- 分页：Redis 取全部后内存分页（数据量可控，因为活跃用户有限）

---

### 16 Excel 导入导出

**学习目标**：实现若依 `ExcelUtil` 等价物。

**Java 原版位置**：`ruoyi-common/.../utils/poi/ExcelUtil.java`、`ruoyi-common/.../annotation/Excel.java`

**Python 实现方案**：
- 用 `openpyxl`（读写 xlsx）
- 导出：
  - 路由 `@router.get("/export")` -> 查询数据 -> `openpyxl.Workbook` -> `StreamingResponse` 返回
  - 字段映射：Pydantic 模型字段注解（`Field(description="用户账号")`）作为列名
- 导入：
  - `POST /import`：接收 `UploadFile` -> `openpyxl.load_workbook` -> 逐行解析为 Pydantic 模型 -> 批量入库
  - 模板下载：`GET /importTemplate` 返回空 Excel
- `ExcelUtil` 通用工具类：基于 Pydantic 模型自动生成列、读、写

**关键代码**：[待填充]

**设计权衡与坑点**：
- 大数据量导出用 `openpyxl.worksheet.WriteOnlyWorksheet` 流式写
- 导入必须模板校验（列顺序、数据类型）
- 字段顺序：Pydantic 模型字段定义顺序即列顺序
- Java 用 `@Excel(name="用户账号")` 注解；Python 用 `Field(description="...")` 作为列名来源

---

### 17 文件上传

**学习目标**：实现通用文件上传接口。

**Java 原版位置**：`ruoyi-admin/.../web/controller/common/CommonController.java`、`ruoyi-common/.../utils/file/FileUploadUtils.java`

**Python 实现方案**：
- `POST /common/upload`：
  - 接收 `UploadFile` + `biz` 业务标识
  - 校验大小（`settings.UPLOAD_MAX_SIZE`）+ 扩展名（`settings.UPLOAD_ALLOWED_EXT`）
  - 文件名重命名（`uuid4().hex + 扩展名`）
  - 写 `settings.UPLOAD_PATH / biz / YYYY / MM / DD / 新文件名`
  - 返回 `{code, msg, url, fileName, newFileName, originalFilename}`
- 静态资源服务：`app.mount("/static", StaticFiles(directory=settings.UPLOAD_PATH))`

**关键代码**：[待填充]

**设计权衡与坑点**：
- 必须校验扩展名白名单（防止上传 .py / .sh / .jsp）
- 文件名重命名（UUID + 原扩展名），防止覆盖和路径穿越
- `UploadFile.file` 是 SpooledTemporaryFile，大文件会写磁盘；不要 `await file.read()` 全读入内存
- 路径穿越：`Path(filename).name` 取纯文件名，丢弃任何路径部分

---

### 18 限流

**学习目标**：实现若依 `@RateLimiter` 等价物。

**Java 原版位置**：`ruoyi-common/.../annotation/RateLimiter.java`、`ruoyi-common/.../enums/LimitType.java`、`ruoyi-framework/.../aspectj/RateLimiterAspect.java`

**Python 实现方案**：
- 用 `slowapi` 库（FastAPI 限流标准选择）
- 配置：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)
app.state.limiter = limiter
```

- 装饰器：`@limiter.limit("10/minute")`，基于 Redis 计数
- 全局异常处理：`slowapi.errors.RateLimitExceeded` -> 返回 `R.fail(msg="请求过于频繁", code=429)`

**关键代码**：[待填充]

**设计权衡与坑点**：
- 限流维度：IP / 用户 / 接口，`LimitType` 枚举对应 `DEFAULT` / `IP` / `USER`
- `slowapi` 默认用 Redis 存储，与若依原版一致
- 限流装饰器必须放在路由装饰器之外，否则拿不到 `request` 对象

---

## 附录

### A. Java <-> Python 概念对照速查

| Java (Spring Boot) | Python (FastAPI) |
|---|---|
| `@RestController` | `APIRouter` + `@router.get/post` |
| `@Autowired` | `Depends(...)` |
| `@Service` | 普通函数或类，无装饰器 |
| `@Configuration` | `pydantic-settings.BaseSettings` |
| `@Value("${...}")` | `Settings` 字段 |
| `@PreAuthorize("@ss.hasPermi(...)")` | `Depends(require_perm(...))` |
| `@DataScope` AOP | `apply_data_scope()` 函数 + repository 调用 |
| `@Log` AOP | `@log(...)` 装饰器 |
| `@Transactional` | `with db.begin():` 或 `db.commit()` |
| `BCryptPasswordEncoder` | `passlib[bcrypt]` |
| Spring Security filter chain | FastAPI middleware + Depends |
| `application.yml` | `.env` + `settings.py` |
| MyBatis XML Mapper | SQLAlchemy 2.0 ORM |
| PageHelper | 自定义分页或 `fastapi-pagination` |
| Druid | SQLAlchemy pool（已内置） |
| Kaptcha | `captcha` 库或 Pillow |
| Quartz | APScheduler |
| Velocity | Jinja2 |
| Apache POI | openpyxl |
| Springdoc | FastAPI 内置 OpenAPI |
| Spring AOP | 装饰器 + middleware |
| `@Async` | `async/await` + `BackgroundTasks` |
| `@RequestParam` | Pydantic 模型字段 |
| `@PathVariable` | 路由参数 |
| `@RequestBody` | Pydantic 模型参数 |
| `HttpServletRequest` | `Request` 依赖 |
| `@Value` 默认值 | `Field(default=...)` |

### B. 推荐学习资源

- FastAPI 官方文档：https://fastapi.tiangolo.com（中文版同步）
- SQLAlchemy 2.0 教程：https://docs.sqlalchemy.org/en/20/tutorial/
- Pydantic V2 迁移指南：https://docs.pydantic.dev/2.0/migration/
- `redis-py` 异步文档：https://redis-py.readthedocs.io/en/stable/
- `passlib` BCrypt 文档：https://passlib.readthedocs.io/en/stable/lib/passlib.hash.bcrypt.html
- `python-jose` 文档：https://python-jose.readthedocs.io/
- 若依原版文档：http://doc.ruoyi.vip
