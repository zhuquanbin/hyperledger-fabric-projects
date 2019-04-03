#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/3/8 15:05
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import sys
import json
import logging
from collections import OrderedDict

from utils.chaincode.operation import ChaincodeInstallOperator, ChaincodeInstantiateOperator, \
    ChaincodeUpgradeOperator
from .configuration import Configuration, ExtendConfiguration
from utils import format_org_msp_id, format_org_domain, split_line
from utils.remote import *
from utils.configtx import *
from utils.tool import *

logger = logging.getLogger(__name__)


def check_params(host, ele=None):
    if not isinstance(host, Host):
        raise AttributeError(f'param "host" type must be <Host>!')

    if ele is not None and not isinstance(ele, Element):
        raise AttributeError(f'param "ele" type must be <Element>!')


class BaseContext(object):
    def __init__(self, cfg=None, ext=None, **kwargs):
        """
        :param cfg: Current Configuration
        :param ext: Extend Network Configuration
        :param kwargs:
        """
        if cfg is None or not isinstance(cfg, Configuration):
            raise AttributeError("Network configuration error!")
        if ext and not isinstance(ext, ExtendConfiguration):
            raise AttributeError("Network extend configuration error!")
        self.cfg = cfg
        self.ext = ext
        self._load = False
        self._kwargs = kwargs

    def __check_load(self):
        if not self._load:
            raise SystemError("please invoke Context.load_network function to load fabric network!")

    @property
    def fabric_network(self):
        self.__check_load()
        return self.cfg.fabric_network

    @property
    def assign_manager(self):
        self.__check_load()
        return self.cfg.assign_manager

    @property
    def fabric_release(self):
        self.__check_load()
        return self.cfg.fabric_release

    @property
    def fabric_operator(self):
        self.__check_load()
        return self.cfg.get_fabric_operator()

    @property
    def crypto_configurator(self):
        self.__check_load()
        return self.cfg.crypto_configurator

    @property
    def crypto_handler(self):
        self.__check_load()
        return self.cfg.crypto_handler

    @property
    def configtx_configurator(self):
        self.__check_load()
        return self.cfg.configtx_configurator

    @property
    def configtx_handler(self):
        self.__check_load()
        return self.cfg.configtx_handler

    @property
    def docker_compose_configurator(self):
        self.__check_load()
        return self.cfg.docker_compose_configurator

    def load_network(self):
        """
        1. 加载 deployment.yaml 文件
        2. 读取网络配置， 并生成 configtx.yaml and crypto-config.yaml
        3. 完成配置预处理 证书管理、压缩包、服务器角色配置 等
        :return:
        """
        self._load = True
        self.cfg.load_config()

    def load_extend(self):
        """
        1. 加载 deployment.yaml extend.yaml 文件
        2. 读取网络配置， 内存中合并扩展配置
        :return:
        """
        self._load = True
        self.ext.load_config()
        try:
            # 先排除扩展channel合并， 后续重新 reload
            updated_cfg = self.ext.merge_config(self.cfg.config_filepath, exclude_extend_channel=True)
        except AttributeError as e:
            logger.error(e)
            sys.exit(1)
        self.cfg.load_config(updated_cfg)

    def need_extend_cert(self):
        """
        判断是否加入新节点或组织
        :return:
        """
        return True if self.ext.add_peers or self.ext.add_orgs \
            else False

    def new_hosts(self):
        """
        new hosts
        :return:
        """
        return [i for i in self.ext.hosts]

    def new_peers(self):
        """
        new peers
        :return:
        """
        peers = OrderedDict()
        for org in self.ext.add_peers:
            peers[format_org_msp_id(org)] = [i for i in self.ext.add_peers[org]]
        return peers

    def new_organizations(self):
        """
        new orgs
        :return:
        """
        return [
            format_org_msp_id(o) for o in self.ext.add_orgs
        ]

    def new_channels(self):
        """
        new channels
        :return:
            list [(channel_id, consortium_name)]
        """
        return [
            (c, self.ext.add_channels[c]["consortium"]) for c in self.ext.add_channels
        ]

    def new_extend_channels(self):
        """
        new extend info
        :return:
        """
        extend_channels = OrderedDict()
        for c in self.ext.extend_channels:
            extend_channels[c] = [
                format_org_msp_id(o) for o in self.ext.extend_channels[c].get("orgs", [])
            ]
        return extend_channels

    def need_extend_explorer(self):
        """
        need extend explorer ?
        :return:
        """
        return True if self.ext.extend_explorer else False

    def merge_yaml(self):
        """
        合并配置 yaml 文件
        :return:
        """
        # reload
        self.ext.merge_config(self.cfg.config_filepath)
        # merge file
        self.ext.merge_file(self.cfg.cfg_path, self.cfg.filename)

    def gen_go_sdk_yaml(self, org):
        """
        生成 go sdk
        :param org:
        :return:
        """
        self.cfg.gen_sdk_config(org)

    def set_exec_status(self, **kwargs):
        """
        记录执行状态， 物理写入
        :param kwargs:
        :return:
        """
        # create a new file and open it for writing if it not exists else read and write
        # mode = "x" if not os.path.exists(self.exec_status_json_file) else "r"
        template = {}
        if os.path.exists(self.cfg.exec_status_json_file):
            with open(self.cfg.exec_status_json_file, "r") as fp:
                template = json.load(fp)

        # update key value
        for key in kwargs:
            sub_keys = key.split("_")
            sub_dict = template
            # find key
            for sub_key in sub_keys[:-1]:
                if sub_key not in sub_dict:
                    sub_dict[sub_key] = {}
                sub_dict = sub_dict[sub_key]
            # set key/value
            sub_dict[sub_keys[-1]] = kwargs[key]

        with open(self.cfg.exec_status_json_file, "w") as fp:
            json.dump(template, fp, indent=4)

    def get_exec_status(self, key):
        """
        读取状态, 物理读取
        :param key:
        :return:
        """
        if not os.path.exists(self.cfg.exec_status_json_file):
            return None

        # read config
        with open(self.cfg.exec_status_json_file, "r") as fp:
            template = json.load(fp)
        # split key
        sub_keys = key.split("_")
        sub_dict = template
        # find key
        for sub_key in sub_keys[:-1]:
            if sub_key not in sub_dict:
                return None
            sub_dict = sub_dict[sub_key]
        # get key value
        return sub_dict[sub_keys[-1]]


class DeployContext(BaseContext):

    def __init__(self, **kwargs):
        super(DeployContext, self).__init__(**kwargs)

    # docker compose functions
    def compose_gen(self, virtual_host=False):
        self.docker_compose_configurator.generate_all(virtual_host)

    def compose_zip(self, *modules):
        """
        服务配置文件打成zip压缩包
        :param modules:
        :return:
        """
        self.assign_manager.zip(*modules)

    def compose_show(self, *modules):
        """
        展示压缩包文件
        :param modules:
        :return:
        """
        for module in modules:
            self.assign_manager.show_zip(module)

    def compose_clean(self, compose, zip):
        """
        清空 compose 文件 或者 zip 压缩包
        :param compose:
        :param zip:
        :return:
        """
        if compose:
            self.docker_compose_configurator.clean_output()
        if zip:
            self.assign_manager.clean_package()

    # crypto functions
    def crypto_list(self, *args, **kwargs):
        raise NotImplementedError()

    def crypto_show(self, *args, **kwargs):
        raise NotImplementedError()

    def crypto_gen(self, *args, **kwargs):
        """
        证书生成
        :param args:
        :param kwargs:
        :return:
        """
        generated = self.get_exec_status("crypto-config_generated")
        if not generated:
            self.crypto_handler.gen()
            self.set_exec_status(**{"crypto-config_generated": True})
        else:
            print("crypto-config had generated!")

    def crypto_ext(self, *args, **kwargs):
        self.crypto_handler.extend()

    def crypto_add_org(self, *args, **kwargs):
        raise NotImplementedError()

    def crypto_add_peer(self, *args, **kwargs):
        raise NotImplementedError()

    # configtx functions
    def config_tx_list(self, *args, **kwargs):
        raise NotImplementedError()

    def config_tx_show(self, *args, **kwargs):
        raise NotImplementedError()

    def config_tx_system(self, *args, **kwargs):
        """
        生成System Orderer创世块
        :param args:
        :param kwargs:
        :return:
        """
        self.configtx_handler.gen_orderer_genesis()

    def config_tx_cfg_channel(self, *args, **kwargs):
        raise NotImplementedError()

    def config_tx_gen_channel(self, *args, **kwargs):
        """
        创建 channel transaction
        :param args:
        :param kwargs:
            id : channel name id
        :return:
        """
        channel_id = kwargs.get("id", None)
        if not channel_id:
            logger.error(f"channel id must been provided!")

        self.configtx_handler.gen_channel_genesis(
            self.configtx_configurator.get_channel(channel_id))

    def config_tx_ext_consortium(self, consortium):
        """
        修改 System 创世区块配置，添加新联盟
        :param consortium:
        :return:
        """
        channel = self.configtx_configurator.system_channel_id
        # 随机的节点
        one_node = self.assign_manager.first_orderer_cli
        logger.info(
            f"start to update system channel<{channel}>, add channel<{consortium}> configure.")
        prefix_path = f"{channel}/{consortium}"

        # step 0 gen new system genesis
        logger.info(f"step 0 start to generate system.json.")
        new_system_pb = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "system.pb")
        new_system_json = new_system_pb.replace(".pb", ".json")
        new_system_channel = self.configtx_configurator.orderer_genesis.copy(
            "system.pb",
            os.path.dirname(new_system_pb))
        ret = self.configtx_handler.gen_orderer_genesis(new_system_channel)
        if 0 != ret.returncode:
            logger.info(f"stdout: {ret.stdout}\nstderr: {ret.stderr}")
            return
        self.configtx_handler.proto_decode(self.configtx_configurator.relative_path(new_system_pb),
                                           self.configtx_configurator.relative_path(new_system_json))
        logger.info(f"step 0 finished!")

        rc = SshHost.getConnection(self.assign_manager.get_host(one_node))
        # step 1
        channel_config_pb = self.__config_tx_ext_fetch_cfg(
            one_node, prefix_path, channel,
            tls_ca=self.assign_manager.orderer_cli_tls_ca
        )

        # step 2 ~ 3
        channel_part_config_json = self.__config_tx_ext_decode_and_extract(
            prefix_path, channel_config_pb
        )

        # step 4
        modified_config_json = self.__config_tx_ext_modify_config(
            prefix_path, channel_part_config_json, new_system_json,
            consortium=consortium
        )

        # step 5 ~ 7
        consortium_updated_json = self.__config_tx_ext_compute_config(
            prefix_path, channel, channel_part_config_json,
            modified_config_json, consortium
        )

        # step 8 ~ 9
        consortium_update_in_envelope_pb = self.__config_tx_ext_envelope_config(
            prefix_path, channel, consortium_updated_json, consortium
        )

        # step 10、对 orgN_update_in_envelope.pb进行签名， 并进行下载
        logger.info(f"step 10 start to remote docker cli exec sign & update pb file!")
        envelope_pb_filename = os.path.basename(consortium_update_in_envelope_pb)
        sign_cmd, one_node_path = self.configtx_handler.remote_sign_channel_pb_cmd(envelope_pb_filename, one_node)
        update_cmd, _ = self.configtx_handler.remote_update_channel_pb_cmd(
            envelope_pb_filename, one_node, channel,
            self.assign_manager.first_orderer_service, self.assign_manager.orderer_cli_tls_ca)
        rc.upload(consortium_update_in_envelope_pb, "/tmp")
        rc.sudo(f"mv /tmp/{envelope_pb_filename} {one_node_path}")
        rc.sudo(sign_cmd)
        rc.sudo(update_cmd)

    def config_tx_ext_channel(self, **kwargs):
        """
        向现有的channel中添加新的组织， 包含的步骤：
            0、 获取新增组织必要配置证书生成 orgN.json
            1、 获取 channel 最新的配置文件 channel_config.pb
            2、 将 channel_config.pb 文件转换为 channel_config.json
            3、 从 channel_config.json 中提取必要的字段配置信息生成 config.json
            4、 将 orgN.json 添加到 config.json 中 生成新的 modified_config.json
            5、 将 config.json 转换为 config.pb, modified_config.json 转换为 modified_config.pb
            6、 对比 config.pb 和 modified_config.pb 之间的差异生成 orgN_updated.pb
            7、 将 orgN_updated.pb 转换为 orgN_updated.json
            8、 对 orgN_updated.json 添加头信息并包装之前剥离出来的信息生成 orgN_update_in_envelope.json
            9、 将 orgN_update_in_envelope.json 转换为 orgN_update_in_envelope.pb
            10、对 orgN_update_in_envelope.pb进行签名， 并进行提交

        :param kwargs:
            channel:
                需要添加组织的channel id
            org:
                待添加的组织名
        :return:
        """
        #
        channel = kwargs["channel"]
        # 随机的节点
        one_node = self.configtx_configurator.get_peer_from_channel(channel)
        to_extend_org = format_org_msp_id(kwargs["org"])
        logger.info(
            f"start to extend channel<{channel}>, add org<{to_extend_org}>.")
        prefix_path = f"{channel}/{to_extend_org}"

        # step 0
        logger.info(f"step 0 start to generate {to_extend_org}.json.")
        to_extend_org_json = self.configtx_configurator.get_config_tx_org_path(
            f"{to_extend_org}.json")
        if not os.path.exists(to_extend_org_json):
            self.configtx_handler.print_org(to_extend_org)
        logger.info(f"step 0 finished!")

        # 获取远程 docker cli 命令执行实例
        rc = SshHost.getConnection(self.assign_manager.get_host(one_node))

        # step 1
        channel_config_pb = self.__config_tx_ext_fetch_cfg(
            one_node, prefix_path, channel,
            tls_ca=self.assign_manager.peer_cli_tls_ca
        )

        # step 2 ~ 3
        channel_part_config_json = self.__config_tx_ext_decode_and_extract(
            prefix_path, channel_config_pb
        )

        # step 4
        modified_config_json = self.__config_tx_ext_modify_config(
            prefix_path, channel_part_config_json, to_extend_org_json,
            organization=to_extend_org, channel=channel
        )

        # step 5 ~ 7
        extend_org_updated_json = self.__config_tx_ext_compute_config(
            prefix_path, channel, channel_part_config_json,
            modified_config_json, to_extend_org
        )

        # step 8 ~ 9
        org_update_in_envelope_pb = self.__config_tx_ext_envelope_config(
            prefix_path, channel, extend_org_updated_json, to_extend_org
        )

        # step 10、对 orgN_update_in_envelope.pb进行签名， 并进行下载
        logger.info(f"step 10 start to remote docker cli exec sign pb file!")
        envelope_pb_filename = os.path.basename(org_update_in_envelope_pb)
        sign_cmd, one_node_path = self.configtx_handler.remote_sign_channel_pb_cmd(envelope_pb_filename, one_node)
        rc.upload(org_update_in_envelope_pb, "/tmp")
        rc.sudo(f"mv /tmp/{envelope_pb_filename} {one_node_path}")
        rc.sudo(sign_cmd)

        # step 11、下载签名过的pb文件, 并在 channel 所在的其他组织cli上进行 channel update
        envelope_signed_pb_filepath = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path,
            f"{format_org_domain(to_extend_org)}_signed_in_envelope.pb"
        )
        envelope_signed_pb_filename = os.path.basename(envelope_signed_pb_filepath)

        rc.download(f"{one_node_path}{envelope_pb_filename}", envelope_signed_pb_filepath)
        # 其他组织进行 channel update 操作
        for node in self.configtx_configurator.get_peer_from_channel(channel, first=False):
            update_cmd, remote_path = self.configtx_handler.remote_update_channel_pb_cmd(
                envelope_signed_pb_filename, node, channel,
                self.assign_manager.first_orderer_service,
                self.assign_manager.peer_cli_tls_ca)
            oc = SshHost.getConnection(self.assign_manager.get_host(node))
            oc.upload(envelope_signed_pb_filepath, "/tmp")
            oc.sudo(f"mv /tmp/{envelope_signed_pb_filename} {remote_path}")
            oc.sudo(update_cmd)
            return

    def __config_tx_ext_fetch_cfg(self, node, prefix_path, channel, orderer_service=None, tls_ca=None):
        """
        step 1:
            获取 channel 配置文件

        :param node:  cli 节点
        :param prefix_path:  文件生成目录前缀
        :param channel:
        :param orderer_service:
        :param tls_ca:
        :return:
        """
        # step 1
        logger.info(f"step 1 start to fetch remote channel config file!")
        # 获取远程 docker cli 命令执行实例
        rc = SshHost.getConnection(self.assign_manager.get_host(node))
        # 本地保存路径
        channel_config_pb = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "config_block.pb")
        # 获取 fetch 执行命令
        cmd, remote_pb = self.configtx_handler.remote_fetch_config_pb_cmd(
            node,
            channel,
            orderer_service if orderer_service else self.assign_manager.first_orderer_service,
            tls_ca if tls_ca else self.assign_manager.orderer_cli_tls_ca
        )
        rc.sudo(cmd, )
        rc.download(remote_pb, channel_config_pb)
        rc.sudo(f"rm -f {remote_pb}")
        logger.info(f"step 1 new <{channel_config_pb}> finished!")

        return channel_config_pb

    def __config_tx_ext_decode_and_extract(self, prefix_path, channel_config_pb):
        """
        step 2: decode channel pb 文件 -> json
        step 3: 从 json 文件中提取 channel 相关的配置
        :param prefix_path:
        :param channel_config_pb:
        :return:
        """
        # step 2
        channel_config_json = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "config_block.json")
        logger.info(f"step 2 start to proto decode config file <{channel_config_pb}>")
        ret = self.configtx_handler.proto_decode(
            self.configtx_configurator.relative_path(channel_config_pb),
            self.configtx_configurator.relative_path(channel_config_json)
        )
        if 0 != ret.returncode:
            logger.error(f"stdout: {ret.stdout}\nstderr: {ret.stderr}")
            sys.exit(1)
        logger.info(f"step 2 new channel config json <{channel_config_json}> finished!")

        # step 3
        logger.info(f"step 3 start to extract json config file <{channel_config_json}>")
        channel_part_config_json = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "config.json")
        with open(channel_config_json, "r") as fp:
            channel_config_dict = json.load(fp)
            with open(channel_part_config_json, "w") as nfp:
                json.dump(channel_config_dict["data"]["data"][0]
                          ["payload"]["data"]["config"], nfp, indent=4)
        logger.info(f"step 3 new config json file <{channel_part_config_json}> finished!")

        return channel_part_config_json

    def __config_tx_ext_modify_config(self, prefix_path, config_json, to_ext_json, **kwargs):
        """
        step 4:
            - 读取 新增的组织 或 联盟 配置
            - 修改 配置文件 加入 新增的成员
        :param prefix_path:
        :param config_json:  提取的配置文件
        :param to_ext_json:  待扩展的配置文件
        :param kwargs:
            consortium:
                添加新的联盟时 填写 与 configtx.yaml 中 联盟的Profile名称
            channel:
                扩展 channel 时 需填写
            organization:
                扩展 channel 时 需填写
        :return:
        """
        # step 4
        channel = kwargs.get("channel", None)
        consortium = kwargs.get("consortium", None)
        organization = kwargs.get("organization", None)
        with open(config_json, "r") as fp:
            part_config = json.load(fp)
        with open(to_ext_json, "r") as fp:
            to_ext_data = json.load(fp)

        # 向系统配置中添加新联盟配置
        if consortium:
            logger.info(f"step 4 start to add Consortium<{consortium}> json to config file.")
            groups = part_config["channel_group"]["groups"]["Consortiums"]["groups"]
            to_ext_cfg = to_ext_data["data"]["data"][0]["payload"]["data"]["config"]
            new_consortium = to_ext_cfg["channel_group"]["groups"]["Consortiums"]["groups"][consortium]
            if consortium in groups:
                logger.error(f"system genesis contains channel profile <{consortium}> !")
                sys.exit(1)
            groups[consortium] = new_consortium
        # 向已经存在的channel中添加新组织
        elif organization:
            logger.info(f"step 4 start to add Organization<{organization}> json to config file.")
            groups = part_config["channel_group"]["groups"]["Application"]["groups"]
            if organization in groups:
                logger.error(f"channel<{channel}> contains organization {organization}")
                sys.exit(1)
            groups[organization] = to_ext_data
        else:
            logger.error("Channel extend param error at step 4!")
            sys.exit(1)

        modified_config_json = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "modified_config.json")
        with open(modified_config_json, "w") as fp:
            json.dump(part_config, fp, indent=4)
        logger.info(f"step 4 new modified config file <{modified_config_json}> finished!")

        return modified_config_json

    def __config_tx_ext_compute_config(self, prefix_path, channel,
                                       channel_part_config_json, modified_config_json, part):
        """
        step 5:
            将 config.json 转换为 config.pb, modified_config.json 转换为 modified_config.pb
        step 6:
            对比 config.pb 和 modified_config.pb 之间的差异生成 part_updated.pb
        step 7:
            将 part_updated.pb 转换为 part_updated.json

        :param prefix_path:
        :param channel:
        :param channel_part_config_json:
        :param modified_config_json:
        :param part:
        :return:
        """
        # step 5、 将 config.json 转换为 config.pb, modified_config.json 转换为 modified_config.pb
        logger.info(f"step 5 start to proto encode config.json and modified_config.json.")
        channel_part_config_pb = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "config.pb")
        self.configtx_handler.proto_encode(self.configtx_configurator.relative_path(channel_part_config_json),
                                           self.configtx_configurator.relative_path(channel_part_config_pb))
        logger.info(f"step 5 new pb file <{channel_part_config_pb}> finished!")
        modified_config_pb = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path, "modified_config.pb")
        self.configtx_handler.proto_encode(self.configtx_configurator.relative_path(modified_config_json),
                                           self.configtx_configurator.relative_path(modified_config_pb))
        logger.info(f"step 5 new pb file <{modified_config_pb}> finished!")

        # step 6、 对比 config.pb 和 modified_config.pb 之间的差异生成 consortium_updated.pb
        logger.info(f"step 6 start to compare config.pb with modified_config.pb .")
        part_updated_pb = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path,
            f"{part}_updated.pb"
        )
        self.configtx_handler.compute_update(
            channel,
            self.configtx_configurator.relative_path(channel_part_config_pb),
            self.configtx_configurator.relative_path(modified_config_pb),
            self.configtx_configurator.relative_path(part_updated_pb)
        )
        logger.info(f"step 6 new pb file <{part_updated_pb}> finished!")

        # step 7、 将 orgN_updated.pb 转换为 orgN_updated.json
        logger.info(f"step 7 start to proto decode config file <{part_updated_pb}>")
        part_updated_json = part_updated_pb.replace(".pb", ".json")
        self.configtx_handler.proto_decode(
            self.configtx_configurator.relative_path(part_updated_pb),
            self.configtx_configurator.relative_path(part_updated_json),
            decode_type="common.ConfigUpdate")
        logger.info(f"step 7 new json file <{part_updated_json}> finished!")

        return part_updated_json

    def __config_tx_ext_envelope_config(self, prefix_path, channel, updated_json, part):
        """
        step 8:
            对 part_updated.json 添加头信息并包装之前剥离出来的信息生成 part_update_in_envelope.json
        step 9:
            将 part_update_in_envelope.json 转换为 part_update_in_envelope.pb

        :param prefix_path:
        :param channel:
        :param updated_json:
        :param part:
        :return:
            part_update_in_envelope.pb
        """
        # step 8、 对 orgN_updated.json 添加头信息并包装之前剥离出来的信息生成 orgN_update_in_envelope.json
        logger.info(f"step 8 start to wrap in an envelope message ...")
        with open(updated_json, "r") as fp:
            updated_dict = json.load(fp)
        part_update_in_envelope_dict = {
            "payload": {
                "header": {
                    # https://github.com/hyperledger/fabric/blob/eca1b14b7e3453a5d32296af79cc7bad10c7673b/protos/common/common.proto#L47
                    # CONFIG_UPDATE = 2;             // Used for transactions which update the channel config
                    "channel_header": {"channel_id": channel, "type": 2}
                },
                "data": {"config_update": updated_dict}}
        }
        part_update_in_envelope_json = self.configtx_configurator.get_config_tx_channel_path(
            prefix_path,
            f"{part}_updated_in_envelope.json"
        )
        with open(part_update_in_envelope_json, "w") as fp:
            json.dump(part_update_in_envelope_dict, fp, indent=4)
        logger.info(f"step 8 new json file <{part_update_in_envelope_json}> finished!")

        # step 9、将 orgN_update_in_envelope.json 转换为 orgN_update_in_envelope.pb
        logger.info(f"step 9 start to proto encode file <{part_update_in_envelope_json}> ...")
        part_update_in_envelope_pb = part_update_in_envelope_json.replace(".json", ".pb")
        self.configtx_handler.proto_encode(
            self.configtx_configurator.relative_path(part_update_in_envelope_json),
            self.configtx_configurator.relative_path(part_update_in_envelope_pb),
            encode_type="common.Envelope")
        logger.info(f"step 9 new pb file <{part_update_in_envelope_pb}> finished!")

        return part_update_in_envelope_pb

    # scp functions
    def scp_zip(self, *args, **kwargs):
        """
        服务配置文件远程拷贝
        :param args:
            None
        :param kwargs:
            modules:    服务类型
            hosts:      服务主机， 若空则服务对应的所有机器拷贝，若存在拷贝至服务指定的服务器
        :return:
        """

        def _copy(ele=None, host=None, **kwargs):
            """
            copy 操作
            :param ele:     object <Element>
            :param host:    object <Host>
            :return:
            """
            check_params(host, ele)
            rc = SshHost.getConnection(host)
            rc.upload(ele.absolute_zip_path,
                      self.assign_manager.remote_tmp_path)
            rc.run(" && ".join(ele.remote_unzip_bashes))

        self.assign_manager.handle_func(_copy, *args, **kwargs)

    def scp_channel(self, *args, **kwargs):
        """
        复制 channel 创世块至远程服务器
        :param args: None
        :param kwargs:
            channel_name:
            orgs:
            hosts:
        :return:
        """
        channel_name = kwargs.get("channel_name", None)
        orgs = kwargs.get("orgs", [])
        hosts = kwargs.get("hosts", [])
        channel_genesis_path = self.configtx_configurator.get_channel(
            channel_name).filepath
        if not os.path.exists(channel_genesis_path):
            raise FileNotFoundError(f"{channel_genesis_path} not found!")

        def wrap_upload_file(_host, _src, _dest):
            _ssh = SshHost.getConnection(_host)
            _ssh.run(f"mkdir -p {_dest}")
            _ssh.upload(_src, "/tmp")
            _ssh.run(f"mv /tmp/{os.path.basename(_src)} {_dest}")

        if orgs and isinstance(orgs, (list, tuple)):
            # for org in orgs:
            for role_domain in self.assign_manager.get_org_elements("peer-cli", orgs):
                wrap_upload_file(self.assign_manager.get_host(role_domain),
                                 channel_genesis_path,
                                 self.assign_manager.remote_bash_path)

        elif hosts and isinstance(hosts, (list, tuple)):
            for host in hosts:
                wrap_upload_file(self.assign_manager.get_host(host),
                                 channel_genesis_path,
                                 self.assign_manager.remote_bash_path)
        else:
            pass

    # install functions
    def install(self, services=None, hosts=None, **kwargs):
        """
        Install the services on given hosts sequentially
        :param services: The type of host to install, such as kafka, zookeeper, peer etc.:
        :param hosts: The list of host ips;
        :param kwargs: optional extra parameters as key-value paris:
        :return:
        """
        _services = AssignManage.To_Array(services, "services")
        AssignManage.Check_Module(*_services)
        for _module in _services:
            if _module == "docker":
                _module_func = self.__install_docker
            else:
                _module_func = self.__install_fabric
            self.assign_manager.handle_func(_module_func, _module, hosts, **kwargs)

    def __install_docker(self, host=None, **kwargs):
        if not isinstance(host, Host):
            logger.info(f'param "host" type must be <Host>!')
            return

        detect = kwargs.get("detect", False)
        uninstall = kwargs.get("uninstall", False)
        if detect:
            try:
                SshHost.getConnection(host).run(
                    "docker -v && docker-compose -v")
            except RuntimeError as e:
                logger.error(e)
        elif uninstall:
            logger.warning(f"Don't support to uninstall docker in {host}")
        else:
            logger.info(f"Start to install docker in {host}")
            Docker().install(SshHost.getConnection(host), **kwargs)
            logger.info(f"Install docker finished!")
            logger.warning(f"*" * 45)

    def __install_fabric(self, host=None, ele=None, **kwargs):
        """
        安装Fabric相关组件（安装，卸载，重新安装）
        :param host: <Host>
        :param ele:  <Element>
        :param kwargs
            uninstall: 卸载, 默认False
            reinstall: 重新安装, 默认False
        :return:
        """
        check_params(host, ele)
        uninstall = kwargs.get("uninstall", False)
        restart = kwargs.get("restart", False)
        reinstall = kwargs.get("reinstall", False)
        detect = kwargs.get("detect", False)

        rc = SshHost.getConnection(host)
        try:
            # 检测
            if detect:
                logger.info(f"Start to detect {ele.role} in {host}.")
                rc.run(" && ".join(ele.detect_bashes))
            # 重启
            elif restart:
                logger.info(f"Start to restart {ele.role} in {host}.")
                rc.run(" && ".join(ele.restart_bashes))
            # 卸载
            elif uninstall:
                logger.info(f"Start to uninstall {ele.role} in {host}.")
                rc.run(" && ".join(ele.uninstall_bashes))
                logger.info(f"Uninstall module finished!")
            # 重装
            elif reinstall:
                logger.warning(
                    f"Don't support to reinstall {ele.role} in {host}, because of the installation sequence!")
            # 安装 & 检测
            else:
                logger.info(f"Start to install {ele.role} in {host}.")
                rc.run(" && ".join(ele.install_bashes))
                logger.info(f"Start to detect {ele.role} in {host}.")
                rc.run(" && ".join(ele.detect_bashes))

        except RuntimeError as e:
            if "No such container" in str(e):
                logger.warning(
                    f"Docker container: {ele.docker_container_name} stopped!")
            else:
                raise e

        split_line(logger)

    def channel(self, channel_id=None, hosts=None, **kwargs):
        """
        通道操作
        :param channel_id: channel id
        :param hosts: 安装服务器
        :param kwargs:
            install: 安装
            orgs: 安装组织, 默认全部安装
        :return:
        """
        if not channel_id:
            logger.error("channel id must be provided!")
            return

        # 尝试获取 Custom Channel
        custom_channel = self.configtx_configurator.get_channel(channel_id)
        kwargs["custom_channel"] = custom_channel

        if kwargs.get("install", False):
            # 判断指定安装的 org 是否属于 channel 配置中的orgs, 否则退出
            to_install_orgs = set(
                map(lambda o: format_org_domain(o), kwargs.get("orgs", [])))
            if to_install_orgs:
                diff_orgs = to_install_orgs.difference(
                    custom_channel.get_org())
                if diff_orgs:
                    logger.error(f"The organizations<{diff_orgs}> does not belong to "
                                 f"the channel<{custom_channel.genesis_channelID}>")
                    return
            else:
                # 没有指定则安装 channel 下对应的所有 orgs
                kwargs["orgs"] = list(custom_channel.get_org())
            self.assign_manager.handle_func(self.__channel_install, "peer-cli", hosts=hosts, **kwargs)

        elif kwargs.get("extend", False):
            extend_orgname = kwargs.get("extend_orgname", None)
            if extend_orgname is None:
                logger.error("param 'extend_orgname' must been provided!")
                return
            # 将 org cert 更新至 channel
            self.config_tx_ext_channel(channel=custom_channel.genesis_channelID, org=extend_orgname)
            # 添加 org 对应的 peer 加入 channel
            self.assign_manager.handle_func(self.__channel_extend, modules="peer-cli", orgs=[extend_orgname], **kwargs)
            # 添加 org 到 channel 中
            custom_channel.add_org(extend_orgname)
        elif kwargs.get("join", False):
            self.assign_manager.handle_func(self.__channel_join, modules="peer-cli", hosts=hosts, **kwargs)
        else:
            pass

    def __channel_install(self, host=None, ele=None, **config):
        """
        install channel
        :param host:
        :param ele:
        :param config:
            custom_channel: CustomChannel Object

        :return:
        """

        custom_channel = config.get("custom_channel", None)
        if not isinstance(custom_channel, CustomChannel):
            raise AttributeError("custom_channel type must be <CustomChannel>!")

        logger.info(f"Channel<{custom_channel.genesis_channelID}> will to install on {ele.role_domain} {host}")
        rc = SshHost.getConnection(host)
        tx_block_filename = f"{custom_channel.genesis_channelID}.block"
        tx_block_filepath = os.path.join(self.configtx_configurator.configtx_genesis, tx_block_filename)

        # 判断本地是否有 channel.block , 没有则远程生成并下载至本地
        if not os.path.exists(tx_block_filepath):
            tx_to_block_cmd = f"peer channel create -o {self.assign_manager.first_orderer_service} -c %s -f %s " \
                f"--tls --cafile {self.assign_manager.peer_cli_tls_ca}"
            # 上传 channel.tx 至 /tmp 目录下
            rc.upload(custom_channel.filepath, "/tmp")
            # 移动 channel.tx 到 peer-cli 挂载目录下
            rc.run(f'sudo cp /tmp/{custom_channel.genesis_name} {ele.docker_container_volume}')
            # 根据 channel.tx 创建 channel.block
            rc.run(f'sudo docker exec {ele.docker_container_name} bash -c "cd /root/cli-data/ && '
                   f'{tx_to_block_cmd % (custom_channel.genesis_channelID, custom_channel.genesis_name)}"',
                   throw=False)
            # 下载 channel.block 至本地
            remote_path = f"{ele.docker_container_volume}/{tx_block_filename}"
            # 复制到tmp下 并修改权限
            rc.run(f"sudo cp {remote_path} /tmp/{tx_block_filename} && "
                   f"sudo chown {host.username}:{host.username} /tmp/{tx_block_filename}")
            # download
            rc.download(f"/tmp/{tx_block_filename}",
                        tx_block_filepath,
                        throw=False)

        else:
            # channel.block 上传至 peer-cli /root/cli-data 目录下
            rc.upload(tx_block_filepath, "/tmp/")
            rc.run(f"sudo mv /tmp/{tx_block_filename} {ele.docker_container_volume}")

        # 将节点加入channel
        rc.run(f'sudo docker exec {ele.docker_container_name} bash -c "cd /root/cli-data/ && '
               f'peer channel join -b {tx_block_filename}"', throw=False)

        split_line(logger)

    def __channel_extend(self, host=None, ele=None, **config):
        """
        extend channel, fetch channel block & join commands:
            peer channel fetch 0 mychannel.block -o orderer.example.com:7050 -c $CHANNEL_NAME --tls --cafile $ORDERER_CA
            peer channel join -b mychannel.block

        :param host:
        :param ele:
        :param config:
            custom_channel: CustomChannel Object

        :return:
        """
        custom_channel = config.get("custom_channel", None)
        if not isinstance(custom_channel, CustomChannel):
            raise AttributeError("custom_channel type must be <CustomChannel>!")

        logger.info(f"Channel<{custom_channel.genesis_channelID}> will to install on {ele.role_domain} {host}")

        rc = SshHost.getConnection(host)
        tx_block_filename = f"{custom_channel.genesis_channelID}.block"

        extend_cmds = [
            "cd /root/cli-data/",
            f"peer channel fetch 0 {tx_block_filename} -o {self.assign_manager.first_orderer_service} "
            f"-c {custom_channel.genesis_channelID} --tls --cafile {self.assign_manager.peer_cli_tls_ca}",
            f"peer channel join -b {tx_block_filename}"
        ]
        rc.run(f'sudo docker exec {ele.docker_container_name} bash -c "{" && ".join(extend_cmds)}"')

    def __channel_join(self, host=None, ele=None, **config):
        return self.__channel_extend(host=host, ele=ele, **config)

    def chaincode(self, cc_install_operators=None, cc_instantiate_operators=None, cc_upgrade_operators=None, **kwargs):
        """
        安装/实例化 链码
        注意配置文件的路径
        :return:
        """
        self.cfg.load_sdk_config()
        if kwargs.get("install", False):
            self.fabric_operator.chaincode_install(cc_install_operators)
        elif kwargs.get("instantiate", False):
            self.fabric_operator.chaincode_instantiate(cc_instantiate_operators)
        elif kwargs.get("upgrade", False):
            self.fabric_operator.chaincode_upgrade(cc_upgrade_operators)
        else:
            pass

    def first_deploy_chaincode(self):
        """
        one key deploy use this method to process deploy chaincode first.
        :return:
        """
        cc_install_operators = []
        cc_instantiate_operators = []
        for channel_name, channel_value in self.fabric_network['channels'].items():
            peers_names = []
            for org_name in channel_value['orgs']:
                org_value = self.fabric_network['organization'].get(org_name)
                for index in range(len(org_value.peers)):
                    peers_names.append(f"peer{index}.{org_name}.{self.cfg.domain}")
            chaincode_names = []
            for per_chaincode_name, _ in channel_value.get("chaincodes").items():
                chaincode_names.append(per_chaincode_name)
            cc_install_operator = ChaincodeInstallOperator(channel_name, peers_names, chaincode_names)
            cc_install_operators.append(cc_install_operator)
            cc_instantiate_operator = ChaincodeInstantiateOperator(channel_name, peers_names, chaincode_names)
            cc_instantiate_operators.append(cc_instantiate_operator)

        self.chaincode(install=True, cc_install_operators=cc_install_operators)
        self.chaincode(instantiate=True, cc_instantiate_operators=cc_instantiate_operators)

    def extend_deploy_chaincode(self):
        """
        get add org, add peer and add channel from self.ext
        and invoke fabric_operator.chaincode_install and chaincode_instantiate
        note: for extend channels, the chaincode should be upgrade. so follow code increase chaincode version by 0.1
        :return:
        """
        # get all operation channel from add_channel and extend_channel

        extend_channels = [channel_name for channel_name in self.ext.extend_channels.keys()]
        add_channels = [channel_name for channel_name in self.ext.add_channels.keys()]

        for channel_name, channel_value in self.fabric_network['channels'].items():
            peers_names = []
            for org_name in self.configtx_configurator.get_channel(channel_name).get_org():
                peers_names.extend([pd for _, pd in self.fabric_network["peer"][org_name].items()])
            chaincode_names = [per_chaincode_name for per_chaincode_name, _ in channel_value.get("chaincodes").items()]

            if channel_name in add_channels:
                cc_install_wait_instantiate_operators = []
                cc_instantiate_operators = []
                cc_install_wait_instantiate_operator = ChaincodeInstallOperator(channel_name, peers_names,
                                                                                 chaincode_names)
                cc_install_wait_instantiate_operators.append(cc_install_wait_instantiate_operator)
                cc_instantiate_operator = ChaincodeInstantiateOperator(channel_name, peers_names, chaincode_names)
                cc_instantiate_operators.append(cc_instantiate_operator)
                self.chaincode(install=True, cc_install_operators=cc_install_wait_instantiate_operators)
                self.chaincode(instantiate=True, cc_instantiate_operators=cc_instantiate_operators)
            elif channel_name in extend_channels:
                cc_install_wait_upgrade_operators = []
                cc_upgrade_operators = []
                cc_install_wait_upgrade_operator = ChaincodeInstallOperator(channel_name, peers_names, chaincode_names)
                cc_install_wait_upgrade_operators.append(cc_install_wait_upgrade_operator)
                cc_upgrade_operator = ChaincodeUpgradeOperator(channel_name, peers_names, chaincode_names)
                cc_upgrade_operators.append(cc_upgrade_operator)
                self.chaincode(install=True, cc_install_operators=cc_install_wait_upgrade_operators)
                self.chaincode(upgrade=True, cc_upgrade_operators=cc_upgrade_operators)

    def onekey_deploy(self):
        """
        一键安装 by deployment.yaml
        :return:
        """
        # 0. 安装docker
        self.install(services="docker")

        # 1. 生成证书
        self.crypto_gen()

        # 2. 生成 docker-compose
        self.compose_gen(virtual_host=self._kwargs.get("virtual_host", False))

        # 3. 打包 & 拷贝
        to_do_modules = ("zookeeper", "kafka", "orderer",
                         "orderer-cli", "peer", "peer-cli", "explorer")
        self.compose_zip(*to_do_modules)
        self.scp_zip(modules=to_do_modules)

        # 3.1 生成 orderer system genesis
        self.config_tx_system()
        # 3.2 拷贝 orderer system genesis
        self.scp_channel(
            channel_name=self.configtx_configurator.system_channel_id, orgs=["orderer"])

        # 4. 顺序安装 zookeeper & kafka & orderer & orderer-cli & peer & peer-cli 安装
        self.install(services=to_do_modules[:-1])

        # 5. channel 安装
        channels = self.fabric_network["channels"]
        if channels and isinstance(channels, dict):
            for channel_id in channels:
                self.config_tx_gen_channel(id=channel_id)
                self.channel(channel_id=channel_id, install=True, )
        else:
            logger.warning("Not found any channel!")

        self.install(services=to_do_modules[-1:])

        # 6. chain-code install and instantiate
        self.first_deploy_chaincode()

    def onekey_extend(self):
        """
        一键扩展 by extend.yaml， 执行顺序:
            0. 新增主机 安装 docker
            1. extend cert
            2. gen compose & package
            3. new peers install
            4. new organizations install
            5. new channels install
            6. extend channels
            7. channel install
        :return:
        """
        logger.info("start to extend current fabric-network!")
        # 0. 新增主机 安装 docker
        new_hosts = self.new_hosts()
        if new_hosts:
            self.install(services="docker", hosts=new_hosts)

        # 1. extend cert
        if self.need_extend_cert():
            self.crypto_ext()

        new_peers = self.new_peers()
        new_organizations = self.new_organizations()
        # 2. gen docker-compose & package
        if new_peers or new_organizations or self.need_extend_explorer():
            self.compose_gen(virtual_host=self._kwargs.get("virtual_host", False))
            self.compose_zip("peer", "peer-cli", "explorer")

        # 3. new peers install
        for org, peers in new_peers.items():
            if peers:
                # scp;   note: 不能在指定hosts时指定多个 modules
                self.scp_zip(modules=["peer"], orgs=[org], hosts=peers)
                self.scp_zip(modules=["peer-cli"], orgs=[org], hosts=peers)
                # install; note: 不能在指定hosts时指定多个 modules
                self.install(services=["peer"], orgs=[org], hosts=peers)
                self.install(services=["peer-cli"], orgs=[org], hosts=peers)
                for channel_id in self.configtx_configurator.get_org_channel_id(org):
                    self.channel(join=True, hosts=peers, channel_id=channel_id, orgs=[org])

        # 4. new organizations install
        for org in new_organizations:
            # scp
            self.scp_zip(modules=("peer", "peer-cli"), orgs=[org])
            # install
            self.install(services=("peer", "peer-cli"), orgs=[org])

        # 5. new channels install
        for channel_id, consortium in self.new_channels():
            self.config_tx_ext_consortium(consortium)
            self.config_tx_gen_channel(id=channel_id)
            self.channel(install=True, channel_id=channel_id)
            split_line(logger)

        # 6. extend channels
        for channel_id, orgs in self.new_extend_channels().items():
            for org in orgs:
                self.channel(extend=True, channel_id=channel_id, extend_orgname=org)
                split_line(logger)

        # 7. extend explorer
        if self.need_extend_explorer():
            _m = ["explorer"]
            self.scp_zip(modules=_m)
            self.install(services=_m, restart=True)

        # 8. exist channel install chaincode
        self.extend_deploy_chaincode()
        split_line(logger)

    def clean_all(self):
        """
        一键清除 services 和 本地配置
        :return:
        """
        self.assign_manager.clean_env()
        self.crypto_configurator.clean_output()
        self.configtx_configurator.clean_output()
        self.docker_compose_configurator.clean_output()
        self.assign_manager.clean_package()
        self.fabric_operator.clean_network_config()
        if os.path.exists(self.cfg.exec_status_json_file):
            os.remove(self.cfg.exec_status_json_file)
