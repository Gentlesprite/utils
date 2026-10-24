# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-09-18 15:51:00
# File:update_remote.py
import urllib.request

from utils import logging


def refresh_remote_config(url):
    '''访问远程地址，手动刷新jsdelivr缓存。'''
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            body = resp.read().decode('utf-8', errors='ignore')
        logging.info(f'刷新远程配置成功,状态码:"{status}"。')
        logging.info(f'刷新远程配置返回内容:"{body}"')
        return body
    except Exception as e:
        logging.error(f'远程配置刷新失败,原因:"{e}"')
        return None


if __name__ == '__main__':
    refresh_remote_config('https://purge.jsdelivr.net/gh/Gentlesprite/TRMD_CONFIG@main/config.json')
