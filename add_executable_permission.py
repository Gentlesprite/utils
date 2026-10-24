# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-03-09 22:36:00
# File:add_executable_permission.py
import os
import stat
import sys

def add_executable_permission(file_path: str) -> bool:
    """确保文件具有执行权限(仅Linux/macOS)。"""
    if sys.platform not in ('linux', 'darwin'):
        return True
    try:
        st = os.stat(file_path)
        mode = st.st_mode
        if not (mode & stat.S_IXUSR):
            os.chmod(file_path, mode | stat.S_IXUSR)
            print(f'已为"{file_path}"添加执行权限。')
            return True
        return False
    except Exception as e:
        print(f'添加执行权限失败:{e}。')
        return False