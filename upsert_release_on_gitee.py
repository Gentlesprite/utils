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

GITEE_RELEASE_API = 'https://gitee.com/api/v5/repos/{owner}/{repository}/releases'
GITEE_RELEASE_BY_TAG_API = 'https://gitee.com/api/v5/repos/{owner}/{repository}/releases/tags/{tag}'
GITEE_RELEASE_BY_ID_API = 'https://gitee.com/api/v5/repos/{owner}/{repository}/releases/{release_id}'
GITEE_TAGS_API = 'https://gitee.com/api/v5/repos/{owner}/{repository}/tags'
USER_AGENT = 'TRMD-Release-Script'
PER_PAGE = 100  # Gitee的tags接口每页最多100条。


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

    def __post_init__(self):
        # default_factory仅在"未传proxy"时生效;显式传入'auto'/'none'/裸地址时必须在此统一解析,
        # 否则'auto'会被当成代理地址直接交给ProxyHandler,导致连不上。resolve_proxy幂等,重复调用无副作用。
        self.proxy = resolve_proxy(self.proxy)


def __get(gitee_config: GiteeConfig, url: str, params: Optional[dict] = None):
    """GET请求:access_token与额外参数拼在query里,返回解析后的响应。"""
    query = {'access_token': gitee_config.token}
    if params:
        query.update(params)
    request = urllib.request.Request(
        url=f'{url}?{urllib.parse.urlencode(query)}',
        headers={'User-Agent': USER_AGENT},
        method='GET'
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode('UTF-8'))


def __submit(gitee_config: GiteeConfig, url: str, data: dict, method: str):
    """POST/PATCH请求:access_token随表单提交(Gitee接口为表单编码,不是JSON)。"""
    payload = dict(data)
    payload['access_token'] = gitee_config.token
    request = urllib.request.Request(
        url=url,
        data=urllib.parse.urlencode(payload).encode('UTF-8'),
        headers={'User-Agent': USER_AGENT},
        method=method
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode('UTF-8'))


def tag_exists(gitee_config: GiteeConfig) -> bool:
    """判断远程仓库是否已存在该tag。

    Gitee没有"按名称查单个tag"的接口,只能分页遍历tags列表比对名称;
    Gitee同步GitHub后tag是存在的,故这里能正确识别"有tag但无发行版"的情形。
    """
    url = GITEE_TAGS_API.format(owner=gitee_config.owner, repository=gitee_config.repository)
    page = 1
    while True:
        tags = __get(gitee_config, url, {'page': page, 'per_page': PER_PAGE})
        if not isinstance(tags, list) or not tags:
            return False
        if any(str(tag.get('name', '')) == gitee_config.tag_name for tag in tags):
            return True
        if len(tags) < PER_PAGE:  # 不足一页,说明已是最后一页。
            return False
        page += 1


def get_release_by_tag(gitee_config: GiteeConfig) -> Optional[dict]:
    """按tag查询已存在的发行版;不存在(404)返回None,其它错误向上抛出。"""
    url = GITEE_RELEASE_BY_TAG_API.format(
        owner=gitee_config.owner,
        repository=gitee_config.repository,
        tag=urllib.parse.quote(gitee_config.tag_name)
    )
    try:
        return __get(gitee_config, url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def update_release(gitee_config: GiteeConfig, release_id: int, release_note: str):
    """PATCH更新已有发行版的标题与说明(不动已上传的附件)。"""
    url = GITEE_RELEASE_BY_ID_API.format(
        owner=gitee_config.owner,
        repository=gitee_config.repository,
        release_id=release_id
    )
    return __submit(gitee_config, url, {'name': gitee_config.name, 'body': release_note}, 'PATCH')


def post_release(gitee_config: GiteeConfig, release_note: str):
    """tag已存在但没有发行版时,创建发行版并写入release note。"""
    url = GITEE_RELEASE_API.format(owner=gitee_config.owner, repository=gitee_config.repository)
    return __submit(gitee_config, url, {
        'tag_name': gitee_config.tag_name,
        'name': gitee_config.name,
        'body': release_note,
        'target_commitish': gitee_config.target_commitish,  # noqa.
    }, 'POST')


def create_release_on_gitee(gitee_config: GiteeConfig):
    """写入Gitee的release note,只针对远程仓库已存在的tag。

    规则:
      1. 远程没有这个tag    → 直接跳过,既不创建tag也不创建release;
      2. 有tag但没有发行版  → 创建发行版并写入release note
         (Gitee同步GitHub的tag后正是这种情形,所以必须查tag而不是查发行版);
      3. 有tag且已有发行版  → 更新其release note。
    """
    if not gitee_config.token:
        logging.info('请设置环境变量:GITEE_ACCESS_TOKEN。')
        return None
    if not tag_exists(gitee_config):
        logging.info(f'远程仓库没有tag"{gitee_config.tag_name}",跳过(既不创建tag也不创建release)。')
        return None
    with open(gitee_config.release_note_path, encoding='UTF-8') as file:  # 用with确保文件句柄被关闭。
        release_note: str = file.read()
    try:
        existing: Optional[dict] = get_release_by_tag(gitee_config)
        if existing and existing.get('id'):
            logging.info(f'tag"{gitee_config.tag_name}"已有发行版(id={existing["id"]}),更新其release note。')
            payload = update_release(gitee_config, existing['id'], release_note)
        else:
            logging.info(f'tag"{gitee_config.tag_name}"尚无发行版,创建发行版并写入release note。')
            payload = post_release(gitee_config, release_note)
    except urllib.error.HTTPError as e:  # urllib遇4xx/5xx直接抛异常,需捕获才读得到错误响应体。
        logging.error(f'请求出错:原因:"{e}"')
        raw: str = e.read().decode('UTF-8', errors='replace')
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:  # 网关异常时返回的是HTML,不是JSON,原样保留避免二次抛异常。
            payload = raw

    logging.info(payload)
    return payload
