# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-25 00:41:14
# File:create_release_on_gitee.py
import json
import urllib.parse
import urllib.error
import urllib.request
from typing import Optional
from dataclasses import (
    dataclass,
    field
)

from utils import logging
from detect_system_proxy import resolve_proxy


@dataclass
class GiteeConfig:
    token: str
    owner: str
    repository: str
    tag_name: str  # vx.x.x
    name: str  # vx.x.x
    release_note_path: str
    target_commitish: str = 'main'  # noqa
    proxy: Optional[str] = field(default_factory=resolve_proxy)


def create_release_on_gitee(gitee_config: GiteeConfig):
    if not gitee_config.token:
        logging.info('请设置环境变量:GITEE_ACCESS_TOKEN。')
        return None
    url = f'https://gitee.com/api/v5/repos/{gitee_config.owner}/{gitee_config.repository}/releases'
    with open(gitee_config.release_note_path, encoding='UTF-8') as file:  # 用with确保文件句柄被关闭。
        release_note: str = file.read()

    data = {
        'access_token': gitee_config.token,
        'tag_name': gitee_config.tag_name,
        'name': gitee_config.name,
        'body': release_note,
        'target_commitish': gitee_config.target_commitish,  # noqa.
    }
    request = urllib.request.Request(
        url=url,
        data=urllib.parse.urlencode(data).encode('UTF-8'),
        headers={'User-Agent': 'TRMD-Release-Script'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode('UTF-8'))
    except urllib.error.HTTPError as e:  # urllib遇4xx/5xx直接抛异常(不像requests返回响应),需捕获才读得到错误响应体。
        logging.error(f'请求出错:原因:"{e}"')
        payload = json.loads(e.read().decode('UTF-8'))

    logging.info(payload)
