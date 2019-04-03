#!usr/bin/python
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/22 11:05
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""


import os
TEMPLATE_PATH = os.path.dirname(os.path.abspath(__file__))


def getTemplateFilePath(template):
    filepath = os.path.join(TEMPLATE_PATH, template)
    if os.path.isfile(filepath):
        return filepath
    else:
        raise FileNotFoundError(f"{template} is not exist!")


ZOOKEEPER_TEMPLATE = getTemplateFilePath("zookeeper.yaml")
KAKFA_TEMPLATE = getTemplateFilePath("kafka.yaml")
ORDERER_TEMPLATE = getTemplateFilePath("orderer.yaml")
ORDERER_CLI_TEMPLATE = getTemplateFilePath("orderer-cli.yaml")
PEER_TEMPLATE = getTemplateFilePath("peer.yaml")
PEER_CLI_TEMPLATE = getTemplateFilePath("peer-cli.yaml")
EXPLORER_TEMPLATE = getTemplateFilePath("explorer.yaml")
EXPLORER_DB_TEMPLATE = getTemplateFilePath("explorer-db.yaml")
EXPLORER_CONFIG_TEMPLATE = getTemplateFilePath("config.json")
GO_SDK_CONFIG_TEMPLATE = getTemplateFilePath("go-sdk-config.yaml")

__all__ = ["ZOOKEEPER_TEMPLATE", "KAKFA_TEMPLATE", "ORDERER_TEMPLATE", "ORDERER_CLI_TEMPLATE", "PEER_TEMPLATE",
           "PEER_CLI_TEMPLATE", "EXPLORER_TEMPLATE", "EXPLORER_DB_TEMPLATE", "EXPLORER_CONFIG_TEMPLATE",
           "GO_SDK_CONFIG_TEMPLATE"]
