# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-25 01:20:00
# File:create_release_on_github.py
import json
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import (
    dataclass,
    field
)
from typing import Optional

from . import logging
from .detect_system_proxy import resolve_proxy
from .download_github_latest_release import (  # 复用GitHub请求封装:鉴权头与带代理的发送(支持http/https/socks)。
    github_headers,
    __open
)

GITHUB_RELEASE_API = 'https://api.github.com/repos/{owner}/{repository}/releases'
GITHUB_RELEASE_BY_TAG_API = 'https://api.github.com/repos/{owner}/{repository}/releases/tags/{tag}'
GITHUB_RELEASE_BY_ID_API = 'https://api.github.com/repos/{owner}/{repository}/releases/{release_id}'
GITHUB_TAG_REF_API = 'https://api.github.com/repos/{owner}/{repository}/git/ref/tags/{tag}'


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

    def __post_init__(self):
        # default_factory仅在"未传proxy"时生效;显式传入'auto'/'none'/裸地址时必须在此统一解析,
        # 否则'auto'会被当成代理地址直接交给ProxyHandler,导致连不上。resolve_proxy幂等,重复调用无副作用。
        self.proxy = resolve_proxy(self.proxy)


def tag_exists(github_config: GithubConfig) -> bool:
    """判断远程仓库是否已存在该tag(只查tag,不查发行版);404视为不存在,其它错误向上抛出。"""
    url = GITHUB_TAG_REF_API.format(
        owner=github_config.owner,
        repository=github_config.repository,
        tag=urllib.parse.quote(github_config.tag_name)
    )
    request = urllib.request.Request(url=url, headers=github_headers(github_config.token), method='GET')
    try:
        with __open(request, github_config.proxy) as response:
            json.loads(response.read().decode('UTF-8'))
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def get_release_by_tag(github_config: GithubConfig) -> Optional[dict]:
    """按tag查询已存在的发行版(release);不存在(404)返回None,其它错误向上抛出。"""
    url = GITHUB_RELEASE_BY_TAG_API.format(
        owner=github_config.owner,
        repository=github_config.repository,
        tag=urllib.parse.quote(github_config.tag_name)  # tag可能含特殊字符,需URL编码。
    )
    request = urllib.request.Request(url=url, headers=github_headers(github_config.token), method='GET')
    try:
        with __open(request, github_config.proxy) as response:
            return json.loads(response.read().decode('UTF-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def update_release(github_config: GithubConfig, release_id: int, release_note: str) -> dict:
    """PATCH更新已有发行版的标题与说明。

    只改name与body,不会动已上传的附件(流水线产物不受影响);若该release是草稿,
    可在data里加'draft': False一并发布。
    """
    url = GITHUB_RELEASE_BY_ID_API.format(
        owner=github_config.owner,
        repository=github_config.repository,
        release_id=release_id
    )
    headers = github_headers(github_config.token)  # GitHub强制要求User-Agent,该函数已带上UA与Bearer鉴权。
    headers['Content-Type'] = 'application/json'  # GitHub的release接口接收JSON,而非表单。
    request = urllib.request.Request(
        url=url,
        data=json.dumps({'name': github_config.name, 'body': release_note}).encode('UTF-8'),
        headers=headers,
        method='PATCH'
    )
    with __open(request, github_config.proxy) as response:
        return json.loads(response.read().decode('UTF-8'))


def post_release(github_config: GithubConfig, release_note: str) -> dict:
    """tag已存在但没有发行版时,创建发行版并写入release note。"""
    url = GITHUB_RELEASE_API.format(owner=github_config.owner, repository=github_config.repository)
    headers = github_headers(github_config.token)
    headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(
        url=url,
        data=json.dumps({
            'tag_name': github_config.tag_name,
            'name': github_config.name,
            'body': release_note,
            'target_commitish': github_config.target_commitish,  # noqa.
        }).encode('UTF-8'),
        headers=headers,
        method='POST'
    )
    with __open(request, github_config.proxy) as response:
        return json.loads(response.read().decode('UTF-8'))


def upsert_release_on_github(github_config: GithubConfig):
    """写入GitHub的release note,只针对远程仓库已存在的tag。

    规则:
      1. 远程没有这个tag    → 直接跳过,既不创建tag也不创建release;
      2. 有tag但没有发行版  → 创建发行版并写入release note;
      3. 有tag且已有发行版  → 更新其release note(不影响已上传的附件)。
    """
    if not github_config.token:
        logging.info('请设置环境变量:GITHUB_TOKEN。')
        return None
    if not tag_exists(github_config):
        logging.info(f'远程仓库没有tag"{github_config.tag_name}",跳过(既不创建tag也不创建release)。')
        return None
    with open(github_config.release_note_path, encoding='UTF-8') as file:  # 用with确保文件句柄被关闭。
        release_note: str = file.read()
    logging.info(f'使用代理:"{github_config.proxy or "直连"}"。')
    try:
        existing: Optional[dict] = get_release_by_tag(github_config)
        if existing and existing.get('id'):
            logging.info(f'tag"{github_config.tag_name}"已有发行版(id={existing["id"]}),更新其release note。')
            payload = update_release(github_config, existing['id'], release_note)
        else:
            logging.info(f'tag"{github_config.tag_name}"尚无发行版,创建发行版并写入release note。')
            payload = post_release(github_config, release_note)
    except urllib.error.HTTPError as e:  # urllib遇4xx/5xx直接抛异常,需捕获才读得到错误响应体。
        logging.error(f'请求出错:原因:"{e}"')
        raw: str = e.read().decode('UTF-8', errors='replace')
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:  # 网关异常时返回的是HTML,不是JSON,原样保留避免二次抛异常。
            payload = raw

    logging.info(payload)
    return payload
