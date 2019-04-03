#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/28 11:14
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
from zipfile import ZipFile
from pathlib import Path


class ConfigZipFile(object):

    def __init__(self, filename):
        """
        配置文件压缩操作
        :param filename: 压缩包名
        """
        self.filename = filename
        base_dir = os.path.dirname(self.filename)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # 去重, 兼容windows
        self.archive_set = set()
        with ZipFile(self.filename, self.open_mode) as fp:
            self.archive_set = set(fp.namelist())

    @property
    def open_mode(self):
        return "a" if os.path.exists(self.filename) else "w"

    def clear(self):
        if os.path.exists(self.filename):
            os.remove(self.filename)

    def contain(self, archive_name):
        return True if Path(archive_name).as_posix() in self.archive_set \
            else False

    def add_file(self, file_path, archive_path):
        """
        添加单个文件
        :param file_path:   要压缩文件的路径
        :param archive_path:归档文件根路径
        :return:
        """
        with ZipFile(self.filename, self.open_mode) as fp:
            file_name = os.path.basename(file_path)
            archive_name = os.path.join(archive_path, file_name)
            if not self.contain(archive_name):
                fp.write(file_path, archive_name)
                self.archive_set.add(Path(archive_name).as_posix())

    def add_directory(self, src_path, archive_root_path):
        """
        添加文件目录
        :param src_path:   要压缩目录的路径
        :param archive_root_path:归档目录根路径
        :return:
        """
        with ZipFile(self.filename, self.open_mode) as fp:
            for root, _, files in os.walk(src_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = Path(file_path).relative_to(src_path)
                    archive_path = os.path.join(archive_root_path, relative_path)
                    if not self.contain(archive_path):
                        fp.write(file_path, archive_path)
                        self.archive_set.add(Path(archive_path).as_posix())

