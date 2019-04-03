#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 15:14
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

from invoke import UnexpectedExit
from fabric import Connection, Config
from collections import OrderedDict
import logging
logger = logging.getLogger(__name__)


class Host(object):
    """
    主机登录信息
    """
    def __init__(self, ip, **kwargs):
        """
        :param ip:
        :param kwargs:
            id:
                ip对应的编号
            username:
                login user
            password：
                login pass
            key:
                login private cert
        """
        self.ip = ip
        self.id = kwargs.get("id", None)
        self.username = kwargs.get("username", None)
        self.password = kwargs.get("password", None)
        self.key = kwargs.get("key", None)
        if not self.username:
            raise AttributeError(f"host<{self.ip}> login user must be provided!")

        if not self.password and not self.key:
            raise AttributeError(f"host<{self.ip}> login password or key must be provided!")

    def __repr__(self):
        return "<Host: %s>" % self.ip


class HostPool(object):
    """
    主机信息管理池
    """
    def __init__(self):
        self.pool = OrderedDict()
        self.index = OrderedDict()

    def add_host(self, host):
        """
        添加Host 到 pool 中
        :param host:
        :return:
        """
        if isinstance(host, Host):
            self.pool[host.ip] = host
            if host.id:
                self.add_index(host.id, host.ip)
        else:
            raise ValueError("param 'host' only accept type <utils.remote.Host>")

    def add_index(self, _index, _ip):
        """
        为主机添加索引
        :param _index:
            domain / id
        :param _ip:
            ip
        :return:
        """
        _value = self.index.get(_index, None)
        if _value and _value != _ip:
            logger.warning(f"{_ip} and {_value} have same index: {_index}")
        if _index and _ip:
            self.index[_index] = _ip

    def get_host(self, _index, throw=False):
        """
        获取 主机信息
        :param _index:  ip/id/domain
        :param throw:
                :raise AttributeError
        :return: <utils.remote.Host>
        """
        if _index in self.pool:
            return self.pool[_index]
        elif _index in self.index:
            return self.pool[self.index[_index]]
        else:
            if throw:
                raise AttributeError(f"Invalid host index: {_index}")
            else:
                return None

    def items(self):
        """
        遍历所有主机
        :return:
        """
        for ip in self.pool:
            yield ip, self.pool[ip]


class SshHost(object):
    # 连接池
    SSH_POOL_HOSTS = OrderedDict()

    @staticmethod
    def getConnection(host):
        """获取连接"""
        if isinstance(host, Host):
            if host.ip not in SshHost.SSH_POOL_HOSTS:
                SshHost.SSH_POOL_HOSTS[host.ip] = SshHost(host)
            return SshHost.SSH_POOL_HOSTS[host.ip]
        else:
            raise AttributeError("required Object<utils.remote.Host>")

    def __init__(self, host):
        self.host = host
        self.conn = self.connect(host)

    def connect(self, host):
        if isinstance(host, Host):
            config = Config(overrides={'sudo': {'password': host.password}})
            if hasattr(host, "keyFile"):
                connArgs = {'key_filename': host.keyFile}
            else:
                connArgs = {'password': host.password}
            return Connection(host.ip, user=host.username, connect_kwargs=connArgs, config=config)
        else:
            raise AttributeError("required Object<utils.remote.Host>")
    #
    # def check(self, log, ret):
    #     if isinstance(ret, TransferResult):
    #         logger.info(f"{log}")
    #     elif isinstance(ret, CommandResult):
    #         if ret.stdout:
    #             logger.info(f"{ret.stdout.strip()}")
    #         if ret.stderr:
    #             logger.info(f"{ret.stderr.strip()}")
    #     else:
    #         pass

    def sudo(self, cmd, throw=True, **kwargs):
        try:
            logger.info(f"[{self.host.ip}] bash# {cmd}")
            if self.conn and isinstance(self.conn, Connection):
                ret = self.conn.sudo(cmd, **kwargs)
                return ret
            else:
                raise AttributeError("cannot login in remote ssh!")
        except UnexpectedExit as e:
            if throw:
                raise RuntimeError(e.result)
            else:
                logger.error(e.result)

    def run(self, cmd, throw=True, **kwargs):
        try:
            logger.info(f"[{self.host.ip}] bash# {cmd}")
            if self.conn and isinstance(self.conn, Connection):
                ret = self.conn.run(cmd, **kwargs)
                return ret
            else:
                raise AttributeError("cannot login in remote ssh!")
        except UnexpectedExit as e:
            if throw:
                raise RuntimeError(e.result)
            else:
                logger.error(e.result)

    def download(self, remote, local, **kwargs):
        """
        Download a file from the current connection to the local filesystem.
        :param remote: Remote file to download.
        :param local: Local path to store downloaded file in, or a file-like object.
        :return:
        """
        try:
            if self.conn and isinstance(self.conn, Connection):
                ret = self.conn.get(remote, local=local)
                logger.info(f"download file {remote} from {self.host.ip}")
                return ret
            else:
                raise AttributeError("cannot login in remote ssh!")
        except UnexpectedExit as e:
            if kwargs.get("throw", True):
                raise RuntimeError(e.result)
            else:
                logger.error(e.result)

    def upload(self, local, remote, **kwargs):
        """
        Upload a file from the local filesystem to the current connection.
        :param local: Local path of file to upload, or a file-like object.
        :param remote: Remote path to which the local file will be written.
        :return:
        """
        try:
            if self.conn and isinstance(self.conn, Connection):
                logger.info(f"upload file {local} to {self.host.ip}")
                ret = self.conn.put(local, remote=remote)
                return ret
            else:
                raise AttributeError("cannot login in remote ssh!")
        except UnexpectedExit as e:
            if kwargs.get("throw", True):
                raise RuntimeError(e.result)
            else:
                logger.error(e.result)

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
        else:
            pass

    def __del__(self):
        self.close()
