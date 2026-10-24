# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# File:detect_system_proxy.py
import os
import re
import sys
import platform
from typing import Optional


def parse_proxy_url(proxy_url: str) -> Optional[dict]:
    try:
        if not proxy_url:
            return None
        proxy_url_pattern = re.compile(r'^(?:(https?|socks[45][ah]?)://)?(?:[^@]*@)?([^:]+):(\d+)/*$')
        match = proxy_url_pattern.match(proxy_url.strip().lower())
        if not match:
            return None
        scheme, hostname, port = match.group(1), match.group(2), match.group(3)
        if not scheme:
            scheme = 'http'
        elif scheme in ('socks4a', 'socks5h'):  # socks4a/socks5h统一为socks4/socks5。
            scheme = scheme[:-1]
        try:
            port = int(port)
        except ValueError:
            return None
        if not (0 <= port <= 65535):
            return None
        return {'scheme': scheme, 'hostname': hostname, 'port': port}
    except Exception:  # noqa.
        return None


def get_unix_proxy() -> Optional[dict]:
    for var in ('http_proxy', 'HTTP_PROXY', 'https_proxy', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
        proxy_url = os.environ.get(var)
        if proxy_url:
            proxy_info = parse_proxy_url(proxy_url)
            if proxy_info:
                return proxy_info
    return None


def get_windows_proxy() -> Optional[dict]:
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Internet Settings'
        ) as key:
            proxy_enable, _ = winreg.QueryValueEx(key, 'ProxyEnable')
            if not proxy_enable:
                return None
            proxy_server, _ = winreg.QueryValueEx(key, 'ProxyServer')
            if not proxy_server:
                return None
            proxy_server_pattern = re.compile(r'(\w+)=([^;]+)')
            proxy_info = {proto.lower(): addr for proto, addr in proxy_server_pattern.findall(proxy_server)}
            if not proxy_info:
                proxy_info['http'] = proxy_server
            proxy_addr = proxy_info.get('http') or proxy_info.get('https') or proxy_info.get('socks')
            if not proxy_addr:
                return None
            addr_pattern = re.compile(r'^([^:]+):(\d+)$')
            addr_match = addr_pattern.match(proxy_addr.strip())
            if not addr_match:
                return None
            hostname = addr_match.group(1)
            try:
                port = int(addr_match.group(2))
            except ValueError:
                return None
            # 判断协议类型。
            lowered = proxy_server.lower()
            scheme = 'http'
            if 'socks5' in lowered:
                scheme = 'socks5'
            elif 'socks4' in lowered:
                scheme = 'socks4'
            elif 'socks=' in lowered:  # 只有socks=没有数字,默认socks5。
                scheme = 'socks5'
            if not (0 <= port <= 65535):
                return None
            return {'scheme': scheme, 'hostname': hostname, 'port': port}
    except (OSError, ValueError):
        return None


def format_proxy(proxy: Optional[dict]) -> str:
    if not proxy:
        return ''
    return f"{proxy.get('scheme', 'http')}://{proxy.get('hostname', '')}:{proxy.get('port', '')}"


def detect_system_proxy() -> str:
    proxy = get_windows_proxy() if platform.system() == 'Windows' else get_unix_proxy()
    return format_proxy(proxy)


def main() -> int:
    proxy = detect_system_proxy()
    if proxy:
        print(f'检测到系统代理:"{proxy}"。', file=sys.stderr)
        return 0
    print('未检测到系统代理。', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
