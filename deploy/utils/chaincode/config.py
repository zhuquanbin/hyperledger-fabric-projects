#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
@Author     : luzhao
@Email      : zhao.lu@parcelx.io
@date       : 2/27/2019 11:02 AM
@Description:
-------------------------------------------------
"""
import copy
import json

from hfc.fabric.client import Client
from ruamel.yaml import YAML

from utils import *
from .channel_util import reproduce_channel

logger = logging.getLogger(__name__)


class Config(object):
    """
    NetWorkConfig for chaincode install and instantiate
    """

    def __init__(self, config_path='./gen/network-config/', config_name='network-config-tls.yaml'):
        """ 加载配置"""
        self.config_yaml_path = convert_project_abs_path(os.path.join(config_path, config_name))
        self.config_json_path = convert_project_abs_path(os.path.join(config_path,  'network-mutual-tls.json'))
        with open(self.config_yaml_path, 'r') as fp:
            yaml = YAML()
            self.networkconfig = yaml.load(fp)
        # 使用深拷贝，防止删除属性导致访问self.networkconfig错误
        self.__convert__(copy.deepcopy(self.networkconfig), config_path)
        logger.info(config_path)
        self.client = Client(self.config_json_path)
        reproduce_channel(self.networkconfig, self.client)
        os.environ['GOPATH'] = convert_project_abs_path('chaincode-resources/chaincode')

    def __convert__(self, networkconfig, config_path):
        logger.info("Convert network-config to network-mutual-tls start")
        del networkconfig['channels']
        with open(convert_project_abs_path(os.path.join(config_path, 'network-mutual-tls.json')), 'w') as fw:
            json.dump(networkconfig, fw, sort_keys=False, indent=2, separators=(', ', ': '))
        logger.info("Convert network-config to network-mutual-tls end")
