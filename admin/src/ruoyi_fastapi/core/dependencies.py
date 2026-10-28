"""FastAPI 通用依赖。"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from ruoyi_fastapi.core.db import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话依赖。

    用法：路由函数参数声明 db: Session = Depends(get_db)
    请求结束后自动关闭会话（generator 的 finally 语义）。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
