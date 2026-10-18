# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026/10/18 14:56
# File:update_date.py
import os
import re
import subprocess
from datetime import datetime

DATATIME_PATH = ('module', '__init__.py')
DATATIME_NAME = '__update_date__'
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DATETIME_PATTERN = re.compile(rf"{DATATIME_NAME} = '(.*?)'")



def run_git(args):
    # 执行git命令并返回标准输出。
    result = subprocess.run(['git'] + args, capture_output=True, text=True, encoding='UTF-8')
    return result.stdout


def main():
    root = run_git(['rev-parse', '--show-toplevel']).strip()
    target = os.path.join(root, *DATATIME_PATH)
    with open(target, 'r', encoding='UTF-8') as file:
        content = file.read()
    now = datetime.now().strftime(DATETIME_FORMAT)
    new_content = DATETIME_PATTERN.sub("%s = '%s'" % (DATATIME_NAME, now), content, count=1)
    if new_content == content:
        return
    with open(target, 'w', encoding='UTF-8') as file:
        file.write(new_content)
    relative_path = '/'.join(DATATIME_PATH)
    run_git(['add', '--', relative_path])
    print('已更新%s为%s。' % (DATATIME_NAME, now))


if __name__ == '__main__':
    main()
