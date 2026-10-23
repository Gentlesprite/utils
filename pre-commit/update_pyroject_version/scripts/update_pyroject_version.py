# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-10-23 20:20:47
# File:update_pyroject_version.py
import os
import re
import subprocess

VERSION_PATH = ('module', '__init__.py')
VERSION_NAME = '__version__'
VERSION_PATTERN = re.compile(rf"{VERSION_NAME} = '(.*?)'")
PYPROJECT_PATH = ('pyproject.toml',)
PYPROJECT_VERSION_PATTERN = re.compile(r'(?m)^version = "(.*?)"')
REBASE_MARKER_NAMES = ('rebase-merge', 'rebase-apply')


def run_git(args):
    # 执行git命令并返回标准输出。
    result = subprocess.run(['git'] + args, capture_output=True, text=True, encoding='UTF-8')
    return result.stdout


def main():
    root = run_git(['rev-parse', '--show-toplevel']).strip()
    # 如果正在进行rebase,直接退出,避免edit message时钩子改写文件导致rebase中断。
    for marker_name in REBASE_MARKER_NAMES:
        marker_path = run_git(['rev-parse', '--git-path', marker_name]).strip()
        if marker_path and os.path.isdir(os.path.join(root, marker_path)):
            print('正在进行rebase,取消本次更新。')
            return
    init_path = os.path.join(root, *VERSION_PATH)
    pyproject_path = os.path.join(root, *PYPROJECT_PATH)
    # 读不到或文件不存在就什么都不做。
    if not os.path.isfile(init_path) or not os.path.isfile(pyproject_path):
        return
    with open(init_path, 'r', encoding='UTF-8') as file:
        init_content = file.read()
    match = VERSION_PATTERN.search(init_content)
    if not match:
        return
    version = match.group(1)
    if not version:
        return
    with open(pyproject_path, 'r', encoding='UTF-8') as file:
        pyproject_content = file.read()
    new_content = PYPROJECT_VERSION_PATTERN.sub('version = "%s"' % version, pyproject_content, count=1)
    if new_content == pyproject_content:
        return
    with open(pyproject_path, 'w', encoding='UTF-8') as file:
        file.write(new_content)
    relative_path = '/'.join(PYPROJECT_PATH)
    run_git(['add', '--', relative_path])
    print('已更新pyproject.toml的version为%s。' % version)


if __name__ == '__main__':
    main()
