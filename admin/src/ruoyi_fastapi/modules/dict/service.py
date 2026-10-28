"""字典模块业务逻辑（对应若依 SysDictTypeServiceImpl / SysDictDataServiceImpl）。

字典数据读多写少，采用与 sys_config 相同的缓存旁路模式：
sys_dict:{dictType} 存 DictData 列表 JSON，不设过期，写操作后主动删缓存。
"""

import json

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ruoyi_fastapi.core.constant import SYS_DICT_KEY
from ruoyi_fastapi.core.exception import ServiceException
from ruoyi_fastapi.core.redis import redis_client

from .models import DictData, DictType
from .schemas import (
    DictDataCreate,
    DictDataPageQuery,
    DictDataResp,
    DictDataUpdate,
    DictTypeCreate,
    DictTypePageQuery,
    DictTypeResp,
    DictTypeUpdate,
)


def _dict_cache_key(dict_type: str) -> str:
    return SYS_DICT_KEY.format(dict_type)


# ==================== 字典数据（含核心缓存查询） ====================


def select_dict_data_by_type(dict_type: str, db: Session) -> list[DictDataResp]:
    """按字典类型查询启用中的字典数据（对应 selectDictDataByType，缓存旁路）。

    前端下拉框/标签回显的核心接口：先查 Redis，未命中查库并回填。
    """
    cache_key = _dict_cache_key(dict_type)

    # 1. 先查缓存
    cached = redis_client.get(cache_key)
    if cached is not None:
        return [DictDataResp.model_validate(item) for item in json.loads(cached)]

    # 2. 未命中查库：仅启用状态，按排序字段稳定输出
    rows = db.scalars(
        select(DictData)
        .where(DictData.dict_type == dict_type, DictData.status == "0")
        .order_by(DictData.dict_sort, DictData.dict_code)
    ).all()
    result = [DictDataResp.model_validate(r) for r in rows]

    # 3. 回填缓存（JSON 序列化用 camelCase 别名，与响应格式一致）
    redis_client.set(
        cache_key,
        json.dumps([r.model_dump(mode="json", by_alias=True) for r in result],
                   ensure_ascii=False),
    )
    return result


def _evict_dict_cache(dict_types: set[str]) -> None:
    """写操作后删除相关类型的缓存（对齐若依 CacheUtils.deleteObject）。"""
    for dict_type in dict_types:
        if dict_type:
            redis_client.delete(_dict_cache_key(dict_type))


def select_dict_data_list(query: DictDataPageQuery, db: Session) -> tuple[list[DictDataResp], int]:
    """分页查询字典数据列表（对应 selectDictDataList，含停用数据）。"""
    stmt = select(DictData)
    if query.dict_type:
        stmt = stmt.where(DictData.dict_type == query.dict_type)
    if query.dict_label:
        stmt = stmt.where(DictData.dict_label.like(f"%{query.dict_label}%"))
    if query.status:
        stmt = stmt.where(DictData.status == query.status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DictData.dict_type, DictData.dict_sort, DictData.dict_code)
        .limit(query.page_size)
        .offset((query.page_num - 1) * query.page_size)
    ).all()
    return [DictDataResp.model_validate(r) for r in rows], total


def select_dict_data_detail(dict_code: int, db: Session) -> DictDataResp:
    """字典数据详情。"""
    data = db.get(DictData, dict_code)
    if data is None:
        raise ServiceException("字典数据不存在", code=404)
    return DictDataResp.model_validate(data)


def insert_dict_data(req: DictDataCreate, db: Session) -> bool:
    """新增字典数据（对应 insertDictData：插库后删该类型缓存）。"""
    db.add(DictData(**req.model_dump()))
    db.commit()
    _evict_dict_cache({req.dict_type})
    return True


def update_dict_data(req: DictDataUpdate, db: Session) -> bool:
    """修改字典数据（对应 updateDictData：改库后删新旧类型缓存）。"""
    data = db.get(DictData, req.dict_code)
    if data is None:
        raise ServiceException("字典数据不存在", code=404)

    old_type = data.dict_type
    for key, value in req.model_dump(exclude={"dict_code"}).items():
        setattr(data, key, value)
    db.commit()

    # 类型可能被修改，新旧两个键都要失效
    _evict_dict_cache({old_type, req.dict_type})
    return True


def delete_dict_data_by_ids(dict_codes: list[int], db: Session) -> bool:
    """批量删除字典数据（对应 deleteDictDataByIds：物理删除后删对应类型缓存）。"""
    rows = db.scalars(
        select(DictData).where(DictData.dict_code.in_(dict_codes))
    ).all()
    if not rows:
        return True

    affected_types = {r.dict_type for r in rows}
    db.execute(delete(DictData).where(DictData.dict_code.in_(dict_codes)))
    db.commit()
    _evict_dict_cache(affected_types)
    return True


def refresh_dict_cache(db: Session) -> bool:
    """刷新字典缓存（对应 resetDictCache：先清空全部，再从全表重新回填）。"""
    # 1. 清空全部字典缓存（注意：模板带占位符，通配必须直接写字符串 "sys_dict:*"）
    for key in redis_client.scan_iter("sys_dict:*"):
        redis_client.delete(key)

    # 2. 从字典数据全表回填（仅启用状态，与查询口径一致）
    rows = db.scalars(
        select(DictData).where(DictData.status == "0")
        .order_by(DictData.dict_type, DictData.dict_sort, DictData.dict_code)
    ).all()
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        item = DictDataResp.model_validate(r).model_dump(mode="json", by_alias=True)
        grouped.setdefault(r.dict_type, []).append(item)
    for dict_type, items in grouped.items():
        redis_client.set(_dict_cache_key(dict_type), json.dumps(items, ensure_ascii=False))
    return True


# ==================== 字典类型 ====================


def check_dict_type_unique(dict_type: str, dict_id: int | None, db: Session) -> bool:
    """字典类型唯一性校验（对应 checkDictTypeUnique）。返回 True 表示可用。"""
    stmt = select(DictType).where(DictType.dict_type == dict_type)
    if dict_id is not None:
        stmt = stmt.where(DictType.dict_id != dict_id)
    return db.scalars(stmt).first() is None


def select_dict_type_list(query: DictTypePageQuery, db: Session) -> tuple[list[DictTypeResp], int]:
    """分页查询字典类型列表（对应 selectDictTypeList）。"""
    stmt = select(DictType)
    if query.dict_name:
        stmt = stmt.where(DictType.dict_name.like(f"%{query.dict_name}%"))
    if query.dict_type:
        stmt = stmt.where(DictType.dict_type.like(f"%{query.dict_type}%"))
    if query.status:
        stmt = stmt.where(DictType.status == query.status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(DictType.dict_id)
        .limit(query.page_size)
        .offset((query.page_num - 1) * query.page_size)
    ).all()
    return [DictTypeResp.model_validate(r) for r in rows], total


def select_dict_type_detail(dict_id: int, db: Session) -> DictTypeResp:
    """字典类型详情。"""
    dict_type = db.get(DictType, dict_id)
    if dict_type is None:
        raise ServiceException("字典类型不存在", code=404)
    return DictTypeResp.model_validate(dict_type)


def select_dict_type_options(db: Session) -> list[DictTypeResp]:
    """全部字典类型（对应 optionselect：字典类型下拉框）。"""
    rows = db.scalars(select(DictType).order_by(DictType.dict_id)).all()
    return [DictTypeResp.model_validate(r) for r in rows]


def insert_dict_type(req: DictTypeCreate, db: Session) -> bool:
    """新增字典类型（对应 insertDictType：唯一校验 + 插库）。"""
    db.add(DictType(**req.model_dump()))
    db.commit()
    return True


def update_dict_type(req: DictTypeUpdate, db: Session) -> bool:
    """修改字典类型（对应 updateDictType：改 dict_type 时同步字典数据并删缓存）。"""
    dict_type = db.get(DictType, req.dict_id)
    if dict_type is None:
        raise ServiceException("字典类型不存在", code=404)

    old_type = dict_type.dict_type
    for key, value in req.model_dump(exclude={"dict_id"}).items():
        setattr(dict_type, key, value)

    # 类型标识被修改时，字典数据的 dict_type 冗余列必须级联同步
    if req.dict_type != old_type:
        data_rows = db.scalars(
            select(DictData).where(DictData.dict_type == old_type)
        ).all()
        for r in data_rows:
            r.dict_type = req.dict_type
    db.commit()

    _evict_dict_cache({old_type, req.dict_type})
    return True


def delete_dict_type_by_ids(dict_ids: list[int], db: Session) -> bool:
    """批量删除字典类型（对应 deleteDictTypeByIds：有字典数据则拒绝，物理删除）。"""
    rows = db.scalars(select(DictType).where(DictType.dict_id.in_(dict_ids))).all()
    if not rows:
        return True

    # checkDictDataExist：任一类型下仍有字典数据（含停用）即拒绝删除
    affected_types = {r.dict_type for r in rows}
    exists = db.scalar(
        select(func.count()).select_from(DictData).where(DictData.dict_type.in_(affected_types))
    )
    if exists:
        blocked = rows[0].dict_name
        raise ServiceException(f"{blocked}已分配,不能删除")

    for r in rows:
        db.delete(r)
    db.commit()
    _evict_dict_cache(affected_types)
    return True
