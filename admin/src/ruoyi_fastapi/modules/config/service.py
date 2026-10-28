"""参数配置业务逻辑（缓存旁路模式：先查 Redis，未命中再查库并回填）。"""

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.constant import SYS_CONFIG_KEY
from ruoyi_fastapi.core.redis import redis_client

from .models import Config
from .schemas import BaseConfig, ConfigPage

# 验证码开关配置键（对齐若依 sys_config 表内置数据）
CAPTCHA_ENABLED_KEY = "sys.account.captchaEnabled"

_SELECT_CONFIG_SQL = """
    select config_id, config_name, config_key, config_value, config_type from sys_config
"""
_SYS_CONFIG_INFO_COUNT_SQL = "SELECT COUNT(*) FROM sys_config"


def select_captcha_enabled(db: Session) -> bool:
    """查询验证码是否开启。"""
    return select_config_by_key(CAPTCHA_ENABLED_KEY, db).lower() == "true"


def select_config_by_key(config_key: str, db: Session) -> str:
    """根据配置键查询配置值（对应若依 SysConfigServiceImpl.selectConfigByKey）。"""
    cache_key = SYS_CONFIG_KEY.format(config_key)

    # 1. 先查缓存，命中直接返回
    cached = redis_client.get(cache_key)
    if cached is not None:
        return cached

    # 2. 未命中查数据库
    config = db.execute(
        select(Config).where(Config.config_key == config_key)
    ).scalars().first()
    if config is None:
        return ""

    # 3. 回填缓存（对齐若依：配置缓存不设过期，由修改/删除接口主动清理）
    redis_client.set(cache_key, config.config_value)
    return config.config_value


# ==================== 以下方法框架待实现 ====================

def select_config_list(query: ConfigPage, db: Session) -> tuple[list[BaseConfig], int]:
    sql, params = _build_config_conditions(query)
    total = db.execute(text(_SYS_CONFIG_INFO_COUNT_SQL + sql), params).scalar_one()
    page_sql = (
        _SELECT_CONFIG_SQL
        + sql
        + " ORDER BY config_id DESC LIMIT :limit OFFSET :offset"
    )
    params["limit"] = query.page_size
    params["offset"] = (query.page_num - 1) * query.page_size

    rows = db.execute(text(page_sql), params).mappings().all()
    return [BaseConfig.model_validate(dict(r)) for r in rows], total


def select_config_count(query: ConfigPage, db: Session) -> int:
    """统计参数配置总条数（配合 select_config_list 做分页）。

    TODO: 条件与 select_config_list 完全一致，只查 COUNT(*)。
    """
    sql, params = _build_config_conditions(query)
    return db.execute(text(_SYS_CONFIG_INFO_COUNT_SQL + sql), params).scalar_one()


def save_config(config: BaseConfig, db: Session) -> bool:
    """新增参数配置（对应若依 insertConfig：插入成功后立即写缓存）。"""
    db_obj = Config(
        config_name=config.config_name,
        config_key=config.config_key,
        config_value=config.config_value,
        config_type=config.config_type,
    )
    db.add(db_obj)
    db.commit()

    # 对齐若依 CacheUtils.put：新增后按配置键回填缓存
    redis_client.set(_get_cache_key(config.config_key), config.config_value)
    return True


def update_config(config: BaseConfig, db: Session) -> bool:
    """修改参数配置（对应若依 updateConfig：改库后清理该键缓存）。"""
    db_obj = db.get(Config, config.config_id)
    if db_obj is None:
        return False

    # 改键时旧缓存键会失效，提交后新旧键都要清理
    old_cache_key = _get_cache_key(db_obj.config_key)
    db_obj.config_name = config.config_name
    db_obj.config_key = config.config_key
    db_obj.config_value = config.config_value
    db_obj.config_type = config.config_type
    db.commit()

    redis_client.delete(old_cache_key)
    redis_client.delete(_get_cache_key(config.config_key))
    return True


def delete_configs(config_ids: list[int], db: Session) -> bool:
    """批量删除参数配置（对应若依 deleteConfigByIds：内置配置禁删，物理删除后清理缓存）。"""
    # 先查出来：内置校验 + 收集待清理的缓存键
    rows = db.execute(
        select(Config).where(Config.config_id.in_(config_ids))
    ).scalars().all()
    for row in rows:
        if row.config_type == "Y":
            raise ValueError(f"{row.config_name}已内置，不能删除")
    if not rows:
        return True

    # 条件删除：一条 DELETE ... WHERE config_id IN (...)
    db.execute(delete(Config).where(Config.config_id.in_(config_ids)))
    db.commit()

    for row in rows:
        redis_client.delete(_get_cache_key(row.config_key))
    return True


def load_config_cache(db: Session) -> None:
    """全表回填参数缓存（对应若依 loadingConfigCache）。"""
    rows = db.execute(text(_SELECT_CONFIG_SQL)).mappings().all()
    for row in rows:
        redis_client.set(_get_cache_key(row["config_key"]), row["config_value"])
    return None

def clear_config_cache() -> None:
    """清空全部参数配置缓存（对应若依 clearConfigCache）。"""
    for key in redis_client.scan_iter(_get_cache_key("*")):
        redis_client.delete(key)
    return None


def refresh_config_cache(db: Session) -> bool:
    """刷新参数缓存（对应若依 resetConfigCache：先清空再从全表重新回填）。"""
    clear_config_cache()
    load_config_cache(db)
    return True


def export(db: Session, config: Config) -> bool:
    """导出参数配置列表（对应若依 export）。

    TODO: 查全量列表后生成 Excel 文件（后续可引入 openpyxl/pandas）。
    """
    raise NotImplementedError("TODO: 实现导出")


def check_config_key_unique(config_key: str | None, config_id: int | None, db: Session) -> bool:
    """检查配置键是否唯一（对应若依 checkConfigKeyUnique）。返回 True 表示键可用。"""
    if config_id is None:
        config_id = -1
    ret_config = db.execute(
        select(Config).where(Config.config_key == config_key)
    ).scalars().first()
    return ret_config is None or ret_config.config_id == config_id

def _build_config_conditions(query: ConfigPage) -> tuple[str, dict]:
    """构建 WHERE 条件片段（以 ' where 1=1' 开头，条件前置空格防止拼接粘连）。

    对齐若依 selectConfigList：configName 模糊 / configType 等值 / configKey 模糊。
    """
    sql = " where 1=1"
    params: dict = {}
    if query.config_name:
        sql += " AND config_name LIKE :config_name"
        params["config_name"] = f"%{query.config_name}%"
    if query.config_type:
        sql += " AND config_type = :config_type"
        params["config_type"] = query.config_type
    if query.config_key:
        sql += " AND config_key LIKE :config_key"
        params["config_key"] = f"%{query.config_key}%"
    return sql, params


def _get_cache_key(config_key: str) -> str:
    return SYS_CONFIG_KEY.format(config_key)


