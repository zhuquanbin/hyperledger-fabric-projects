#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/2/15 10:35
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io

Fabric 网络服务组件管理
"""
import os
import json
from collections import OrderedDict
from utils import POSIX, to_array
from enum import Enum, IntEnum, unique


@unique
class ZipType(IntEnum):
    FILE = 0
    DIR = 1


@unique
class Role(Enum):
    ZOOKEEPER = "zookeeper"
    KAFKA = "kafka"
    ORDERER = "orderer"
    ORDERER_CLI = "orderer-cli"
    PEER = "peer"
    PEER_CLI = "peer-cli"
    EXPLORER = "explorer"


class Element(object):
    """
    组件相应的配置文件目录管理
    """
    def __init__(self, parent, **kwargs):
        self.parent = parent

        # 角色对应的index
        self.index = kwargs["index"]
        # 对应的ip地址
        self.ip = kwargs["ip"]
        # 对应的 <class Role>
        self.role = kwargs["role"]
        # 对应所在的组织
        self.org = kwargs["org"]
        # 系统域名
        self.domain = self.parent.domain
        # 角色对应的域名
        self.role_domain = kwargs["role_domain"]

        # zip 包名
        self.zip_name = self.role_domain.replace(".", "-") + ".zip"
        # zip 包相对路径
        self.absolute_zip_path = os.path.join(self.parent.package_output, self.zip_name)
        # zip 包待压缩的文件列表
        self.zip_filenames = OrderedDict()

        # docker container name
        self.docker_container_name = None
        # docker container volume
        self.docker_container_volume = None

        # zip 初始化
        self.__zip_path()
        # 用于peer运行时， export出的环境变量
        self.env = {}
        # bash dir
        self.bash_root = self.parent.remote_bash_path

    def __bash_path_join(self, yaml):
        """
        配置角色对应脚本安装路径
        :return:
        """
        # compose
        absolute_path = os.path.join(self.parent.compose_output, yaml)
        self.zip_filenames[absolute_path] = ("", ZipType.FILE)
        # bash
        absolute_path = os.path.join(self.parent.compose_output, f"{self.role_domain}.sh")
        self.zip_filenames[absolute_path] = ("", ZipType.FILE)

    def __crypto_path_join(self, path, t=ZipType.DIR):
        """
        目录拼接，设置证书路径和归档路径
        :param path:  证书相对路径
        :return:
        """
        absolute_path = os.path.join(self.parent.crypto_output, path)
        if t is ZipType.DIR:
            self.zip_filenames[absolute_path] = (path, t)
        elif t is ZipType.FILE:
            self.zip_filenames[absolute_path] = (os.path.dirname(path), t)
        else:
            pass

    def __zip_path(self):
        """
        配置角色对应的配置文件路径
        :return:
        """
        # docker compose & bash
        self.__bash_path_join(f"{self.role.value}.yaml")

        if self.role in (Role.ZOOKEEPER, Role.KAFKA):
            self.docker_container_name = f"{self.role.value}{self.index}"
            self.docker_container_volume = f"/data/{self.role.value}/{self.index}"

        # elif self.role is Role.KAFKA:
        #     self.docker_container_name = f"{self.role.value}{self.index}"
        #     self.docker_container_volume = f"/data/{self.role.value}/{self.index}"

        elif self.role is Role.PEER:
            # peer msp
            path = f"crypto-config/peerOrganizations/{self.org}.{self.domain}/peers/{self.role_domain}"
            self.__crypto_path_join(path)
            # docker info
            self.docker_container_name = self.role_domain
            self.docker_container_volume = f"/data/fabric/{self.role_domain}/production"

        elif self.role is Role.PEER_CLI:
            # peer tls cert
            path = f"crypto-config/peerOrganizations/{self.org}.{self.domain}/peers/{self.role_domain}/tls".replace("-cli", "")
            self.__crypto_path_join(path)
            # peer user msp
            path = f"crypto-config/peerOrganizations/{self.org}.{self.domain}/users"
            self.__crypto_path_join(path)
            # orderer tls ca
            path = f"crypto-config/ordererOrganizations/{self.domain}/users/Admin@{self.domain}/msp/tlscacerts/"
            self.__crypto_path_join(path)
            # docker info
            self.docker_container_name = self.role_domain
            self.docker_container_volume = f'/data/fabric/{self.role_domain.replace("-cli", "")}/cli-data'

        elif self.role is Role.ORDERER:
            # orderer msp
            path = f"crypto-config/ordererOrganizations/{self.domain}/orderers/{self.role_domain}"
            self.__crypto_path_join(path)
            # docker info
            self.docker_container_name = self.role_domain

        elif self.role is Role.ORDERER_CLI:
            # orderer user msp
            path = f"crypto-config/ordererOrganizations/{self.domain}/users/"
            self.__crypto_path_join(path)
            # docker info
            self.docker_container_name = self.role_domain

        elif self.role is Role.EXPLORER:
            # add sdk config
            absolute_path = os.path.join(self.parent.compose_output, "config.json")
            self.zip_filenames[absolute_path] = ("", ZipType.FILE)
            # add explorer db
            absolute_path = os.path.join(self.parent.compose_output, "explorer-db.yaml")
            self.zip_filenames[absolute_path] = ("", ZipType.FILE)

            self.docker_container_name = ["fabric-explorer-db", "fabric-explorer"]
        else:
            pass

    def reload(self):
        if self.role is Role.EXPLORER:
            config_path = os.path.join(self.parent.compose_output, "config.json")
            if not os.path.exists(config_path):
                raise AttributeError(f"fabric-explorer config.json not exist!")
            with open(config_path, "r") as fp:
                config = json.load(fp)

                organizations = config["network-configs"]["network-1"]["organizations"]
                for value in organizations.values():
                    if "adminPrivateKey" in value:
                        self.__crypto_path_join(value["adminPrivateKey"]["path"][5:])
                    if "signedCert" in value:
                        self.__crypto_path_join(value["signedCert"]["path"][5:])

                peers = config["network-configs"]["network-1"]["peers"]
                for value in peers.values():
                    if "tlsCACerts" in value:
                        self.__crypto_path_join(value["tlsCACerts"]["path"][5:], t=ZipType.FILE)

            if os.path.exists(self.absolute_zip_path):
                os.remove(self.absolute_zip_path)
        else:
            pass

    def add_zip_path(self, absolute_path, archive_path, path_type):
        """
        添加压缩文件
        :param absolute_path:  系统绝对路径
        :param archive_path:    压缩文件归档路径
        :param path_type:  类型
        :return:
        """
        if type not in (ZipType.DIR, ZipType.FILE):
            raise AttributeError("Add zip path type error! (ZipType.DIR | ZipType.FILE)")
        self.zip_filenames[absolute_path] = (archive_path, path_type)

    def show_zip_path(self):
        print(f"ZIP: {self.zip_name}")
        for absolute_path in self.zip_filenames:
            print(f"\tAbsolute path: {POSIX(absolute_path)}")
            print(f"\t\tArchive path: {POSIX(self.zip_filenames[absolute_path][0])}")
            archive_type = "FILE" if self.zip_filenames[absolute_path][1] is ZipType.FILE else "DIR"
            print(f"\t\tArchive type: {archive_type}")

    @property
    def remote_os_path(self):
        """
        获取zip包远程服务器的路径
        :return: linux <zip path>
        """
        return POSIX(os.path.join(self.parent.remote_tmp_path, self.zip_name))

    @property
    def remote_unzip_bashes(self):
        """
        获取解压 zip 命令
        :return: list<command>
        """
        return [
            # 安装 unzip command
            # 'sh -c \'if ! [ -x $(command -v unzip) ]; then apt-get install unzip -y; else echo "unzip installed"; fi\'',
            'command -v unzip >/dev/null 2>&1 || { sudo apt-get install unzip -y; }',
            # # 创建解压目录
            f"mkdir -p {self.parent.remote_bash_path}",
            # 解压压缩文件到指定目录
            f"unzip -o {self.remote_os_path} -d {self.parent.remote_bash_path}"
        ]

    @property
    def install_bashes(self):
        """
        获取安装组件的命令
        :return: list<command>
        """
        if self.role is Role.EXPLORER:
            return [
                f"cd {self.bash_root}",
                f"sudo docker-compose -f explorer-db.yaml up -d",
                f"sleep 5",
                f"docker exec -i fabric-explorer-db bash -c \"sudo -s -u postgres ./createdb.sh\"",
                f"sleep 1",
                f"sudo docker-compose -f explorer.yaml up -d"
            ]
        else:
            return [
                f"cd {self.bash_root}",
                f"sudo sh {self.role_domain}.sh"
            ]

    @property
    def restart_bashes(self):
        """
        重启组件的命令
        :return:
        """
        if self.role is Role.EXPLORER:
            return [
                "sudo docker restart fabric-explorer"
            ]
        else:
            raise NotImplemented

    @property
    def uninstall_bashes(self):
        """
        获取卸载组件的命令
        :return: list<command>
        """
        _cmd = []
        if not self.docker_container_name:
            raise AttributeError(f"unknown docker container name, role: {self.role}, index: {self.index}")
        # 删除容器命令
        for container in to_array(self.docker_container_name, to_lower=False):
            _cmd.append(f'sudo docker rm -f {container}')

        # 删除本地挂载目录
        for v in to_array(self.docker_container_volume):
            if v not in ("/", "/data"):
                _cmd.append(f"sudo rm -rf {v}")

        return _cmd

    @property
    def detect_bashes(self):
        """
        探测组件服务状态
        :return: list<command>
        """
        return [
            f"sudo docker ps -f name={container} && "
            f"sudo docker logs --tail 10 {container}"
            for container in to_array(self.docker_container_name, to_lower=False)
        ]

