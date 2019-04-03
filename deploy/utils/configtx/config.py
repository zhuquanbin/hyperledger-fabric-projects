#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 15:30
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import shutil
from utils import format_org_domain, format_org_msp_id
from pathlib import Path
from .gen import ConfigTxGenerator
from collections import OrderedDict
from enum import IntEnum


class ChannelType(IntEnum):
    GENESIS = 0,
    CHANNEL = 1


class CustomChannel(object):
    """Custom Channel Configure"""

    def __init__(self, genesis, profile, channel_id, out="./", role=ChannelType.CHANNEL):
        self.genesis_name = genesis
        self.genesis_profile = profile
        self.genesis_channelID = channel_id
        self.organizations = OrderedDict()
        self.output = out
        self.role = role

    def add_org(self, *org):
        """
        Daemon, to be developed
        :param org:
        :return:
        """
        for o in org:
            self.organizations.update({format_org_domain(o): None})
        return self

    def get_org(self):
        """
        Get channel org list
        :return:
        """
        return self.organizations.keys()

    @property
    def genesis_channel_id(self):
        """channel id must be lower"""
        return self.genesis_channelID.lower()

    @property
    def filepath(self):
        return os.path.join(self.output, self.genesis_name)

    def copy(self, genesis=None, out=None):
        return CustomChannel(
            genesis if genesis else self.genesis_name,
            self.genesis_profile,
            self.genesis_channelID,
            out if out else self.output,
            self.role
        )


class ConfigTxConfigure(object):
    def __init__(self, output):
        self.domain = None
        # 工具类运行目录
        # crypto and configtx 必须在同一目录下, 存在依赖关系, 该目录下存放 configtx.yaml
        self.output = os.path.join(output, "fabric-config")
        # 设置 创世块配置文件目录 configtx/genesis
        self.configtx_genesis = os.path.join(self.output, "configtx/genesis")
        # 设置 涉及通道配置文件目录 configtx/channels/<channel_name>
        self.configtx_channels = os.path.join(self.output, "configtx/channels")
        # 设置 涉及组织证书json目录  configtx/orgs/
        self.configtx_orgs = os.path.join(self.output, "configtx/orgs")
        # mkdir -p /path/to/config
        if not os.path.exists(self.configtx_genesis):
            os.makedirs(self.configtx_genesis)
        if not os.path.exists(self.configtx_channels):
            os.makedirs(self.configtx_channels)
        if not os.path.exists(self.configtx_orgs):
            os.makedirs(self.configtx_orgs)

        self.fabric_network = None
        # 配置文件中的所有组织
        self.organizations = OrderedDict()
        # channel 配置
        self.channels = OrderedDict()
        # Example
        # configure for generate orderer genesis block
        self.system_channel_id = "orderersystemchannel"

    def load_network(self, **kwargs):
        self.domain = kwargs.get("domain", "parcelx.io")
        self.fabric_network = kwargs.get("network", None)
        if not self.fabric_network:
            raise ValueError("Fabric network configuration must be provided")
        self.__init_config_file()

    def __init_config_file(self):
        """
        Init Config File Example
        """
        generator = ConfigTxGenerator(self.filepath, **self.fabric_network)
        generator.run()

        # 加载创世块
        self.channels[self.system_channel_id] = CustomChannel(
            "genesis.block",
            self.fabric_network.get("genesis", "ParcelXOrgsOrdererGenesis"),
            self.system_channel_id,
            self.configtx_genesis,
            ChannelType.GENESIS)

        # load channels map orgs
        channels = self.fabric_network.get("channels", None)
        if not channels:
            raise ValueError(f"channels configuration not found")

        for channel_id, channel in channels.items():
            orgs = channel.get("orgs", None)
            if not orgs:
                raise ValueError(f"Orgs node not found in channel config: {channel}")

            channel_id_lower = channel_id.lower()
            if channel_id_lower in self.channels:
                raise AttributeError(f"channel name: {channel_id} conflict!")
            # 记录 组织 对应的 channel
            for org in orgs:
                org_id = format_org_msp_id(org)
                if org_id not in self.organizations:
                    self.organizations[org_id] = set()
                self.organizations[org_id].add(channel_id_lower)
            # 记录 channel 对应的配置
            self.channels[channel_id_lower] = CustomChannel(f"{channel_id_lower}.tx",
                                                            channel["profile"],
                                                            channel_id_lower,
                                                            self.configtx_genesis).add_org(*orgs)

    def get_peer_from_channel(self, channel_name, first=True):
        """
        随机获取一个peer从channel所在的组织中
        :param channel_name:
        :param first:
            True  返回 第一个组织 对应的 cli 节点
            False 返回 除第一个之外组织 对应的 cli 节点
        :return:
        """
        organizations = list(self.get_channel(channel_name).get_org())
        if len(organizations) < 2:
            raise AttributeError(f"The channel<{channel_name}> only had one organization!")

        if first:
            return f"peer-cli0.{organizations[0]}.{self.domain}"
        else:
            return [f"peer-cli0.{org}.{self.domain}" for org in organizations[1:]]

    def get_config_tx_genesis_path(self, filename):
        """
        返回genesis的路径
        :param filename:
        :return:
        """
        return os.path.join(self.configtx_genesis, filename)

    def get_config_tx_org_path(self, filename):
        """
        返回输出org证书的路径
        :param filename:
        :return:
        """
        return os.path.join(self.configtx_orgs, filename)

    def get_config_tx_channel_path(self, channel, filename):
        """
        返回涉及channel相关配置文件的的路径
        :param channel:
        :param filename:
        :return:
        """
        channel_path = os.path.join(self.configtx_channels, channel)
        if not os.path.exists(channel_path):
            os.makedirs(channel_path)
        return os.path.join(channel_path, filename)

    def relative_path(self, absolute):
        """
        工具类所运行的工作目录涉及的配置文件相对路径截取
        :param absolute: 相对程序运行的绝对路径
        :return: 相对工具类运行的相对路径
        """
        return Path(absolute).relative_to(self.output).as_posix()

    @property
    def filepath(self):
        return os.path.join(self.output, "configtx.yaml")

    @property
    def orderer_genesis(self):
        """
        为 Orderer 创建创世块， 大多数情况下是固定配置
        :return:
        """
        return self.get_channel(self.system_channel_id)

    def get_org_channel_id(self, org):
        """
        获取 组织对应的 channel id
        :param org:
        :return:
        """
        return self.organizations.get(format_org_msp_id(org), set())

    def get_channel(self, channel_name):
        """
        获取 channel
        :param channel_name: channel name id
        :return: <object CustomChannel>
        """
        channel_name_lower = channel_name.lower()
        if channel_name_lower in self.channels:
            return self.channels[channel_name_lower]
        else:
            raise NotImplementedError(f"Channel: {channel_name} non-support, please modify the channel configuration!")

    def clean_output(self):
        """
        清空输出目录
        :return:
        """
        if os.path.exists(self.output):
            shutil.rmtree(self.output)
