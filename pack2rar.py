# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025-02-24 01:12:00
# File:pack2rar.py
import rarfile


def create_rar(rar_name, files):
    # 创建RAR文件
    with rarfile.RarFile(rar_name, 'w') as rar:
        for file in files:
            rar.write(file)
            print(f'Added {file} to {rar_name}')


if __name__ == '__main__':
    files_to_zip = []  # 要打包的文件
    create_rar('output.rar', files_to_zip)  # 创建RAR文件
