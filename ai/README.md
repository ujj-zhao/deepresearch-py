# deepresearch-ai

DeepResearch AI 服务：Graph 编排的多智能体深度研究，对标
[spring-ai-alibaba-deepresearch](https://github.com/alibaba/spring-ai-alibaba/tree/main/spring-ai-alibaba-examples/deepresearch) 的 Python 重写版。

## 职责边界

| 本服务负责 | admin 服务（ruoyi-fastapi）负责 |
|---|---|
| StateGraph 编排、节点执行 | 用户 / RBAC / 菜单 |
| SSE 流式推送研究进度 | 研究任务管理页、报告展示 |
| RAG 检索（pgvector） | 知识库文件上传 |
| 长任务执行 | 登录签发 JWT |

集成方式：admin 签发 JWT，本服务用共享密钥校验（`core/config.py` 的 JWT_* 配置）。

## 目录结构

```
src/deepresearch/
├── main.py            # FastAPI 入口
├── core/              # 配置、安全、数据库（随阶段补充）
├── api/v1/            # HTTP 接口（SSE 端点在 P2 落地）
└── graph/             # P1 核心实现区
    ├── nodes/         # 图节点（对标 Java 版 node 包）
    └── edges/         # 条件边 dispatcher（对标 Java 版 dispatcher 包）
prompts/               # 各角色提示词模板（P1 起补充）
```

## 路线图

- [ ] P1 最小图核心：coordinator → planner → researcher → reporter 闭环，CLI 跑通
- [ ] P2 流式 + 人机协同：SSE + interrupt 暂停确认，接 FastAPI
- [ ] P3 并行 + RAG：并行 researcher + pgvector 混合检索
- [ ] P4 生产化：质检回环、会话记忆、可观测、Docker 部署

## 本地开发

```bash
uv sync                # 安装依赖
cp .env.example .env   # 配置（JWT_SECRET_KEY 与 admin 保持一致）
uv run uvicorn deepresearch.main:app --reload --port 8001
```
