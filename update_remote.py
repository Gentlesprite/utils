# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-09-18 15:51:00
# File:update_remote.py
import urllib.request


def refresh_remote_config(url):
    '''访问远程地址，手动刷新jsdelivr缓存。'''
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            body = resp.read().decode('utf-8', errors='ignore')
        print('刷新成功，状态码：', status)
        print('返回内容：', body)
        return body
    except Exception as e:
        print('刷新失败：', e)
        return None


if __name__ == '__main__':
    refresh_remote_config('https://purge.jsdelivr.net/gh/Gentlesprite/TRMD_CONFIG@main/config.json')
