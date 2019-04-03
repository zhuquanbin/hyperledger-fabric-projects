#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/21 12:10
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import logging
from optparse import OptionParser, OptionGroup

from utils import split_value
from utils.chaincode.operation import ChaincodeInstallOperator, ChaincodeInstantiateOperator, \
    ChaincodeUpgradeOperator
from utils.configuration import Configuration, ExtendConfiguration
from utils.context import DeployContext

logger = logging.getLogger(__name__)


class FabricDeployCommand(object):
    def __init__(self, _parser):
        self.parser = _parser
        self.options, self.args = self.parser.parse_args()
        self.deploy = DeployContext(cfg=Configuration(
            self.options.configPath, self.options.configName, configOutPath=self.options.output),
            virtual_host=self.options.virtual_host
        )

    def compose(self):
        """
        Docker compose 配置文件 及 运行脚本管理
        """

        def wrap(func, modules):
            ms = split_value(modules)
            if ms:
                func(*ms)
            else:
                func("zookeeper", "kafka", "orderer",
                     "orderer-cli", "peer", "peer-cli")

        if self.options.clean_compose or self.options.clean_zip:
            self.deploy.compose_clean(
                self.options.clean_compose, self.options.clean_zip)
        elif self.options.compose_gen:
            self.deploy.compose_gen(virtual_host=self.options.virtual_host)
        elif self.options.compose_zip:
            wrap(self.deploy.compose_zip, self.options.zip_modules)
        elif self.options.compose_show:
            wrap(self.deploy.compose_show, self.options.zip_modules)
        else:
            self.parser.print_help()

    def crypto(self):
        """
        Fabric Network MSP 管理:
            - 显示 Fabric network Org & Peer
            - 显示 Fabric network 已创建的 Org & Peer
            - 创建 Member Ship Provider
            - 扩展 Member Ship Provider
            - 添加 Organization
            - 添加 Peer
        """
        # 显示 Fabric network Org & Peer
        if self.options.list:
            self.deploy.crypto_list()

        # 显示 Fabric network 已创建的 Org & Peer
        elif self.options.show:
            self.deploy.crypto_show()

        # 创建 Member Ship Provider
        elif self.options.gen_crypto:
            self.deploy.crypto_gen()

        # 扩展 Member Ship Provider
        elif self.options.extend_crypto:
            self.deploy.crypto_ext()

        # 添加 Organization 至配置文件
        elif self.options.add_org:
            self.deploy.crypto_add_org()

        # 添加 Peer 至配置文件
        elif self.options.add_peer:
            self.deploy.crypto_add_peer()

        else:
            self.parser.print_help()

    def configtx(self):
        """
        Channel 创世块管理:
            - 显示 Fabric network  Channel 配置
            - 显示 Fabric network 已创建的 Channel
            - 创建 Fabric network Orderer 创世块
            - 配置 Fabric network channel 根据指定 organizations
            - 创建 Fabric network channel 根据指定 channel id
            - 扩展 Fabric network channel 组织成员根据指定 channel id & organizations
        """
        # 列出所有已经生成的创世区块
        if self.options.list:
            self.deploy.config_tx_list()

        # 展示配置文件中的创世块结构
        elif self.options.show:
            self.deploy.config_tx_show()

        # 生成System Orderer创世块
        elif self.options.system:
            self.deploy.config_tx_system()

        # 配置Channel
        elif self.options.cfg_channel:
            self.deploy.config_tx_cfg_channel()

        # 生成Channel
        elif self.options.gen_channel:
            self.deploy.config_tx_gen_channel(id=self.options.channel_id)

        # 扩展Channel
        elif self.options.ext_channel:
            self.deploy.config_tx_ext_channel()

        else:
            self.parser.print_help()

    def scp(self):
        """
        Remote Copy 管理
            - 复制 MSP 根据服务器对应配置
            - 复制 Genesis 至指定服务器
        """

        # 复制模块相应的zip压缩包
        if self.options.scp_zip:
            self.deploy.scp_zip(modules=split_value(self.options.scp_modules),
                                orgs=split_value(self.options.remote_org),
                                hosts=split_value(self.options.remote_hosts))

        # 复制 Genesis 至指定服务器
        elif self.options.scp_channel:
            self.deploy.scp_channel(channel_name=self.options.channel_name,
                                    orgs=split_value(self.options.remote_org),
                                    hosts=split_value(self.options.remote_hosts))

        else:
            self.parser.print_help()

    def install(self):
        """
        Remote Install 管理:
            - 在指定一批服务器上按顺序远程安装指定的某一个服务
        """
        services = split_value(self.options.install_modules)
        if self.options.clean_all:
            flag = input("警告: 操作将清空服务器所有docker container、脚本文件及映射目录 [N/y]:")
            if flag.lower() != "y":
                return
            logger.info("准备清空所有服务 .....")
            self.deploy.clean_all()

        elif services:
            self.deploy.install(services=services,
                                orgs=split_value(self.options.install_org),
                                hosts=split_value(self.options.remote_hosts),
                                reinstall=self.options.reinstall,
                                uninstall=self.options.uninstall,
                                detect=self.options.detect)
        else:
            self.parser.print_help()

    def channel(self):
        """
        通道管理
            - 安装
        :return:
        """
        if self.options.channel_install:
            self.deploy.channel(channel_id=self.options.channel_id,
                                install=True,
                                orgs=split_value(self.options.channel_org),
                                hosts=split_value(self.options.channel_hosts))
        else:
            self.parser.print_help()

    def chaincode(self):
        """
        Chaincode install and instantiate
        """
        # 链码的安装
        if self.options.chaincode_install:
            cc_install_operator = ChaincodeInstallOperator(channel_name=self.options.channel_name,
                                                     peer_names=split_value(self.options.peer_names),
                                                     chaincode_names=split_value(self.options.chaincode_names))
            cc_install_operators = [cc_install_operator]
            self.deploy.chaincode(install=True, cc_install_operators = cc_install_operators)

        # 链码的初始化
        elif self.options.chaincode_instantiate:
            cc_instantiate_operator = ChaincodeInstantiateOperator(channel_name=self.options.channel_name,
                                                     peer_names=self.options.peer_names,
                                                     chaincode_names=split_value(self.options.chaincode_names))
            cc_instantiate_operators = [cc_instantiate_operator]
            self.deploy.chaincode(instantiate=True, cc_instantiate_operators=cc_instantiate_operators)

        # 链码升级
        elif self.options.chaincode_upgrade:
            cc_upgrade_operator = ChaincodeUpgradeOperator(channel_name=self.options.channel_name,
                                                                peer_names=self.options.peer_names,
                                                                chaincode_names=split_value(self.options.chaincode_names))
            cc_upgrade_operators = [cc_upgrade_operator]
            self.deploy.chaincode(upgrade=True, cc_upgrade_operators=cc_upgrade_operators)

        else:
            self.parser.print_help()

    def extend(self):
        extend_config = ExtendConfiguration(
            self.options.configPath, self.options.configExtend)
        extend_config.load_config()
        extend_config.merge_config(
            os.path.join(self.options.configPath, self.options.configName))
        extend_config.merge_file(self.options.configPath, self.options.configName)

    def run(self):
        self.deploy.load_network()
        # docker compose manage
        if self.options.compose:
            self.compose()

        # crypto config manage
        elif self.options.crypto:
            self.crypto()

        # config tx manage
        elif self.options.configtx:
            self.configtx()

        # file scp manage
        elif self.options.scp:
            self.scp()

        # service install manage
        elif self.options.install:
            self.install()

        # channel operate
        elif self.options.channel:
            self.channel()

        # chaincode operate
        elif self.options.chaincode:
            self.chaincode()

        # generate all dependencies for extending fabric network
        elif self.options.extend:
            self.extend()

        else:
            self.parser.print_help()


if __name__ == '__main__':
    parser = OptionParser(conflict_handler="resolve")
    parser.add_option("-p", "--scripts", action="store_true", dest="compose",
                      help="根据Hyperledger Fabric配置文件生成docker-compose 和 scripts")
    parser.add_option("-r", "--crypto", action="store_true", dest="crypto",
                      help="根据Hyperledger Fabric配置文件 crypto-config.yaml 生成 MSP")
    parser.add_option("-t", "--configtx", action="store_true", dest="configtx",
                      help="根据Hyperledger Fabric配置文件 configtx.yaml 生成 Genesis Block")
    parser.add_option("-s", "--scp", action="store_true",
                      dest="scp", help='传输指定服务配置文件至远程服务器')
    parser.add_option("-i", "--install", action="store_true",
                      dest="install", help='远程安装指定服务')
    parser.add_option("-c", "--channel", action="store_true",
                      dest="channel", help='通道操作')
    parser.add_option("--chaincode", action="store_true",
                      dest="chaincode", help='链码的创建和初始化')
    parser.add_option("--extend", action="store_true",
                      dest="extend", help='扩充Fabric网络')

    group = OptionGroup(parser, "Common Options", "通用配置选项")
    group.add_option("-d", "--directory", dest="configPath", default="./configs/",
                     help="Hyperledger Fabric 配置文件所在目录, default: ./configs/")
    group.add_option("--config", dest="configName", default="deployment.yaml",
                     help="Hyperledger Fabric 配置文件名, default: deployment.yaml")
    group.add_option("--configExtend", dest="configExtend", default="extend.yaml",
                     help="Hyperledger Fabric extend 配置文件名, 用于定义需要对现有的Fabric网络进行扩充, default: extend.yaml")
    group.add_option("--output", dest="output", default="./gen",
                     help="配置文件输出结果目录,default: ./gen")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Generate Options", "生成Docker-Compose选项")
    group.add_option("--gen", action="store_true",
                     dest="compose_gen", help="生成所有配置文件")
    group.add_option("--virtual-host", action="store_true", dest="virtual_host",
                     help="服务器是否为虚拟主机, 涉及 docker 网络部署模式")
    group.add_option("--zip", action="store_true",
                     dest="compose_zip", help="根据配置文件中服务器对应角色进行scp相应的zip包")
    group.add_option("--zip-modules", dest="zip_modules",
                     help="指定服务项打包, eg: zookeeper;kafka , default: zookeeper;kafka;orderer;peer;peer-cli")
    group.add_option("--clean-compose", action="store_true",
                     dest="clean_compose", help="删除生成的 .sh 和 .yaml 文件")
    group.add_option("--clean-zip", action="store_true",
                     dest="clean_zip", help="删除生成的 .zip 文件")
    group.add_option("--show", action="store_true", dest="compose_show",
                     help="列出所有 crypto-config & docker compose zip")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Crypto Options", "生成配置文件选项")
    group.add_option("--list-msp", action="store_true",
                     dest="list", help="列出已经创建的MSP")
    group.add_option("--show-msp", action="store_true",
                     dest="show", help="展示所有组织信息")
    group.add_option("--gen-crypto", action="store_true", dest="gen_crypto",
                     help="生成Hyperledger Fabric MSP 根据配置文件")
    group.add_option("--extend-crypto", action="store_true", dest="extend_crypto",
                     help="扩展Hyperledger Fabric MSP 根据配置文件")
    group.add_option("--add-org", action="store_true",
                     dest="add_org", help="添加组织选项")
    group.add_option("--add-peer", action="store_true",
                     dest="add_peer", help="添加节点选项")
    group.add_option("--org", dest="OrgName", help="添加的组织名")
    group.add_option("--peer", dest="PeersNum", type="int", help="添加的节点数")
    parser.add_option_group(group)

    group = OptionGroup(parser, "ConfigTx Options", "生成配置交易选项")
    group.add_option("--list-config-tx", action="store_true",
                     dest="list", help="列出所有已经生成的创世区块")
    group.add_option("--show-config-tx", action="store_true",
                     dest="show", help="展示配置文件中的创世块结构")
    group.add_option("--system", action="store_true",
                     dest="system", help="生成System Orderer创世块")
    group.add_option("--cfg-channel", action="store_true",
                     dest="cfg_channel", help="配置Channel")
    group.add_option("--gen-channel", action="store_true",
                     dest="gen_channel", help="生成Channel")
    group.add_option("--ext-channel", action="store_true",
                     dest="ext_channel", help="扩展Channel")
    group.add_option("--id", dest="channel_id",
                     help="cfg/gen/ext channel 需填写 channel id, 必须为小写")
    group.add_option("--org", dest="organizations",
                     help="cfg/ext Channel 需填写加入channel的组织. eg: org1;org2")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Remote Copy Options", "远程拷贝选项")
    group.add_option("--scp-zip", action="store_true",
                     dest="scp_zip", help="根据配置文件中服务器对应角色进行scp相应的zip包")
    group.add_option("--scp-modules", dest="scp_modules",
                     help="指定服务项拷贝, eg: zookeeper;kafka")
    group.add_option("--scp-channel", action="store_true",
                     dest="scp_channel", help="拷贝指定的channel tx至指定的服务器")
    group.add_option("--channel-name", dest="channel_name",
                     help="指定待拷贝的channel名, eg: dev1")
    group.add_option("--remote-org", dest="remote_org", help="复制到指定组织下的所有节点上, eg: orgEast;"
                                                             "不支持 多个组织名 和 --remote-hosts 一起使用")
    group.add_option("--remote-hosts", dest="remote_hosts",
                     help="远程服务器IP地址, eg: 192.168.0.10;192.168.0.11")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Install Options", "安装服务选项")
    group.add_option("--install-modules", dest="install_modules",
                     help="服务名, eg: docker/zookeeper/kafka/orderer/peer/peer-cli/explorer")
    group.add_option("--install-org", dest="install_org", help="安装组织下的所有节点, 仅支持服务: peer和peer-cli eg: orgeast; "
                                                               "不支持 多个组织名 和 --remote-hosts 一起使用")
    group.add_option("--remote-hosts", dest="remote_hosts",
                     help="远程服务器IP地址, eg: 192.168.0.10;192.168.0.11")
    group.add_option("--uninstall", action="store_true",
                     dest="uninstall", help="卸载指定服务")
    group.add_option("--reinstall", action="store_true",
                     dest="reinstall", help="重新安装指定服务")
    group.add_option("--detect", action="store_true",
                     dest="detect", help="检查服务")
    group.add_option("--clean-all", action="store_true",
                     dest="clean_all", help="清空服务器所有docker container 脚本文件及映射目录")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Channel Options", "通道操作选项")
    group.add_option("--install", action="store_true", dest="channel_install", help="安装channel步骤,"
                                                                                    "不指定org和host则默认安装channel对应的组织所有节点")
    group.add_option("--id", dest="channel_id", help="channel id, 必须为小写")
    group.add_option("--org", dest="channel_org",
                     help="安装组织下的所有节点 eg: orgeast; 不支持 多个组织名 和 --remote-hosts 一起使用")
    group.add_option("--hosts", dest="channel_hosts",
                     help="远程服务器IP地址, eg: 192.168.0.10;192.168.0.11")
    parser.add_option_group(group)

    group = OptionGroup(parser, "Chaincode Options", "链码相关选项")
    group.add_option("--install", action="store_true", dest="chaincode_install", help="安装链码")
    group.add_option("--instantiate", action="store_true", dest="chaincode_instantiate", help="初始化链码")
    group.add_option("--upgrade", action="store_true", dest="chaincode_upgrade", help="链码升级")


    group.add_option("--channel", dest="channel_name",
                     help="指定操作的channel, eg:parcelxdevchannel, 适用类型:链码安装、链码初始化和链码")
    group.add_option("--peernames", dest="peer_names",
                     help="指定链码操作的peernames, eg:peer0.orgEast.parcelx.io;peer1.orgEast.parcelx.io, 适用类型:链码安装、链码初始化和链码升级")
    group.add_option("--chaincodenames", dest="chaincode_names",
                     help="指定操作的chaincodenames, eg:example, 适用类型: 链码安装、链码初始化和链码升级")
    parser.add_option_group(group)

    FabricDeployCommand(parser).run()
