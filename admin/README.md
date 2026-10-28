# ruoyi-fastapi

基于 FastAPI 的后台管理系统骨架（若依 Python 版）。

## 技术栈（待补充）

- Python 3.10+
- FastAPI
- SQLModel / SQLAlchemy
- 其他依赖自行添加

## 开发

```bash
# 初始化环境（自行实践）
uv sync

# 启动开发服务
uvicorn ruoyi_fastapi.main:app --reload
```

## 目录结构

```
src/ruoyi_fastapi/
├── core/       # 配置、数据库、鉴权等基础设施
├── api/v1/     # API 路由聚合层
└── modules/    # 业务模块（user/role/menu 等按需添加）
```
