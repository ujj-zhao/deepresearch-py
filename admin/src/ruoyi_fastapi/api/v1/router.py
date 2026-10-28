"""API v1 路由聚合。

各业务模块的 router 在此聚合后，由 main.py 挂载到 /api/v1 前缀。
"""

from fastapi import APIRouter
from ruoyi_fastapi.modules.dict.router import dict_data_router, dict_type_router
from ruoyi_fastapi.modules.config.router import router as config_router
from ruoyi_fastapi.modules.dept.router import router as dept_router
from ruoyi_fastapi.modules.login.router import router as login_router
from ruoyi_fastapi.modules.auth.router import router as auth_router
from ruoyi_fastapi.modules.menu.router import router as menu_router
from ruoyi_fastapi.modules.monitor.router import router as monitor_router
from ruoyi_fastapi.modules.notice.router import router as notice_router
from ruoyi_fastapi.modules.post.router import router as post_router
from ruoyi_fastapi.modules.role.router import router as role_router
from ruoyi_fastapi.modules.user.router import router as user_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(login_router)
router.include_router(dict_type_router)
router.include_router(dict_data_router)
router.include_router(config_router)
router.include_router(dept_router)
router.include_router(menu_router)
router.include_router(monitor_router)
router.include_router(notice_router)
router.include_router(post_router)
router.include_router(role_router)
router.include_router(user_router)
