#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/28 15:39
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io

    Fabric 网络对应的服务组件（Zookeeper/Kafka/Peer/Cli ... etc）;
    网络、配置文件、证书及操作命令 管理
"""
import os
import shutil
import logging
from collections import OrderedDict
from sortedcontainers import SortedSet
from utils.remote import HostPool, SshHost
from utils import Dict2Obj, format_org_domain, to_array
from .zip import ConfigZipFile
from .module import Role, Element, ZipType
logger = logging.getLogger(__name__)


def check_module(*modules):
    """
    检查服务模块
    :param modules:
    :return:
    """
    for _module in modules:
        if _module not in AssignManage.MODULES:
            logger.error(f'module:{_module} could not been supported! eg:{"/".join(AssignManage.MODULES)}')
            raise AttributeError(f'module:{_module} could not been supported!')


class AssignManage(object):
    """
    服务器对应的服务组件; 配置文件、证书、操作管理
    """
    # fabric network 模块
    MODULES = {'docker', 'zookeeper', 'kafka', 'orderer', 'peer', 'explorer', 'orderer-cli', 'peer-cli'}

    # 清空所有docker 相关的 container & image
    CLEAN_ALL = "docker rm -f -v`docker ps -qa` && " \
                "docker rmi -f $(docker images |grep 'dev-peer'|awk '{print $3}') && " \
                "docker rmi -f $(docker images |grep 'hyperledger'|awk '{print $3}') && " \
                "docker rmi $(docker images -q -f dangling=true)"

    # 清空在运行的container
    CLEAN_CONTAINER = "docker rm -f -v`docker ps -qa`"

    Check_Module = check_module
    To_Array = to_array

    def __init__(self, output):
        self.domain = None
        self.out_put = output
        self.crypto_output = None
        self.configtx_output = None
        self.compose_output = None
        # 主机池管理
        self.host_pool = HostPool()
        # 组件管理
        self.zookeeper = OrderedDict()
        self.kafka = OrderedDict()
        self.orderer = OrderedDict()
        self.orderer_cli = OrderedDict()
        self.org = OrderedDict()
        self.peer = OrderedDict()
        self.peer_cli = OrderedDict()
        self.explorer = OrderedDict()

        self.package_output = os.path.join(self.out_put, "package")
        if not os.path.exists(self.package_output):
            os.makedirs(self.package_output)

        self.remote_bash_path = "$HOME/fabric-scripts"
        self.remote_tmp_path = "/tmp"

    @property
    def network(self,):
        """
        获取 fabric network 模块的 ip/domain
        :return: OrderedDict()
        """
        network = {}
        hosts = []

        def _get(key, elements):
            if key not in network:
                network[key] = OrderedDict()
            for domain in elements:
                ele = elements[domain]
                if key == "peer":
                    if ele.org not in network[key]:
                        network[key][ele.org] = OrderedDict()
                    network[key][ele.org][ele.ip] = ele.role_domain
                else:
                    network[key][ele.ip] = ele.role_domain
                hosts.append(f"{ele.role_domain}:{ele.ip}")

        modules = ("zookeeper", "kafka", "orderer", "peer")
        _ = list(map(lambda m: _get(m, self.__get_module(m)), modules))
        network["hosts"] = hosts
        return network

    @property
    def docker(self):
        """
        获取所有配置服务机器， 安装docker
        :return:
        """
        docker = OrderedDict()
        for ip, _ in self.host_pool.items():
            docker[ip] = Dict2Obj({"role_domain": f'docker-{ip.replace(".", "-")}', "ip": ip})
        return docker

    def __get_module(self, module):
        """
        获取变量
        :param module: 组件名 zookeeper/kafka/orderer/peer/orderer-cli/peer-cli/explorer
        :return:
        """
        _module = module.replace("-", "_")
        if not hasattr(self, _module):
            raise AttributeError(f"module {_module} does not exist!")
        return getattr(self, _module)

    def add_host(self, host):
        """
        添加主机
        :param host: An instance of Host
        :return:
        """
        self.host_pool.add_host(host)

    def get_host(self, _index, throw=False):
        """
        获取ip相应的主机信息
        :param _index: 接受 id/ip/domain
        :param throw
            throw Exception, default false
        :return: <Host>
        """
        return self.host_pool.get_host(_index, throw=throw)

    def get_org_elements(self, module=None, orgs=None):
        """
        获取组织的 Elements
        :param module:
        :param orgs:
        :return:
        """
        check_module(module)
        check_orgs = to_array(orgs, param="orgs")

        # 获取所有排序节点
        if module == "peer-cli" and len(check_orgs) == 1 and check_orgs[0].lower() in ("orderer", "ordererorg"):
            return self.orderer

        # 获取相应服务对应的节点
        _eles = self.__get_module(module)
        if module in ("peer", "peer-cli") and check_orgs:
            _es = OrderedDict()
            for o in check_orgs:
                _o = format_org_domain(o)
                if _o not in self.org:
                    raise AttributeError(f"Org: {_o} is invalid!")
                for _d in self.org[_o][module]:
                    _es[_d] = _eles[_d]
            return _es
        else:
            return _eles

    def add_item(self, index, org, role, domain, ip):
        """
        添加分配管理 item
        :param index:  编号
        :param org:  组织 可以为空
        :param role: 角色 <tool.assign.Role>
        :param domain: 域名
        :param ip: ip地址
        :return:
        """
        if not role or not domain or not ip:
            raise AttributeError("ip、role and domain must be provided!")
        role_domain = f"{role.value}{index}.{domain}"
        self.host_pool.add_index(role_domain, ip)

        if role is Role.ZOOKEEPER:
            self.zookeeper[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)

        elif role is Role.KAFKA:
            self.kafka[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)

        elif role is Role.ORDERER:
            self.orderer[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)
            org_name = org if org else "Orderer"
            if org_name not in self.org:
                self.org[org_name] = SortedSet()
            self.org[org_name].add(role_domain)

        elif role is Role.ORDERER_CLI:
            self.orderer_cli[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)

        elif role is Role.PEER:
            self.peer[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)
            if org not in self.org:
                self.org[org] = OrderedDict()
            if "peer" not in self.org[org]:
                self.org[org]["peer"] = SortedSet()
            self.org[org]["peer"].add(role_domain)

        elif role is Role.PEER_CLI:
            self.peer_cli[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)
            if org not in self.org:
                self.org[org] = OrderedDict()
            if "peer-cli" not in self.org[org]:
                self.org[org]["peer-cli"] = SortedSet()
            self.org[org]["peer-cli"].add(role_domain)

        elif role is Role.EXPLORER:
            self.explorer[role_domain] = Element(self, index=index, ip=ip, role=role, org=org, role_domain=role_domain)

        else:
            raise AttributeError("item role error!")

    def zip(self, *modules):
        """
        压缩服务对应组件需要的配置文件
        """
        def _zip(elements):
            for _domain in elements:
                elements[_domain].reload()
                zip_files = elements[_domain].zip_filenames
                config_zip = ConfigZipFile(elements[_domain].absolute_zip_path)
                for absolute_path in zip_files:
                    archive_path, path_type = zip_files[absolute_path]
                    if path_type is ZipType.FILE:
                        config_zip.add_file(absolute_path, archive_path)
                    elif path_type is ZipType.DIR:
                        config_zip.add_directory(absolute_path, archive_path)
                    else:
                        pass
        _ = list(map(lambda m: _zip(self.__get_module(m)), modules))

    def show_zip(self, module):
        """
        show 服务对应组件需要的配置文件
        :param module: 组件名 zookeeper/kafka/orderer/peer/orderer-cli/peer-cli/explorer
        :return:
        """
        elements = self.__get_module(module)
        for _domain in elements:
            elements[_domain].show_zip_path()

    def handle_func(self, func, modules=None, hosts=None, **kwargs):
        """
        对模块对应的服务器进行操作
        :param func:   def handle(domain, ele, host)
        :param modules:  组件名 zookeeper/kafka/orderer/peer/orderer-cli/peer-cli/explorer
        :param hosts:  主机 ips/domains
        :param kwargs:
            orgs :  当modules 为 peer/peer-cli 时 支持 org 选择；
                    当指定 ips/domains 不支持 org 选择
        :return:
        """
        modules = to_array(modules, "modules")
        hosts = to_array(hosts, "hosts")

        if not modules:
            logger.error(f'Please specify the module [{"/".join(AssignManage.MODULES)}]')
            return

        if hosts and len(modules) > 1:
            logger.error('Host cannot be specified when multiple modules are specified!')
            return

        if hosts:
            module = modules[0]
            # 当处理 peer/peer-cli 模块时指定了 --remote-hosts, 只支持指定一个 org
            _tmp_msg = ""
            if module in ("peer", "peer-cli"):
                orgs = kwargs.get("orgs", [])
                if len(orgs) == 0:
                    logger.error(f"When dealing with module<{module}>, it is specified that --remote-hosts,"
                                 f"parameter --remote-org/--install-org have to fill one org-name!")
                    return
                if orgs and len(orgs) != 1:
                    logger.error(f"When dealing with module<{module}>, it is specified that --remote-hosts,"
                                 f"parameter --remote-org/--install-org supports only one org-name!")
                    return
                _tmp_msg = f"<organization [{format_org_domain(orgs[0])}]>"
                elements = self.get_org_elements(module, orgs)
            else:
                elements = self.get_org_elements(module)

            # 获取模块所有的 ips
            module_ips = list(map(lambda e: e.ip, elements.values()))
            # 模块下待处理的 ips
            todo_ips = SortedSet()
            for h in hosts:
                host = self.get_host(h, throw=True)
                if host.ip not in module_ips:
                    logger.error(f'The host<{h}> does not belong to the peers of the module <{module}{_tmp_msg}>')
                    return
                todo_ips.add(host.ip)
            # do func
            for k in elements:
                ele = elements[k]
                if ele.ip in todo_ips:
                    func(domain=ele.role_domain, ele=ele, host=self.get_host(ele.ip), **kwargs)
        else:
            for _module in modules:
                elements = self.get_org_elements(_module, kwargs.get("orgs", None))
                for d, e in elements.items():
                    func(ele=e, host=self.get_host(e.ip), domain=d, **kwargs)

    def clean_package(self):
        """
        清空输出目录
        :return:
        """
        if os.path.exists(self.package_output):
            shutil.rmtree(self.package_output)

    def clean_env(self):
        """
        清除所有 docker containers and /data and $HOME/fabric-scripts
        sh -c 'CONTAINER=`docker ps -qa`; if [ -n "$CONTAINER" ]; then sudo docker rm -f $CONTAINER; fi'
        :return:
        """
        for _, host in self.host_pool.items():
            logger.info(f"Clear {host} env ...")
            _cmd = [f"sh -c 'CONTAINERS=`docker ps -qa`; "
                    f"if [ -n \"$CONTAINERS\" ]; then sudo docker rm -f $CONTAINERS; fi'"]
            if self.remote_tmp_path != "/":
                _cmd.append(f"sh -c 'if [ -x {self.remote_bash_path} ]; then sudo rm -rf {self.remote_bash_path}; fi'")
            _cmd.append(f"sh -c 'if [ -x /data ]; then sudo rm -rf /data; fi'")

            # remove docker images
            _cmd.append("""docker images | grep "^hyperledger" | awk '{print $3}' > /tmp/h""")
            _cmd.append("""docker images -q > /tmp/a""")
            _cmd.append(f"sh -c 'IMAGES=`sort /tmp/a /tmp/h | uniq -u`; "
                        f"if [ -n \"$IMAGES\" ]; then sudo docker rmi $IMAGES; fi'")

            SshHost.getConnection(host).run(f"{' && '.join(_cmd)}", throw=False)

    @property
    def first_orderer_service(self):
        """
        获取第一个 Orderer Service 域名地址
        :return:
        """
        for d in self.orderer:
            return f"{d}:7050"
        else:
            raise AttributeError("There are no optional orderer services")

    @property
    def first_orderer_cli(self):
        """
        获取第一个 Orderer CLi 域名地址
        :return:
        """
        for d in self.orderer_cli:
            return d
        else:
            raise AttributeError("There are no optional orderer-cli services")

    @property
    def peer_cli_tls_ca(self):
        """
        Peer-Cli Container TLS证书路径
        :return:
        """
        return f"/etc/fabric/crypto/ordererOrganizations/{self.domain}/users/Admin@{self.domain}" \
            f"/msp/tlscacerts/tlsca.{self.domain}-cert.pem"

    @property
    def orderer_cli_tls_ca(self):
        """
        Peer-Cli Container TLS证书路径
        :return:
        """
        return f"/etc/hyperledger/users/Admin@{self.domain}/msp/tlscacerts/tlsca.{self.domain}-cert.pem"
