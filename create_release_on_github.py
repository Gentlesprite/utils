# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-25 01:20:00
# File:create_release_on_github.py
import json
import urllib.error
import urllib.request
from dataclasses import (
    dataclass,
    field
)
from typing import Optional

from utils import logging
from detect_system_proxy import resolve_proxy
from download_github_latest_release import (  # 复用GitHub请求封装:鉴权头与带代理的发送(支持http/https/socks)。
    github_headers,
    __open
)

GITHUB_RELEASE_API = 'https://api.github.com/repos/{owner}/{repository}/releases'


@dataclass
class GithubConfig:
    token: str
    owner: str
    repository: str
    tag_name: str  # vx.x.x
    name: str  # vx.x.x
    release_note_path: str
    target_commitish: str = 'main'  # noqa
    proxy: Optional[str] = field(default_factory=resolve_proxy)


def create_release_on_github(github_config: GithubConfig):
    if not github_config.token:
        logging.info('请设置环境变量:GITHUB_TOKEN。')
        return None
    url = GITHUB_RELEASE_API.format(owner=github_config.owner, repository=github_config.repository)
    with open(github_config.release_note_path, encoding='UTF-8') as file:  # 用with确保文件句柄被关闭。
        release_note: str = file.read()
    proxy = github_config.proxy
    logging.info(f'使用代理:"{proxy or "直连"}"。')

    data = {
        'tag_name': github_config.tag_name,
        'name': github_config.name,
        'body': release_note,
        'target_commitish': github_config.target_commitish,  # noqa.
    }
    headers = github_headers(github_config.token)  # GitHub强制要求User-Agent,该函数已带上UA与Bearer鉴权。
    headers['Content-Type'] = 'application/json'  # GitHub的release接口接收JSON,而非表单。
    request = urllib.request.Request(
        url=url,
        data=json.dumps(data).encode('UTF-8'),
        headers=headers,
        method='POST'
    )
    try:
        with __open(request, proxy) as response:
            payload = json.loads(response.read().decode('UTF-8'))
    except urllib.error.HTTPError as e:  # urllib遇4xx/5xx直接抛异常(不像requests返回响应),需捕获才读得到错误响应体。
        logging.error(f'请求出错:原因:"{e}"')
        payload = json.loads(e.read().decode('UTF-8'))

    logging.info(payload)
    return payload
