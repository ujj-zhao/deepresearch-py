"""IP 处理工具（对应若依 IpUtils + AddressUtils）。"""

import socket
from ipaddress import ip_address

import httpx
from fastapi import Request

from ruoyi_fastapi.core.config import settings
from ruoyi_fastapi.core.constant import IP_LOCATION_KEY
from ruoyi_fastapi.core.redis import redis_client

# 未知 IP 占位符（对齐若依 UNKNOWN）
UNKNOWN = "unknown"


def get_client_ip(request: Request) -> str:
    """提取客户端真实 IP（对应 IpUtils.getIpAddr）。"""
    xff = request.headers.get("x-forwarded-for", "")
    if not _is_unknown(xff):
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip", "")
    if not _is_unknown(xri):
        return xri.strip()
    return request.client.host if request.client else UNKNOWN


def _is_internal_ip(ip: str) -> bool:
    """内网 IP 判断（对应 IpUtils.isInternalIp）。

    ipaddress 的 is_private 覆盖 10/172.16-31/192.168 三段 + loopback + link-local。
    """
    if not _is_valid_ip(ip):
        return False
    return ip_address(ip).is_private


def _is_valid_ip(ip: str) -> bool:
    """IP 格式校验（对应 IpUtils.isIP，额外支持 IPv6）。"""
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False


def _is_unknown(ip: str | None) -> bool:
    """空值/unknown 判断（对应 IpUtils.isUnknown）。"""
    return not ip or ip.lower() == UNKNOWN


def get_multistage_reverse_proxy_ip(ip: str) -> str:
    """多级反向代理场景取 IP：从右往左找第一个公网 IP（对应 IpUtils.getMultistageReverseProxyIp）。"""
    if "," not in ip:
        return ip
    for segment in reversed(ip.split(",")):
        candidate = segment.strip()
        if not _is_unknown(candidate) and not _is_internal_ip(candidate):
            return candidate
    return ip.split(",")[0].strip()


def get_host_ip() -> str:
    """本机内网 IP（对应 IpUtils.getHostIp；UDP connect 不发包，仅让内核选路由）。"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def get_host_name() -> str:
    """本机主机名（对应 IpUtils.getHostName，monitor/server 模块用）。"""
    return socket.gethostname()


# 归属地查询接口（ip-api 免费接口，UTF-8、中文；对应若依 AddressUtils.IP_URL）
_ADDRESS_API_URL = "http://ip-api.com/json/{ip}?lang=zh-CN&fields=status,country,regionName,city"
# 归属地缓存时长：IP 归属地基本不变，7 天足够
_IP_LOCATION_EXPIRE = 7 * 24 * 3600


def get_real_address_by_ip(ip: str) -> str:
    """查询 IP 归属地（对应若依 AddressUtils.getRealAddressByIP）。

    无效 IP → UNKNOWN；内网 IP 不发外网请求 → "内网IP"；
    外网查询结果回填 Redis；任何失败返回 UNKNOWN，绝不让调用方（登录流程）挂掉。
    """
    if not _is_valid_ip(ip):
        return UNKNOWN
    if _is_internal_ip(ip):
        return "内网IP"

    # 先查缓存
    cache_key = IP_LOCATION_KEY.format(ip)
    cached = redis_client.get(cache_key)
    if cached is not None:
        return cached

    # 配置开关关闭时不发外网请求（对应若依 ruoyi.addressEnabled）
    if not settings.ADDRESS_ENABLED:
        return UNKNOWN

    try:
        resp = httpx.get(_ADDRESS_API_URL.format(ip=ip), timeout=5)
        data = resp.json()
        if data.get("status") != "success":
            return UNKNOWN
        address = " ".join(
            part
            for part in (data.get("country"), data.get("regionName"), data.get("city"))
            if part
        )
    except (httpx.HTTPError, ValueError):
        return UNKNOWN

    redis_client.set(cache_key, address, ex=_IP_LOCATION_EXPIRE)
    return address
