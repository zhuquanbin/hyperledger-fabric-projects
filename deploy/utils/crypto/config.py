#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 15:30
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import shutil
from .template import CRYPTO_CONFIG_TEMPLATE
from .gen import ConfigCryptoGenerator

class CryptoConfigure(object):
    def __init__(self, output):
        # crypto and configtx 必须在同一目录下, 存在依赖关系, 该目录下存放 crypto-config.yaml
        self.output = os.path.join(output, "fabric-config")
        if not os.path.exists(self.output):
            os.makedirs(self.output)

    def load_network(self, **kwargs):
        self.fabricNetwork = kwargs.get("network", None)
        if not self.fabricNetwork:
            raise ValueError("Fabric network configuration must be provided")
        self.__init_config_file()

    def __init_config_file(self):
        """
        Init Config File Example
        """
        generator = ConfigCryptoGenerator(self.filepath, **self.fabricNetwork)
        generator.run()

    @property
    def filepath(self):
        return os.path.join(self.output, "crypto-config.yaml")

    def clean_output(self):
        """
        清空输出目录
        :return:
        """
        if os.path.exists(self.output):
            shutil.rmtree(self.output)
