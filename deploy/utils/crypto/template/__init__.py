#!usr/bin/python
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/22 11:05
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

import os
TEMPLATE_PATH = os.path.dirname(os.path.abspath(__file__))
CRYPTO_CONFIG_TEMPLATE = os.path.join(TEMPLATE_PATH, "crypto-config.yaml")

__all__ = ["CRYPTO_CONFIG_TEMPLATE"]
