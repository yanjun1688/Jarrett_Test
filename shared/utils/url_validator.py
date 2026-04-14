"""
URL 安全验证工具

防止 SSRF（Server-Side Request Forgery）攻击。
在发送 HTTP 请求前验证目标 URL，拒绝内网地址和危险协议。
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 禁止访问的私有/保留 IP 段
_BLOCKED_NETWORKS = [
    ipaddress.ip_network('127.0.0.0/8'),       # Loopback
    ipaddress.ip_network('10.0.0.0/8'),         # Private A
    ipaddress.ip_network('172.16.0.0/12'),      # Private B
    ipaddress.ip_network('192.168.0.0/16'),     # Private C
    ipaddress.ip_network('169.254.0.0/16'),     # Link-local / Cloud metadata
    ipaddress.ip_network('0.0.0.0/8'),          # Current network
    ipaddress.ip_network('100.64.0.0/10'),      # Shared address space
    ipaddress.ip_network('198.18.0.0/15'),      # Benchmarking
    ipaddress.ip_network('::1/128'),            # IPv6 loopback
    ipaddress.ip_network('fc00::/7'),           # IPv6 unique local
    ipaddress.ip_network('fe80::/10'),          # IPv6 link-local
]

# 允许的协议
_ALLOWED_SCHEMES = {'http', 'https'}


def _is_private_ip(ip_str: str) -> bool:
    """检查 IP 地址是否属于私有/保留网段"""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in _BLOCKED_NETWORKS)
    except ValueError:
        return False


def validate_request_url(url: str) -> str:
    """
    验证请求 URL 是否安全（防 SSRF）。

    检查项：
    1. URL 格式合法
    2. 协议为 http 或 https
    3. 主机名解析后不指向私有/保留 IP

    Args:
        url: 待验证的 URL

    Returns:
        验证通过的 URL（原样返回）

    Raises:
        ValueError: URL 不合法或指向被禁止的地址
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)

    # 检查协议
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(f"URL scheme '{parsed.scheme}' is not allowed. Only http/https permitted.")

    hostname: str | None = parsed.hostname
    if not hostname or not isinstance(hostname, str):
        raise ValueError("URL must contain a valid hostname")

    # 先检查是否直接是 IP 地址
    if _is_private_ip(hostname):
        raise ValueError(f"Access to private/reserved IP address is not allowed: {hostname}")

    # DNS 解析检查
    try:
        addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for addr_info in addr_infos:
            sockaddr = addr_info[4]
            if isinstance(sockaddr, tuple) and len(sockaddr) > 0:
                ip_str: str = str(sockaddr[0])
                if _is_private_ip(ip_str):
                    raise ValueError(
                        f"Hostname '{hostname}' resolves to private/reserved IP: {ip_str}"
                    )
    except socket.gaierror:
        # DNS 解析失败，让后续 HTTP 客户端处理
        logger.warning(f"DNS resolution failed for {hostname}, allowing request to proceed")

    return url
