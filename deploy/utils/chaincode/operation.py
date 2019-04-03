#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
@Author     : luzhao
@Email      : zhao.lu@parcelx.io
@date       : 2/26/2019 5:05 PM
@Description:
-------------------------------------------------
"""
import json
import logging
import os
import shutil

from utils.chaincode.channel_util import upgrade_chaincode, install_chaincode, query_chaincode
from .config import Config, convert_project_abs_path

logger = logging.getLogger(__name__)


class Operation(object):
    def __init__(self, config_path='./gen/network-config/', config_name='network-config-tls.yaml'):
        """
        networkconfig contain more network information
        :param config_path:
        """
        self.config_abs_path = convert_project_abs_path(config_path)
        self.config_path = config_path
        self.config_name = config_name
        self.config = None
        self.networkconfig = None

    def clean_network_config(self):
        """
          清空输出network-config目录
          :return:
          """
        if os.path.exists(self.config_path):
            shutil.rmtree(self.config_path)

    def get_config_instance(self):
        if not self.config:
            self.config = Config(self.config_path, self.config_name)
        if not self.networkconfig:
            self.networkconfig = self.config.networkconfig

    def chaincode_install(self, cc_install_operators):
        """
        install a chaincode to peers
        :return:
        """
        self.get_config_instance()
        logger.info("Chaincode install start")
        if not cc_install_operators:
            raise RuntimeError("cc_install_operators must be not None or size is zero.")
        for cc_install_operator in cc_install_operators:
            if cc_install_operator.is_empty():
                raise RuntimeError("cc_install_operator must be not empty.")

        for chaincode_operation_instance in cc_install_operators:
            """ 初始化网络配置根据配置文件"""
            channel_value = self.networkconfig["channels"].get(chaincode_operation_instance.channel_name)
            # 根据peer_names以及network-config-tls.yaml(default name)来生成peer_map
            peer_map = dict()
            if chaincode_operation_instance.peer_names:
                for per_peer_name in chaincode_operation_instance.peer_names:
                    peer_map[per_peer_name] = channel_value.get("peers").get(per_peer_name)
            # 根据传入的chaincode_names以及配置文件来生成chaincode_name_value map
            chaincode_map = dict()
            if chaincode_operation_instance.chaincode_names:
                for per_chaincode_name in chaincode_operation_instance.chaincode_names:
                    chaincode_map[per_chaincode_name] = channel_value.get("chaincodes").get(per_chaincode_name)
            for peer_name, _ in peer_map.items():
                org_name = peer_name.split(".", 1)[1]
                org_admin = self.config.client.get_user(org_name, 'Admin')
                for chaincode_name, chaincode_value in chaincode_map.items():
                    response = install_chaincode(
                        client = self.config.client,
                        requestor=org_admin,
                        peer_names=[peer_name],
                        cc_path = chaincode_value.get("chaincodePath", None),
                        cc_name = chaincode_name,
                        cc_version = str(chaincode_value.get("version", None))
                    )
                    logger.info(
                        "Chaincode Operation: Chaincode install response {}".format(response))
        logger.info("Chaincode install end")

    def chaincode_instantiate(self, cc_instantiate_operators):
        """
        instantiate chaincode
        :return:
        """
        self.get_config_instance()
        logger.info("Chaincode instantiate start")
        if not cc_instantiate_operators:
            raise RuntimeError("cc_instantiate_operators must be not None or size is zero.")
        for cc_instantiate_operator in cc_instantiate_operators:
            if cc_instantiate_operator.is_empty():
                raise RuntimeError("cc_instantiate_operator must be not empty.")

        for cc_instantiate_operator in cc_instantiate_operators:
            """ 初始化网络配置根据配置文件"""
            channel_value = self.networkconfig["channels"].get(cc_instantiate_operator.channel_name)
            # 根据传入的chaincode_names以及配置文件来生成chaincode_name_value map
            chaincode_map = dict()
            for per_chaincode_name in cc_instantiate_operator.chaincode_names:
                chaincode_map[per_chaincode_name] = channel_value.get("chaincodes").get(per_chaincode_name)

            if cc_instantiate_operator.peer_names:
                peer_name = cc_instantiate_operator.peer_names[0]
                org_name = peer_name.split(".", 1)[1]
                org_admin = self.config.client.get_user(org_name, 'Admin')
                for chaincode_name, chaincode_value in chaincode_map.items():
                    cc_version = str(chaincode_value.get("version", None))
                    response = self.config.client.chaincode_instantiate(
                        requestor=org_admin,
                        channel_name=cc_instantiate_operator.channel_name,
                        peers=cc_instantiate_operator.peer_names,
                        args=cc_instantiate_operator.args,
                        cc_name=chaincode_name,
                        cc_version=cc_version
                    )
                    if response:
                        logger.info(f"{json.dumps(cc_instantiate_operator.peer_names)} instantiate {chaincode_name}.{cc_version} successfully.")
                    else:
                        logger.info(f"{json.dumps(cc_instantiate_operator.peer_names)} instantiate {chaincode_name}.{cc_version} failed.")
                    logger.info(
                        "Chaincode Operation: Chaincode instantiation response {}".format(response))
        logger.info("Chaincode instantiate end")

    def chaincode_upgrade(self, cc_upgrade_operators):
        """
        upgrade chaincode
        :return:
        """
        self.get_config_instance()
        logger.info("Chaincode upgrade start")
        if not cc_upgrade_operators:
            raise RuntimeError("cc_upgrade_operators must be not None or size is zero.")
        for cc_upgrade_operator in cc_upgrade_operators:
            if cc_upgrade_operator.is_empty():
                raise RuntimeError("cc_upgrade_operator must be not empty.")

        for cc_upgrade_operator in cc_upgrade_operators:
            """ 初始化网络配置根据配置文件"""
            channel_value = self.networkconfig["channels"].get(cc_upgrade_operator.channel_name)
            # 根据传入的chaincode_names以及配置文件来生成chaincode_name_value map
            chaincode_map = dict()
            for per_chaincode_name in cc_upgrade_operator.chaincode_names:
                chaincode_map[per_chaincode_name] = channel_value.get("chaincodes").get(per_chaincode_name)

            if cc_upgrade_operator.peer_names:
                peer_name = cc_upgrade_operator.peer_names[0]
                org_name = peer_name.split(".", 1)[1]
                org_admin = self.config.client.get_user(org_name, 'Admin')
                for chaincode_name, chaincode_value in chaincode_map.items():
                    response = upgrade_chaincode(
                        client=self.config.client,
                        requestor=org_admin,
                        channel_name=cc_upgrade_operator.channel_name,
                        peer_names=cc_upgrade_operator.peer_names,
                        args=cc_upgrade_operator.args,
                        cc_name=chaincode_name,
                        cc_version=str(chaincode_value.get("version", None))
                    )
                    logger.info(
                        "Chaincode Operation: Chaincode upgrade response {}".format(response))
        logger.info("Chaincode upgrade end.")

    def query_chaincode(self, cc_query_operators):
        """
        query chaincodes
        :param requestor:
        :param peers_names:
        :return:
        """
        self.get_config_instance()
        logger.info("Chaincode query start")
        if not cc_query_operators:
            raise RuntimeError("cc_query_operators must be not None or size is zero.")
        for cc_query_operator in cc_query_operators:
            if cc_query_operator.is_empty():
                raise RuntimeError("cc_query_operator must be not empty.")
        # 根据peer_names以及network-config-tls.yaml(default name)来生成peer_map
        for cc_query_operator in cc_query_operators:
            for peer_name in cc_query_operator.peer_names:
                org_name = peer_name.split(".", 1)[1]
                org_admin = self.config.client.get_user(org_name, 'Admin')
                chaincodes = query_chaincode(client=self.config.client,
                                requestor=org_admin,
                                peer_names=[peer_name])

                logger.info(f"{json.dumps(cc_query_operator.peer_names)} query chaincode installed include .")

        logger.info("Chaincode query end")



class ChaincodeInstallOperator(object):
    """
    be used to install chaincode
    """
    def __init__(self, channel_name, peer_names, chaincode_names):
        """
        :param channel_name:
        :param peer_names:
        :param chaincodes:
        """
        self.channel_name = channel_name
        self.peer_names = peer_names
        self.chaincode_names = chaincode_names

    def is_empty(self):
        return not self.channel_name and not self.peer_names and not self.chaincode_names

class ChaincodeInstantiateOperator(object):
    """
    be used to instantiate chaincode
    """
    def __init__(self, channel_name, peer_names, chaincode_names, args = []):
        """
        :param channel_name:
        :param peer_names:
        :param chaincodes:
        :param args: instantiate init args
        """
        self.channel_name = channel_name
        self.peer_names = peer_names
        self.chaincode_names = chaincode_names
        self.args = args

    def is_empty(self):
        return not self.channel_name and not self.peer_names and not self.chaincode_names

class ChaincodeUpgradeOperator(object):
    """
    be used to upgrade chaincode
    """
    def __init__(self, channel_name, peer_names, chaincode_names, args = []):
        """
        :param channel_name:
        :param peer_names:
        :param chaincodes:
        :param args: instantiate init args
        """
        self.channel_name = channel_name
        self.peer_names = peer_names
        self.chaincode_names = chaincode_names
        self.args = args

    def is_empty(self):
        return not self.channel_name and not self.peer_names and not self.chaincode_names

class ChaincodeQueryOperator(object):
    """
    be used to query chaicnode
    """
    def __init__(self, peer_names):
        """

        :param peer_names:
        """
        self.peer_names = peer_names
    def is_empty(self):
        return not self.peer_names
