#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 15:26
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import subprocess
from utils.tool import FabricRelease
from .config import CryptoConfigure


class CryptoHandler(object):
    def __init__(self, release, configure):
        if isinstance(release, FabricRelease):
            self.release = release
        else:
            raise AttributeError("release type must be <utils.tool.FabricRelease>")

        if isinstance(configure, CryptoConfigure):
            self.configure = configure
        else:
            raise AttributeError("configure type must be <utils.cryptogen.CryptoConfigure>")

    def command(self, option):
        ret = subprocess.run([
            self.release.cryptogen,
            option,
            f"--config=./crypto-config.yaml"
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()

    def gen(self):
        self.command("generate")

    def extend(self):
        self.command("extend")

    def package(self):
        pass


