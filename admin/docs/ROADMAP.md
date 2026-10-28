# RuoYi-FastAPI 开发路线图

> 把若依 Java 版用 Python (FastAPI + SQLAlchemy 2.0 + Redis) 重写。
> AI 已生成基础设施代码；本文档聚焦你**自己实现**的三大块：鉴权层 + 核心业务 + 工具类。
> 章节按"实现先后顺序"组织——前面的章节是后面的依赖。

## 现状盘点（截至 2026-09-30）

### AI 已生成的基础设施（可直接用，无需写文档）

| 模块 | 状态 |
|---|---|
| `pyproject.toml` + `.env` + ruff | 完整（含 redis、passlib、python-jose、captcha、openpyxl、slowapi、bleach 等鉴权/工具依赖） |
| `core/config.py`（pydantic-settings） | 完整（含 MySQL/Redis/JWT/CORS/上传配置） |
| `core/db.py`（SQLAlchemy engine + `AuditMixin`） | 完整 |
| `core/dependencies.py`（`get_db`） | 已重命名（原 `dependecies.py` 拼写错） |
| `core/response.py`（`R[T]` + `PageResult[T]`） | 完整（类型注解已修正） |
| `core/exception.py`（`ServiceException` + 3 个 handler） | 完整 |
| `core/middleware.py`（CORS + 防盗链） | 完整 |
| `modules/{user,role,menu,dept,post,dict,config,job,log}/models.py` | 全部对齐原版表结构 |
| `modules/user/{schemas,router}` | 完整 / 3 个示例接口 |
| `modules/fastapi_users/` | **已删除**（与若依原版认证冲突） |

### 你需要自己实现的部分（本文档覆盖）

按依赖顺序分三部分，共 18 章：

#### 第一部分 · 鉴权层（核心，做完才能做业务，共 7 章）

| # | 章节 | 前置 | 产出物 |
|---|---|---|---|
| 01 | Redis 客户端封装 | — | `core/redis.py`（async client + 序列化） |
| 02 | 密码哈希 | — | `core/security.py` 的 `hash_password` / `verify_password` |
| 03 | JWT 编解码 | — | `core/security.py` 的 `create_token` / `parse_token` |
| 04 | 验证码生成与校验 | 01 | `/captchaImage` 接口 + Redis 缓存 |
| 05 | 登录流程实现 | 01-04 | `/login` / `/logout` / `/getInfo` / `/getRouters` |
| 06 | 权限依赖 | 05 | `require_perm` / `require_role` / `get_current_user` |
| 07 | 数据权限 @DataScope 等价物 | 06 | `apply_data_scope()` 函数 |

#### 第二部分 · 核心业务模块（按依赖顺序，共 5 章）

| # | 章节 | 前置 | 产出物 |
|---|---|---|---|
| 08 | 部门管理 dept | 鉴权层 | 树结构 CRUD |
| 09 | 岗位管理 post | 鉴权层 | 标准 CRUD（作为后续模块模板） |
| 10 | 菜单管理 menu | 鉴权层 | 树结构 CRUD + `get_routers` 接口 |
| 11 | 角色管理 role | 10 | CRUD + 角色-菜单授权 + 数据范围分配 |
| 12 | 用户管理 user | 08, 09, 11, 07 | 完整 CRUD + 关联 dept/post/role + 密码重置 |

#### 第三部分 · 工具类（共 6 章）

| # | 章节 | 前置 | 产出物 |
|---|---|---|---|
| 13 | 操作日志 @Log 装饰器 | 06 | `@log` 装饰器 + 异步写入 `sys_oper_log` |
| 14 | 登录日志 logininfor | 05 | `/logininfor/list` + `@record_login_log` |
| 15 | 在线用户 | 01 | `/online/list` + 强制下线 |
| 16 | Excel 导入导出 | 12 | `ExcelUtil` 等价物（openpyxl） |
| 17 | 文件上传 | — | `/common/upload` + 大小/扩展名校验 |
| 18 | 限流 | — | `slowapi` 集成 + `@RateLimiter` |

## 阅读顺序

**严格按 01 -> 18**：每章读完同步在 `ruoyi-fastapi/` 写出对应代码，跑通再进下一章。

## 文档约定

每章统一结构：
1. **学习目标** — 做完这章你能掌握什么
2. **Java 原版位置** — 文件路径 + 类名 + 关键方法（方便回查原版）
3. **Python 实现方案** — 架构决策、选型权衡、为什么这么写
4. **关键代码** — 可运行的最小实现（直接抄进项目就能跑）
5. **设计权衡与坑点** — Java vs Python 差异、容易踩的坑

详细内容见 `DEVELOPMENT.md`。
