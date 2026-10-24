# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-24 19:23:07
# File:download_github_latest_release.py
import os
import re
import sys
import json
import logging
from dataclasses import dataclass
from typing import (
    Dict,
    Union,
    Optional
)
from urllib.parse import urlparse
from urllib.request import (
    Request,
    build_opener,
    ProxyHandler
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import logging
from get_file_hash import get_file_hash
from detect_system_proxy import resolve_proxy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIRECTORY = os.path.join(PROJECT_ROOT, 'output')
GITHUB_LATEST_RELEASE_API = 'https://api.github.com/repos/{repository}/releases/latest'
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')  # noqa.
VERSION_PATTERN = re.compile(r'(\d+\.\d+\.\d+)')
CHUNK_SIZE = 1024 * 1024  # 下载分块大小(1MiB)。


@dataclass
class DownloadResult:
    status: bool = None
    version: Union[str, None] = None
    digest_map: Union[Dict[str, str], None] = None


def normalize_version(tag: str) -> str:
    match = VERSION_PATTERN.search(tag or '')
    return match.group(1) if match else (tag or '').lstrip('v')


def github_headers(token: str) -> dict:
    headers = {'User-Agent': USER_AGENT, 'Accept': 'application/vnd.github+json'}
    token = token or os.environ.get('GITHUB_TOKEN', '')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def fetch_latest_release(repository: str, token: str = '', proxy: str = '') -> dict:
    url = GITHUB_LATEST_RELEASE_API.format(repository=repository)
    logging.info(f'正在获取最新release:"{url}"。')
    request = Request(url=url, headers=github_headers(token))
    with __open(request, proxy) as response:
        return json.loads(response.read().decode('UTF-8'))


def __ensure_socks(proxy: str) -> None:
    try:
        import socks
        import socket
    except ImportError:
        raise RuntimeError('使用socks代理需先安装依赖:pip install PySocks')
    parsed = urlparse(proxy)
    proxy_type = {'socks4': socks.SOCKS4, 'socks5h': socks.SOCKS5}.get(parsed.scheme, socks.SOCKS5)
    socks.set_default_proxy(proxy_type, parsed.hostname, parsed.port)
    socket.socket = socks.socksocket


def __open(request, proxy: str, timeout: int = 60):
    if proxy and proxy.lower().startswith('socks'):
        __ensure_socks(proxy)
        return build_opener(ProxyHandler({})).open(request, timeout=timeout)  # 走socks socket,urllib层不再用http代理。
    if proxy:
        return build_opener(ProxyHandler({'http': proxy, 'https': proxy})).open(request, timeout=timeout)
    return build_opener(ProxyHandler({})).open(request, timeout=timeout)  # 直连,且不受环境变量代理干扰。


def current_output_version() -> str:
    if not os.path.isdir(OUTPUT_DIRECTORY):
        return ''
    for name in sorted(os.listdir(OUTPUT_DIRECTORY)):
        if name.lower().endswith('.rar'):
            return normalize_version(name)
    return ''


def download_assets(assets: list, token: str = '', proxy: str = '') -> None:
    """下载最新release的.rar;以sha256(而非文件名版本)决定是否需要重新下载。

    规则:
      1. 先清理output里不属于本次release的.rar(历史版本残留),避免其被一并发送;
      2. 本地已存在同名文件时比对sha256:一致则跳过下载,不一致(或远程未提供digest)
         则删除后重新下载。
    """
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    keep: set = {str(asset['name']) for asset in assets}
    for name in os.listdir(OUTPUT_DIRECTORY):
        if name.lower().endswith('.rar') and name not in keep:
            os.remove(os.path.join(OUTPUT_DIRECTORY, name))
            logging.info(f'已清理不属于本次release的rar:"{name}"。')
    for asset in assets:
        name: str = asset['name']
        url: str = asset['browser_download_url']
        size: int = int(asset.get('size') or 0)
        target: str = os.path.join(OUTPUT_DIRECTORY, name)
        remote_sha: str = str(asset.get('digest') or '').split(':', 1)[-1].strip().lower()
        if os.path.isfile(target):
            # 远程未提供digest时无法比对,按"不一致"处理,重新下载以确保内容正确。
            if remote_sha and get_file_hash(target, 'sha256').lower() == remote_sha:
                logging.info(f'已存在且sha256一致,跳过:{name}')
                continue
            logging.info(f'已存在但sha256不一致(或远程未提供digest),删除后重新下载:{name}')
            os.remove(target)
        logging.info(f'正在下载{name}({size / 1048576:.1f}MiB) -> {target}')
        request = Request(url=url, headers=github_headers(token))
        downloaded = 0
        with __open(request, proxy) as response, open(target, 'wb') as file:
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                file.write(chunk)
                downloaded += len(chunk)
        logging.info(f'已下载{name}({downloaded}字节)。')


def verify_sha256(digest_map: dict) -> bool:
    if not digest_map:
        logging.info('最新release的资产未提供sha256(digest字段),跳过校验。')
        return True
    all_match = True
    for name, digest in digest_map.items():
        target = os.path.join(OUTPUT_DIRECTORY, name)
        if not os.path.isfile(target):
            logging.info(f'校验跳过:{name}(output中不存在)。')
            continue
        remote_sha = digest.split(':', 1)[-1].strip().lower()
        local_sha = get_file_hash(target, 'sha256').lower()
        if local_sha == remote_sha:
            logging.info(f'sha256一致:{name}')
        else:
            all_match = False
            logging.warning(f'sha256不一致:{name},本地={local_sha},远程={remote_sha}。')
    return all_match


def download(
        repository: str,
        github_token: Optional[str] = None,
        proxy: Optional[str] = None
) -> DownloadResult:
    proxy = resolve_proxy(proxy)
    logging.info(f'使用代理:"{proxy or "直连"}"。')
    try:
        release = fetch_latest_release(repository, github_token, proxy)
    except Exception as e:
        result = DownloadResult(
            status=False,
            version=None,
            digest_map=None
        )
        logging.error(f'获取最新release失败,结果:"{result}",原因:"{e}"')
        return result
    tag: str = release.get('tag_name') or ''
    latest_version: str = normalize_version(tag)
    rar_assets = [a for a in (release.get('assets') or []) if str(a.get('name', '')).lower().endswith('.rar')]
    logging.info(f'仓库最新release:{tag or "(无)"},含{len(rar_assets)}个.rar资产。')
    # 下载前先检查output现有.rar的版本。
    current_version: str = current_output_version()
    logging.info(f'output当前.rar版本:{current_version or "(无)"}。')
    if not rar_assets:
        logging.info('最新release里没有.rar资产,跳过下载。')
    elif not current_version:
        logging.info('output没有.rar,直接下载最新版本。')
        download_assets(rar_assets, github_token, proxy)
    elif current_version != latest_version:
        logging.info(f'output版本({current_version})不是最新({latest_version}),下载最新版本。')
        download_assets(rar_assets, github_token, proxy)
    else:
        logging.info(f'output已是最新版本({current_version}),跳过下载。')
    # 下载完成后,用GitHub给的sha256(资产digest字段)校验本地文件是否一致。
    digest_map = {a['name']: a.get('digest', '') for a in rar_assets if a.get('digest')}
    if verify_sha256(digest_map):
        result = DownloadResult(status=True, version=latest_version, digest_map=digest_map)
        logging.info(f'校验通过:文件sha256与远程一致,结果:"{result}"。')
        return result
    logging.warning('校验未通过:请对照上面的sha256不一致项,结果:"{result}"。')
    result = DownloadResult(status=False, version=latest_version, digest_map=digest_map)
    return result
