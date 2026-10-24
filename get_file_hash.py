# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026-09-25 23:32:00
# File:get_file_hash.py
import hashlib


def get_file_hash(file_path, algorithm='sha256'):
    h = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)

    return h.hexdigest()
