# coding=UTF-8
# Author:龙翔@https://gitee.com/NelsonLong/lanzouyun_down_script
# Software:PyCharm
# Time:2026-10-25 11:37:36
# File:lanzou.py
import os
import time
import json
import urllib.error
import urllib.request

from typing import Optional
from urllib.parse import urlencode
from dataclasses import (
    dataclass,
    field
)
from rich.progress import Progress

from detect_system_proxy import resolve_proxy


@dataclass
class LanzouConfig:
    cookies: str
    boundary: str = '----WebKitFormBoundaryRc2hTIRnFdKHY5lG'
    proxy: Optional[str] = field(default_factory=resolve_proxy)

    def __post_init__(self):
        self.proxy = resolve_proxy(self.proxy)


class Lanzou:
    def __init__(self, config: LanzouConfig):
        self.config: LanzouConfig = config

    def __multipart_encode(self, fields):
        CRLF = b'\r\n'  # noqa.
        chunks = []
        for item in fields:
            name, value = item[0], item[1]
            if isinstance(value, (list, tuple)):
                filename, data, content_type = value
                if isinstance(data, str):
                    data = data.encode('UTF-8')
                chunks.append(b'--' + self.config.boundary.encode() + CRLF)
                chunks.append(
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'.encode() + CRLF
                )
                chunks.append(f'Content-Type: {content_type}'.encode() + CRLF)
                chunks.append(CRLF)
                chunks.append(data)
                chunks.append(CRLF)
            else:
                if isinstance(value, str):
                    value = value.encode('UTF-8')
                chunks.append(b'--' + self.config.boundary.encode() + CRLF)
                chunks.append(f'Content-Disposition: form-data; name="{name}"'.encode() + CRLF)
                chunks.append(CRLF)
                chunks.append(value)
                chunks.append(CRLF)
        chunks.append(b'--' + self.config.boundary.encode() + b'--' + CRLF)
        return b''.join(chunks)

    def upload_file(self, file_path):
        headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryRc2hTIRnFdKHY5lG',
            'origin': 'https://pc.woozooo.com',
            'referer': 'https://pc.woozooo.com/mydisk.php?item=files&action=index&u=3510832',
            'sec-ch-ua': '"Microsoft Edge";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
        }
        url = 'https://pc.woozooo.com/html5up.php'
        with open(file_path, 'rb') as f:
            file_data = f.read()
        base_name = os.path.basename(file_path)
        now_time = time.strftime('%a %b %d %Y %H:%M:%S GMT 0800 (中国标准时间)', time.localtime())
        files = [
            ['task', '1'],
            ['vie', '2'],
            ['ve', '2'],
            ['id', 'WU_FILE_2'],
            ['name', base_name],
            ['type', ' application/octet-stream'],
            ['lastModifiedDate', now_time],
            ['size', str(len(file_data))],
            ['folder_id_bb_n', '-1'],
            ['upload_file', [base_name, file_data, 'application/octet-stream']],
        ]
        body = self.__multipart_encode(files)
        total = len(body)
        headers['Content-Length'] = str(total)
        headers['Cookie'] = self.config.cookies

        def _iter_body():
            with Progress() as progress:
                task = progress.add_task(base_name, total=total)
                for i in range(0, total, 1024 * 1024):
                    chunk = body[i:i + 1024 * 1024]
                    progress.update(task, advance=len(chunk))
                    yield chunk

        request = urllib.request.Request(url, data=_iter_body(), headers=headers, method='POST')
        opener = urllib.request.build_opener()
        if self.config.proxy:
            opener.add_handler(urllib.request.ProxyHandler({'http': self.config.proxy, 'https': self.config.proxy}))
        try:
            with opener.open(request, timeout=120) as response:
                return json.loads(response.read().decode('UTF-8'))
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode('UTF-8', errors='replace'))

    def get_home_files(self):
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'cache-control': 'no-cache',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://pc.woozooo.com',
            'pragma': 'no-cache',
            'referer': 'https://pc.woozooo.com/mydisk.php?item=files&action=index&u=3510832',
            'sec-ch-ua': '"Microsoft Edge";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
            'x-requested-with': 'XMLHttpRequest',
        }
        url = 'https://pc.woozooo.com/doupload.php'
        params = {'uid': '3510832'}
        data = {'task': '5', 'folder_id': '-1', 'pg': '1', 'vei': 'WV1fXVdWAAwCAAFRDlQ='}
        headers['Cookie'] = self.config.cookies
        full_url = f'{url}?{urlencode(params)}'
        body = urlencode(data).encode('UTF-8')
        request = urllib.request.Request(full_url, data=body, headers=headers, method='POST')
        opener = urllib.request.build_opener()
        if self.config.proxy:
            opener.add_handler(urllib.request.ProxyHandler({'http': self.config.proxy, 'https': self.config.proxy}))
        try:
            with opener.open(request, timeout=120) as response:
                return json.loads(response.read().decode('UTF-8'))
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode('UTF-8', errors='replace'))
