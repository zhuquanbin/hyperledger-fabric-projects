#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/21 12:10
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

import os
import sys
import json
import logging
from collections import Counter, OrderedDict
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from utils.chaincode.operation import Operation
from utils import format_org_msp_id, format_org_domain, convert_project_abs_path
from utils.compose import *
from utils.remote import *
from utils.crypto import *
from utils.configtx import *
from utils.tool import *

logger = logging.getLogger(__name__)


class Organization(object):
    def __init__(self, name, domain, peers, country='CN', province='Shanghai', usersCount=1):
        """
        初始化一个组织
        :param name: Organization name
        :param domain: Organization domain
        :param peers: The peers
        :param country: The country
        :param province: The province
        :param usersCount: The count of fabric network users
        :return:
        """
        self.name = name
        self.peers = peers
        self.domain = domain
        self.country = country
        self.province = province
        self.usersCount = usersCount


class Configuration(object):
    def __init__(self, path="./configs", filename="deployment.yaml", **kwargs):
        self.cfg_path = path
        self.filename = filename
        # config file
        if self.filename:
            self.config_filepath = os.path.join(self.cfg_path, self.filename)
        self._kwargs = kwargs

        # config out put directory
        self.config_output = kwargs.get("configOutPath", "./gen")
        # config json,  record script execution status
        self.exec_status_json_file = os.path.join(self.config_output, "_data.json")

        self.yaml = YAML()
        self.yaml.indent(sequence=4, offset=2)

        # fabric network configure
        self.fabric_network = {}
        # fabric sdk operator
        self._sdk_operator = None

    def __init_config(self, config=None):
        """ 加载配置"""
        if config:
            data = config
        else:
            with open(self.config_filepath, 'r') as fp:
                data = self.yaml.load(fp)

        # fabric crypto configurator
        self.crypto_configurator = CryptoConfigure(self.config_output)
        # fabric configtx configurator
        self.configtx_configurator = ConfigTxConfigure(self.config_output)
        # docker compose configurator
        self.docker_compose_configurator = DockerComposeGen(self.config_output)
        # configure assign manager
        self.assign_manager = AssignManage(self.config_output)
        self.assign_manager.crypto_output = self.crypto_configurator.output
        self.assign_manager.configtx_output = self.configtx_configurator.output
        self.assign_manager.compose_output = self.docker_compose_configurator.config_output

        # read yaml configure
        self.__init_network(data)

        # fabric binaries release
        self.fabric_release = FabricRelease(self.fabric_network["version"].get("peer", "1.4.0"), auto=True)
        # fabric crypto load fabric network
        self.crypto_configurator.load_network(
            domain=self.domain, network=self.fabric_network)
        # fabric config tx load fabric network
        self.configtx_configurator.load_network(
            domain=self.domain, network=self.fabric_network)
        # docker compose load fabric network
        self.docker_compose_configurator.load_network(
            domain=self.domain, network=self.fabric_network)
        # fabric crypto operator
        self.crypto_handler = CryptoHandler(
            self.fabric_release, self.crypto_configurator)
        # fabric configtx operator
        self.configtx_handler = ConfigTxHandler(
            self.fabric_release, self.configtx_configurator)

    def __init_network(self, data):
        """ 初始化网络配置根据配置文件"""
        # read host config
        hosts_config = data.get("hosts", None)
        if not hosts_config:
            raise AttributeError("hosts config must be provided!")
        host_credential = hosts_config.get("credential", {})
        _default_user = host_credential.get("user", None)
        _default_password = host_credential.get("password", None)
        for index, item in hosts_config["pool"].items():
            self.assign_manager.add_host(
                Host(item["ip"],
                     id=index,
                     username=item.get("user", _default_user),
                     password=item.get("password", _default_password),
                     key=item.get("key", None))
            )

        # read fabric network config
        fabric_config = data.get("fabric", None)
        if not fabric_config:
            raise AttributeError("fabric network config must be provided!")

        # load host image versions
        version = fabric_config.get('version', None)
        if not version:
            raise AttributeError("fabric network version must be provided!")

        # load orderer org configuration, including
        ordererOrg_config = fabric_config.get("ordererOrg", None)
        if not ordererOrg_config:
            raise AttributeError(
                "fabric network orderer org must be provided!")

        self.ordererOrgName = ordererOrg_config.get("name", "ordererOrg")
        self.domain = ordererOrg_config.get("domain", None)
        self.assign_manager.domain = self.domain
        if not self.domain:
            raise AttributeError("orderer org domain must be provided!")

        zookeepers = ordererOrg_config.get('zookeepers', None)
        if not zookeepers:
            raise AttributeError("orderer org zookeepers must be provided!")

        kafkas = ordererOrg_config.get('kafkas', None)
        if not kafkas:
            raise AttributeError("orderer org kafkas must be provided!")

        orderers = ordererOrg_config.get('orderers', None)
        if not orderers:
            raise AttributeError("orderer org orderers must be provided!")

        for idx, hostId in enumerate(zookeepers):
            host = self.assign_manager.get_host(hostId, throw=True)
            self.assign_manager.add_item(
                idx + 1, None, Role.ZOOKEEPER, self.domain, host.ip)

        for idx, hostId in enumerate(kafkas):
            host = self.assign_manager.get_host(hostId, throw=True)
            self.assign_manager.add_item(
                idx, None, Role.KAFKA, self.domain, host.ip)

        for idx, hostId in enumerate(orderers):
            host = self.assign_manager.get_host(hostId, throw=True)
            self.assign_manager.add_item(
                idx, "OrdererOrg", Role.ORDERER, self.domain, host.ip)
            self.assign_manager.add_item(
                idx, "OrdererOrg", Role.ORDERER_CLI, self.domain, host.ip)

        peerOrgs = fabric_config.get("peerOrgs", None)
        if not peerOrgs:
            raise AttributeError("fabric network peer orgs must be provided!")

        orgs = {}
        for org_name, org_config in peerOrgs.items():
            org_name = format_org_domain(org_name)
            org_domain = org_config.get("domain", f"{org_name}.{self.domain}")
            org_peers = org_config.get("peers", None)
            if not org_peers:
                raise AttributeError("peer org peers must be provided!")
            peers = [self.assign_manager.get_host(
                host_id, throw=True) for host_id in org_peers]
            org = Organization(org_name, org_domain, peers,
                               country=org_config.get('country', 'CN'),
                               province=org_config.get('province', 'Shanghai'),
                               usersCount=org_config.get('usersCount', 1))
            orgs[org_name] = org

        for _, org in orgs.items():
            for idx, host in enumerate(org.peers):
                self.assign_manager.add_item(
                    idx, org.name, Role.PEER, org.domain, host.ip)
                self.assign_manager.add_item(
                    idx, org.name, Role.PEER_CLI, org.domain, host.ip)

        self.fabric_network.update(self.assign_manager.network)
        if "hosts" in self.fabric_network:
            with open(os.path.join(self.config_output, "domain.cfg"), "w") as fp:
                split_hosts = [l.split(":") for l in self.fabric_network["hosts"]]
                max_length = max([len(h[1]) for h in split_hosts]) + 2
                fp.write("\n".join(
                    f"{d[1].ljust(max_length,' ')} {d[0]}" for d in split_hosts
                ))

        channels = fabric_config.get("channels", None)
        if not channels:
            raise AttributeError("fabric network channels must be provided!")

        explorer = fabric_config.get("explorer", None)
        if not explorer:
            logger.warning("fabric-explorer is not provided!")
        else:
            host = self.assign_manager.get_host(explorer["peer"], throw=True)
            self.assign_manager.add_item("", None, Role.EXPLORER, self.domain, host.ip)

        self.fabric_network["version"] = version
        self.fabric_network["orderer_org"] = ordererOrg_config
        self.fabric_network["genesis"] = fabric_config.get(
            "genesis", "ParcelXOrgsOrdererGenesis")
        self.fabric_network["organization"] = orgs
        self.fabric_network["channels"] = channels
        self.fabric_network["explorer"] = explorer
        self.fabric_network["host_credential"] = host_credential

    def __init_sdk_config(self):
        """
        根据deployment.yaml来生成fabric-sdk-py所需要的network-config-tls.yaml
        :return:
        """
        network_config_tls = {}
        network_config_tls['name'] = 'fabric-dev-network'
        network_config_tls['description'] = 'fabric dev network config tls file'
        network_config_tls['version'] = '0.1'
        network_config_tls['client'] = json.loads(
            """
            {
                "organization": "Org1",
                "credentialStore": {
                    "path": "/tmp/hfc-kvs",
                    "cryptoStore": {
                        "path": "/tmp/hfc-cvs"
                    },
                    "wallet": "wallet-name"
                }
            }
            """
        )
        """
        orderers_url_domain   orderers的url 列表
        eg:
        - orderer0.parcelx.io
        - orderer1.parcelx.io
        - orderer2.parcelx.io
        """
        net_config_tls_channels = {}
        for channel_name, channel_value in self.fabric_network["channels"].items():
            net_config_tls_channel_section = {}
            net_config_tls_channel_section['createChannelTX'] = ''
            orderers_url_domain = [v for _, v in self.fabric_network["orderer"].items()]
            net_config_tls_channel_section['orderers'] = orderers_url_domain
            peers = {}
            for org_name in self.configtx_configurator.get_channel(channel_name).get_org():
                for _, pd in self.fabric_network["peer"][org_name].items():
                    peers[pd] = {
                        "endorsingPeer": "true",
                        "chaincodeQuery": "true",
                        "ledgerQuery": "true",
                        "eventSource": "true"
                    }
            net_config_tls_channel_section['peers'] = peers
            net_config_tls_channel_section['chaincodes'] = channel_value.get('chaincodes', None)
            net_config_tls_channels[channel_name] = net_config_tls_channel_section
        network_config_tls['channels'] = net_config_tls_channels
        """
        eg:
        orderer.parcelx.io:
        mspid: OrdererMSP
        orderers:
        - orderer0.parcelx.io
        - orderer1.parcelx.io
        - orderer2.parcelx.io
        certificateAuthorities:
        # - ca-orderer
        users:
          Admin:
            cert: ../fixtures/e2e_cli/crypto-config/ordererOrganizations/parcelx.io/users/Admin@parcelx.io/msp/signcerts/Admin@parcelx.io-cert.pem
            private_key: ../fixtures/e2e_cli/crypto-config/ordererOrganizations/parcelx.io/users/Admin@parcelx.io/msp/keystore/ca4119674289f39a960f438fe9b70b7143f207c08f7997875812704e0647fc94_sk
        """

        organizations = {}
        orderer_org = {}
        orderer_org['mspid'] = format_org_msp_id(self.ordererOrgName)
        orderer_org['orderers'] = [v for _, v in self.fabric_network["orderer"].items()]
        orderer_users = {}
        orderer_users_admin = self.__orderer_users_admin_msp()
        orderer_users['Admin'] = orderer_users_admin
        orderer_org['users'] = orderer_users
        organizations[f"{self.ordererOrgName}.{self.domain}"] = orderer_org
        for per_org_name, per_org_value in self.fabric_network["organization"].items():
            org_section = {}
            org_section['mspid'] = format_org_msp_id(per_org_value.name)
            org_section['peers'] = [f"peer{index}.{per_org_value.name}.{self.domain}" for index in
                                    range(len(per_org_value.peers))]
            org_section['users'] = self.__org_users_msp(per_org_value.name)
            organizations[f"{per_org_value.name}.{self.domain}"] = org_section
        network_config_tls['organizations'] = organizations
        """
        eg:
        orderers:
            orderer0.parcelx.io:
            url: 192.168.2.211:7050
            # these are standard properties defined by the gRPC library
            # they will be passed in as-is to gRPC client constructor
            grpcOptions:
              grpc.ssl_target_name_override: orderer0.parcelx.io
              grpc-max-send-message-length: 15

            # src/test/fixture/sdkintegration/e2e-2Orgs/v1.3/crypto-config/ordererOrganizations/parcelx.io/tlsca
            tlsCACerts:
              path: ../fixtures/e2e_cli/crypto-config/ordererOrganizations/parcelx.io/orderers/orderer0.parcelx.io/msp/tlscacerts/tlsca.parcelx.io-cert.pem
        """
        orderers_section = {}
        for index, per_orderer_hostid in enumerate(self.fabric_network['orderer_org'].get('orderers', None)):
            orderer_section = {}
            orderer_section['url'] = self.assign_manager.get_host(per_orderer_hostid, throw=True).ip + ":7050"
            orderer_section['grpcOptions'] = {
                'grpc.ssl_target_name_override': f"orderer{index}.{self.domain}",
                'grpc-max-send-message-length': 15
            }
            orderer_section['tlsCACerts'] = self.__orderer_tls(f"orderer{index}")
            orderers_section[f"orderer{index}.{self.domain}"] = orderer_section
        network_config_tls['orderers'] = orderers_section

        peers_section = {}
        for _, per_org_value in self.fabric_network["organization"].items():
            for index, org_per_peer in enumerate(per_org_value.peers):
                peer_section = {}
                peer_section['url'] = f"{org_per_peer.ip}:7051"
                peer_section['eventUrl'] = f"{org_per_peer.ip}:7053"
                peer_section['grpcOptions'] = {
                    'grpc.ssl_target_name_override': f"peer{index}.{per_org_value.name}.{self.domain}",
                    'grpc-max-send-message-length': 15
                }
                peer_section.update(self.__peer_msp(per_org_value.name, index))
                peers_section[f"peer{index}.{per_org_value.name}.{self.domain}"] = peer_section

        network_config_tls['peers'] = peers_section
        # create network-config folder
        network_config_tls_dirpath = convert_project_abs_path(os.path.join(self.config_output, 'network-config'))
        if not os.path.exists(network_config_tls_dirpath):
            os.mkdir(network_config_tls_dirpath)
        with open(os.path.join(network_config_tls_dirpath, 'network-config-tls.yaml'), 'w') as fw:
            self.yaml.dump(network_config_tls, stream=fw)

    def __orderer_users_admin_msp(self):
        admin_msp = {}
        admin_msp['cert'] = convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                                  f"crypto-config/ordererOrganizations/{self.domain}/users/Admin@{self.domain}/msp/signcerts/Admin@{self.domain}-cert.pem"))

        orderer_admin_private_key = convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                                          f"crypto-config/ordererOrganizations/{self.domain}/users/Admin@{self.domain}/msp/keystore"))
        for _, _, file_names in os.walk(orderer_admin_private_key):
            orderer_admin_private_key = os.path.join(orderer_admin_private_key, file_names[0])
            break
        admin_msp['private_key'] = orderer_admin_private_key
        return admin_msp

    def __org_users_msp(self, org_name):
        """

        :param org_name:
        :return:
        """
        users_msp = {}
        users_path = convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                           f"crypto-config/peerOrganizations/{org_name}.{self.domain}/users"))
        users_list = []

        for _, sub_dirs, file_names in os.walk(users_path):
            for sub_dir in sub_dirs:
                users_list.append(str.split(sub_dir, '@')[0])
            break

        for user_name in users_list:
            user_msp = {}
            user_msp['cert'] = convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                                     f"crypto-config/peerOrganizations/{org_name}.{self.domain}/users/{user_name}@{org_name}.{self.domain}/msp/signcerts/{user_name}@{org_name}.{self.domain}-cert.pem"))
            org_user_private_key = convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                                         f"crypto-config/peerOrganizations/{org_name}.{self.domain}/users/{user_name}@{org_name}.{self.domain}/msp/keystore"))
            for _, _, file_names in os.walk(org_user_private_key):
                org_user_private_key = os.path.join(org_user_private_key, file_names[0])
                break
            user_msp['private_key'] = org_user_private_key
            users_msp[user_name] = user_msp
        return users_msp

    def __orderer_tls(self, orderer_name):
        return {
            'path': convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                          f"crypto-config/ordererOrganizations/{self.domain}/orderers/{orderer_name}.{self.domain}/msp/tlscacerts/tlsca.{self.domain}-cert.pem"))
        }

    def __peer_msp(self, org_name, peer_index):
        peer_msp = {}
        peer_msp['tlsCACerts'] = {
            'path': convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                          f"crypto-config/peerOrganizations/{org_name}.{self.domain}/peers/peer{peer_index}.{org_name}.{self.domain}/msp/tlscacerts/tlsca.{org_name}.{self.domain}-cert.pem"))
        }
        peer_msp['clientKey'] = {
            'path': convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                          f"crypto-config/peerOrganizations/{org_name}.{self.domain}/peers/peer{peer_index}.{org_name}.{self.domain}/tls/server.key"))
        }
        peer_msp['clientCert'] = {
            'path': convert_project_abs_path(os.path.join(self.assign_manager.crypto_output,
                                                          f"crypto-config/peerOrganizations/{org_name}.{self.domain}/peers/peer{peer_index}.{org_name}.{self.domain}/tls/server.crt"))
        }
        return peer_msp

    def load_config(self, config=None):
        """
            1. 初始化网络配置
            2. 生成SDK使用的配置文件
        :return:
        """
        self.__init_config(config=config)

    def load_sdk_config(self):
        self.__init_sdk_config()

    def get_fabric_operator(self):
        """
            1. 获取Fabric SDK 操作实例
        :return:
        """
        if not self._sdk_operator:
            self._sdk_operator = Operation(os.path.join(self.config_output, './network-config'))
        return self._sdk_operator

    def gen_sdk_config(self, org_name):
        """
        生成 go SDK client 对应的配置文件
        :param org_name:
        :return:
        """
        org = format_org_domain(org_name)
        if org not in self.fabric_network["peer"]:
            raise AttributeError(f"The organization<{org}> don't exist!")

        related_orgs = {org}
        channel_orgs = OrderedDict()
        for channel_id in self.fabric_network["channels"]:
            channel_obj = self.configtx_configurator.get_channel(channel_id)
            if org in channel_obj.get_org():
                related_orgs.update(channel_obj.get_org())
                channel_orgs[channel_obj.genesis_channel_id] = channel_obj.get_org()

        if not channel_orgs:
            raise AttributeError(f"The organization<{org}> does not belong to any channel!")

        from utils.compose.template import GO_SDK_CONFIG_TEMPLATE
        with open(GO_SDK_CONFIG_TEMPLATE, 'r') as fp:
            sdk_cfg = self.yaml.load(fp)

        # client section modify
        client = sdk_cfg["client"]
        client["organization"] = org
        client["cryptoconfig"]["path"] = "${CRYPTO_CONFIG_PATH}/"
        tls_certs = client["tlsCerts"]
        tls_certs["systemCertPool"] = False
        client_tls_key = "${CRYPTO_CONFIG_PATH}" + \
                         "/peerOrganizations/{0}/users/User1@{0}/tls/client.key".format(f"{org}.{self.domain}")
        tls_certs["client"]["key"]["path"] = client_tls_key
        tls_certs["client"]["cert"]["path"] = client_tls_key.replace(".key", ".crt")

        # organizations section modify
        organizations = CommentedMap()
        organizations["ordererOrg"] = CommentedMap(
            mspID="OrdererMSP",
            cryptoPath="ordererOrganizations/{0}/users/{1}@{0}/msp".format(self.domain, "{username}")
        )
        for _org in related_orgs:
            organizations[_org] = CommentedMap(
                mspID=format_org_msp_id(_org),
                cryptoPath="peerOrganizations/{2}.{0}/users/{1}@{2}.{0}/msp".format(self.domain, "{username}", _org),
                peers=CommentedSeq(
                    v for v in self.fabric_network["peer"][_org].values()
                )
            )
        sdk_cfg["organizations"] = organizations

        # orderers section modify
        orderers = sdk_cfg["orderers"]
        for _ip, _d in self.fabric_network["orderer"].items():
            orderers[_d] = CommentedMap(
                url=f"{_ip}:7050",
                grpcOptions=CommentedMap(),
                tlsCACerts=CommentedMap(
                    path="${CRYPTO_CONFIG_PATH}" +
                         "/ordererOrganizations/{0}/tlsca/tlsca.{0}-cert.pem".format(self.domain)
                )
            )
            orderers[_d]["grpcOptions"]["ssl-target-name-override"] = _d

        # peers section modify
        peers = sdk_cfg["peers"]
        for _org in related_orgs:
            for _ip, _d in self.fabric_network["peer"][_org].items():
                peers[_d] = CommentedMap(
                    url=f"{_ip}:7051",
                    grpcOptions=CommentedMap(),
                    tlsCACerts=CommentedMap(
                        path="${CRYPTO_CONFIG_PATH}" +
                             "/peerOrganizations/{0}.{1}/tlsca/tlsca.{0}.{1}-cert.pem".format(_org, self.domain)
                    )
                )
                peers[_d]["grpcOptions"]["ssl-target-name-override"] = _d

        # channels section modify
        channels = sdk_cfg["channels"]
        for _channel_id in channel_orgs:
            channels[_channel_id] = CommentedMap(
                peers=CommentedMap()
            )
            for _ip, _d in self.fabric_network["peer"][org].items():
                channels[_channel_id]["peers"][_d] = CommentedMap(
                    endorsingPeer=True,
                    chaincodeQuery=True,
                    ledgerQuery=True,
                    eventSource=True
                )

        sdk_config_path = os.path.join(self.config_output, "go-sdk-config")
        if not os.path.exists(sdk_config_path):
            os.makedirs(sdk_config_path)
        yaml_filepath = os.path.join(sdk_config_path, f"fabric-{org}-config.yaml")
        with open(yaml_filepath, "w") as fp:
            self.yaml.dump(sdk_cfg, fp)

        logger.info("crypto-config-path: %s/crypto-config",
                    os.path.abspath(self.configtx_configurator.output).replace("\\", "/"))
        logger.info("network-yaml-path : %s", os.path.abspath(yaml_filepath).replace("\\", "/"))


def check_intersection(first, second, msg):
    """
    检查交集
    :param first:
    :param second:
    :param msg:
    :return:
    """
    if first is None or second is None:
        return

    _c_member = set([p.lower() for p in first])
    _n_member = set([p.lower() for p in second])
    _i_member = _c_member.intersection(_n_member)
    if _i_member:
        raise AttributeError(msg % _i_member)


def check_repetition(array, msg):
    """
    检查重复的元素
    :param array:
    :param msg:
    :return:
    """
    if array is None:
        return

    if not isinstance(array, (list, tuple)):
        raise AttributeError("function <check_repetition> param type(array) must be list or tuple!")
    for k, v in Counter(array).items():
        if v > 1:
            raise AttributeError(msg % k)


def check_contains(src, dest, msg):
    """
    检查是否包含
    :param src:  源数据
    :param dest:  检查对象
    :param msg:
    :return:
    """
    _s_member = set([p.lower() for p in src])
    _d_member = set([p.lower() for p in dest])
    _diff = _d_member.difference(_s_member)
    if _diff:
        raise AttributeError(msg % _diff)


class ExtendConfiguration(object):
    def __init__(self, path="./configs", filename="extend.yaml"):
        self.filename = filename
        self.version = None
        self.hosts = dict()
        self.add_peers = dict()
        self.add_orgs = dict()
        self.add_channels = dict()
        self.extend_channels = dict()
        if self.filename:
            self.config_filepath = os.path.join(path, filename)
        self.updated_config = dict()
        self.extend_explorer = dict()

    def load_config(self):
        if not self.filename:
            raise AttributeError("fabric extend-network yaml file must been provided!")

        with open(self.config_filepath, 'r') as fp:
            data = YAML().load(fp)

        self.version = data.get("version", None)
        if not self.version:
            raise AttributeError(
                f"missing version in extend config file {self.filename}")

        self.hosts = data.get("hosts", {}).get("pool", {})
        self.add_peers = data.get("AddPeers", {})
        self.add_orgs = data.get("AddOrgs", {})
        self.add_channels = data.get("AddChannels", {})
        self.extend_channels = data.get("ExtendChannels", {})
        self.extend_explorer = data.get("ExtendExplorer", {})

    def merge_config(self, filepath, exclude_extend_channel=False):
        """
        update config file by adding the content in extend config
        :param filepath: The path to config file
        :param exclude_extend_channel:
        :return:
        """
        with open(filepath, 'r') as fp:
            yaml = YAML()
            data = yaml.load(fp)

        version = data.get("version", None)
        if not version:
            raise AttributeError(
                f"missing version in config file {filepath}")

        if self.version != version:
            raise AttributeError("config file versions mismatch")

        data["version"] = f"{int(version)+1}"

        if self.hosts:
            data["hosts"]["pool"].update(self.hosts)

        # new peers
        fabric_config = data["fabric"]
        peerOrgs = fabric_config["peerOrgs"]
        for org_name, new_peers in self.add_peers.items():
            org = peerOrgs.get(org_name, None)
            if not org:
                raise AttributeError(f"Organization {org_name} not found, failed to add peers")

            check_intersection(
                org["peers"],
                new_peers,
                f"Organization<{org_name}> to extend peer<%s> have already existed!")

            org["peers"].extend(new_peers)

        # new orgs
        check_intersection(
            peerOrgs.keys(),
            self.add_orgs.keys(),
            f"To extend organization %s have already existed!")
        peerOrgs.update(self.add_orgs)

        # extend channels
        channels = fabric_config["channels"]
        for channel_name, channel_config in self.extend_channels.items():
            channel = channels.get(channel_name, None)
            if not channel:
                raise AttributeError(f"To extend channel<{channel_name}> not found")

            check_contains(
                peerOrgs.keys(),
                channel_config["orgs"],
                f"To extend channel<{channel_name}> organization%s could not been found!")
            check_intersection(
                channel["orgs"],
                channel_config["orgs"],
                f"To extend channel<{channel_name}>'s organization%s have already existed!")

            # merge?
            if not exclude_extend_channel:
                channel["orgs"].extend(channel_config["orgs"])

        # new channels
        # check add channel's configure
        for cid, cfg in self.add_channels.items():
            if "profile" not in cfg:
                raise AttributeError(f"To extend channel<{cid}> must have attr 'profile' !")
            if "consortium" not in cfg:
                raise AttributeError(f"To extend channel<{cid}> must have attr 'consortium' !")
            if len(cfg.get("orgs", [])) < 2:
                raise AttributeError(f"To extend channel<{cid}> must have multiple organizations!")
            check_contains(
                peerOrgs.keys(),
                cfg.get("orgs", []),
                f"To extend channel<{cid}> organization%s could not been found!")

        # check channel id
        if self.add_channels:
            check_intersection(
                channels.keys(),
                self.add_channels.keys(),
                f"To extend channel id %s have already existed!")

            # check if the profile is duplicated
            to_add_profile = [cfg["profile"].lower() for cfg in self.add_channels.values()]
            check_repetition(
                to_add_profile,
                f"To extend channels have the same profile <%s> in {self.filename}"
            )
            check_intersection(
                [cfg["profile"].lower() for cfg in channels.values()],
                to_add_profile,
                f"To extend channels profile %s have already existed!"
            )
            # check if the consortium is duplicated
            to_add_consortium = [cfg["consortium"].lower() for cfg in self.add_channels.values()]
            check_repetition(
                to_add_consortium,
                f"To extend channels have the same consortium <%s> in {self.filename}"
            )
            check_intersection(
                [cfg["consortium"].lower() for cfg in channels.values()],
                to_add_consortium,
                f"To extend channels consortium %s have already existed!"
            )

            channels.update(self.add_channels)

        if self.extend_explorer:
            explorer_config = fabric_config.get("explorer", {})
            if not explorer_config:
                raise AttributeError("No Hyperledger Explorer, no support to extend explorer!")
            add_channels = self.extend_explorer.get("channels", [])

            check_contains(
                channels.keys(),
                add_channels,
                f"To extend explorer channels%s could not been found!")

            check_repetition(
                add_channels,
                f"To extend explorer channels have the same channel <%s> in {self.filename}"
            )

            check_intersection(
                explorer_config.get("channels", []),
                add_channels,
                f"To extend explorer channels %s have already existed!"
            )
            explorer_config["channels"].extend(add_channels)

        """
        for extend channels, increase chaincode version by 0.1 every time
        """
        for extend_channel_name in self.extend_channels.keys():
            for chaincode_name, chaincode_value in data["fabric"]["channels"][extend_channel_name]["chaincodes"].items():
                data["fabric"]["channels"][extend_channel_name]["chaincodes"][chaincode_name]["version"] = format(float(chaincode_value.get("version")) + 0.1, '0.1f')

        self.updated_config = data
        return self.updated_config

    def merge_file(self, path, config_file):
        """
        合并文件
        :param path:
        :param config_file:
        :return:
        """
        output_file_path = os.path.join(path, config_file)

        if os.path.exists(output_file_path):
            backup = os.path.join(path, f"deployment_backup_{self.version}.yaml")
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(output_file_path, backup)

        with open(output_file_path, "w") as fp:
            yaml = YAML()
            yaml.indent(sequence=4, offset=2)
            yaml.dump(self.updated_config, fp)
