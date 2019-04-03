#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 14:49
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import json
import shutil
from ruamel.yaml import YAML
from utils.compose.template import *
from utils import format_org_domain, format_org_msp_id
from collections import OrderedDict


class DockerComposeGen(object):
    def __init__(self, out):
        self.yaml = YAML()
        self.yaml.indent(sequence=4, offset=2)
        self.domain = None
        self.fabric_network = None
        self.virtual_host = False
        self.config_output = os.path.join(out, "docker-compose")
        if not os.path.exists(self.config_output):
            os.makedirs(self.config_output)

    def load_network(self, **kwargs):
        self.domain = kwargs["domain"]
        self.fabric_network = kwargs["network"]
        self.__generate_zookeeper_services()
        self.__generate_kafka_brokers()

    def __generate_from_template(self, idx, prefix, suffix, template_path, **kwargs):
        """
        :param idx:    docker compose id
        :param prefix: docker compose file name prefix
        :param suffix: docker compose file name suffix
        :param template_path: docker compose template file
        :param kwargs: docker compose configure
        :return: None
        """

        with open(template_path, "r", encoding="utf-8") as fp:
            template = self.yaml.load(fp)

        # update key value
        for key in kwargs:
            sub_keys = key.split(".")
            sub_dict = template
            for sub_key in sub_keys[:-1]:
                if sub_key not in sub_dict:
                    raise AttributeError(f"{key} is invalid!")
                sub_dict = sub_dict[sub_key]

            if sub_keys[-1] in sub_dict:
                sub_dict[sub_keys[-1]] = kwargs[key]
            else:
                raise AttributeError(f"{key} is invalid!")

        if suffix:
            filepath = os.path.join(self.config_output, f"{prefix}{idx}.{suffix}.yaml")
        else:
            filepath = os.path.join(self.config_output, f"{prefix}{idx}.yaml")

        if self.virtual_host:
            services = template.get("services", {})
            for _, service in services.items():
                if prefix not in ("kafka", "zookeeper") and "GODEBUG=netdns=go" not in service["environment"]:
                    service["environment"].append("GODEBUG=netdns=go")

        with open(filepath, "w", encoding="utf-8") as fp:
            self.yaml.dump(template, fp)

        return os.path.basename(filepath)

    def __generate_bash(self, idx, prefix, suffix, command, **envs):
        if suffix:
            filepath = os.path.join(self.config_output, f"{prefix}{idx}.{suffix}.sh")
        else:
            filepath = os.path.join(self.config_output, f"{prefix}{idx}.sh")

        with open(filepath, "wb") as fp:
            fp.write(b"#!/bin/bash\n")
            for key in envs:
                fp.write(bytes(f"export {key}={envs[key]}\n", encoding="utf-8"))
            if command:
                fp.write(bytes(command, encoding="utf8"))

    def __generate_zookeeper_services(self):
        # generate zoo_services
        zoo_services = None
        kafka_zoo_services = None
        for idx, _ in enumerate(self.fabric_network["zookeeper"]):
            id = idx + 1
            if zoo_services:
                zoo_services += f" server.{id}=zookeeper{id}.{self.domain}:2888:3888"
                kafka_zoo_services += f",zookeeper{id}.{self.domain}:2181"
            else:
                zoo_services = f"server.{id}=zookeeper{id}.{self.domain}:2888:3888"
                kafka_zoo_services = f"zookeeper{id}.{self.domain}:2181"

        self.zoo_services = f'\'{zoo_services}\''
        self.kafka_zoo_services = kafka_zoo_services

    def __generate_kafka_brokers(self):
        kafka_brokers = ""
        for idx, _ in enumerate(self.fabric_network["kafka"]):
            if kafka_brokers:
                kafka_brokers += f",kafka{idx}.{self.domain}:9092"
            else:
                kafka_brokers = f"kafka{idx}.{self.domain}:9092"
        self.kafka_brokers = f'"[{kafka_brokers}]"'

    def generate_zookeeper_compose(self):
        # generate docker compose
        kwargs = {"services.zookeeper.extra_hosts": self.fabric_network["hosts"]}
        yaml_name = self.__generate_from_template("", "zookeeper", None, ZOOKEEPER_TEMPLATE, **kwargs)

        # generate script bash file
        for idx, _ in enumerate(self.fabric_network["zookeeper"]):
            self.__generate_bash(idx+1, "zookeeper", self.domain, f"docker-compose -f ./{yaml_name} up -d",
                                 ZOOKEEPER_NODE=idx+1,
                                 IMAGE_TAG=self.fabric_network["version"].get("zookeeper", "0.4.14"),
                                 ZOOKEEPER_SERVERS=self.zoo_services.replace(f"zookeeper{idx+1}.{self.domain}", "0.0.0.0"))

    def generate_kafka_compose(self):
        # generate docker compose
        kwargs = {"services.kafka.extra_hosts": self.fabric_network["hosts"]}
        yaml_name = self.__generate_from_template("", "kafka", None, KAKFA_TEMPLATE, **kwargs)

        # generate script bash file
        for idx, _ in enumerate(self.fabric_network["kafka"]):
            self.__generate_bash(idx, "kafka", self.domain, f"docker-compose -f ./{yaml_name} up -d",
                                 KAFKA_NODE=idx,
                                 IMAGE_TAG=self.fabric_network["version"].get("kafka", "0.4.14"),
                                 ZOOKEEPER_SERVERS=self.kafka_zoo_services,
                                 DOMAIN=self.domain)

    def generate_orderer_compose(self):
        # generate docker compose
        kwargs = {"services.orderer.extra_hosts": self.fabric_network["hosts"]}
        yaml_name = self.__generate_from_template("", "orderer", None, ORDERER_TEMPLATE, **kwargs)

        # generate orderer cli
        kwargs = {"services.orderer-cli.extra_hosts": self.fabric_network["hosts"]}
        cli_yaml_name = self.__generate_from_template("", "orderer-cli", None, ORDERER_CLI_TEMPLATE, **kwargs)

        # generate script bash file
        for idx, _ in enumerate(self.fabric_network["orderer"]):
            self.__generate_bash(idx, "orderer", self.domain, f"docker-compose -f ./{yaml_name} up -d",
                                 ORDERER_ID=idx,
                                 IMAGE_TAG=self.fabric_network["version"].get("orderer", "1.3.0"),
                                 KAFKA_BROKERS=self.kafka_brokers,
                                 DOMAIN=self.domain)

            self.__generate_bash(idx, "orderer-cli", self.domain, f"docker-compose -f ./{cli_yaml_name} up -d",
                                 IMAGE_TAG=self.fabric_network["version"].get("orderer", "1.3.0"),
                                 ORDERER_ID=idx,
                                 DOMAIN=self.domain)

    def generate_org_compose(self, org):
        if org not in self.fabric_network["peer"]:
            raise AttributeError(f"{org} not found!")

        # generate peer and peer-cli docker compose
        kwargs = {"services.peer.extra_hosts": self.fabric_network["hosts"]}
        peer_yaml_name = self.__generate_from_template("", "peer", None, PEER_TEMPLATE, **kwargs)
        kwargs = {"services.peer-cli.extra_hosts": self.fabric_network["hosts"]}
        peer_cli_yaml_name = self.__generate_from_template("", "peer-cli", None, PEER_CLI_TEMPLATE, **kwargs)

        # generate script bash file
        org_peers = self.fabric_network["peer"][org].values()
        _org_msp = f"{org}MSP"
        org_msp = _org_msp[0].upper() + _org_msp[1:]
        for idx, _ in enumerate(org_peers):
            self.__generate_bash(idx, "peer", f"{org}.{self.domain}", f"docker-compose -f ./{peer_yaml_name} up -d",
                                 PEER_ID=idx,
                                 IMAGE_TAG=self.fabric_network["version"].get("peer", "1.3.0"),
                                 PEER_ORG=org,
                                 PEER_LOCALMSPID=org_msp,
                                 GOSSIP_BOOTSTRAP=f"peer0.{org}.{self.domain}:7051",
                                 DOMAIN=self.domain)

            self.__generate_bash(idx, "peer-cli", f"{org}.{self.domain}", f"docker-compose -f ./{peer_cli_yaml_name} up -d",
                                 PEER_ID=idx,
                                 IMAGE_TAG=self.fabric_network["version"].get("peer", "1.3.0"),
                                 PEER_ORG=org,
                                 PEER_LOCALMSPID=org_msp,
                                 DOMAIN=self.domain)

    def generate_explorer_config(self):
        """
        生成 fabric explorer 使用的配置文件
        :return:
        """
        with open(EXPLORER_CONFIG_TEMPLATE, "r") as fp:
            config = json.load(fp)

        clients = OrderedDict()
        channels = OrderedDict()
        organizations = OrderedDict()
        peers = OrderedDict()

        orderers = OrderedDict()
        for _ip, _dm in self.fabric_network.get("orderer", {}).items():
            orderers[_dm] = {
                "url": f"grpcs://{_ip}:7050"
            }
        orderer_id = format_org_msp_id(self.fabric_network["orderer_org"]["name"])
        organizations[orderer_id] = {
            "mspid": orderer_id,
            "adminPrivateKey": {
                "path": f"/tmp/crypto-config/ordererOrganizations/{self.domain}/users/Admin@{self.domain}/msp/keystore"
            }
        }

        for channel_id in self.fabric_network.get("channels", {}):
            lower_id = channel_id.lower()
            orgs = self.fabric_network["channels"][channel_id].get("orgs", [])
            if not orgs:
                raise ValueError(f"Orgs node not found in channel config: {channel_id}")
            connect_org = format_org_domain(orgs[0])

            clients[f"client-{lower_id}"] = {
                "tlsEnable": True,
                "organization": connect_org,
                "channel": lower_id,
                "credentialStore": {
                    "path": f"./tmp/credentialStore/{lower_id}/credential",
                    "cryptoStore": {
                        "path": f"./tmp/credentialStore/{lower_id}/crypto"
                    }
                }
            }

            # add organization
            if connect_org not in organizations:
                organizations[connect_org] = {
                    "mspid": format_org_msp_id(connect_org),
                    "fullpath": False,
                    "adminPrivateKey": {
                        "path": f"/tmp/crypto-config/peerOrganizations/{connect_org}.{self.domain}/users/"
                        f"Admin@{connect_org}.{self.domain}/msp/keystore"
                    },
                    "signedCert": {
                        "path": f"/tmp/crypto-config/peerOrganizations/{connect_org}.{self.domain}/users/"
                        f"Admin@{connect_org}.{self.domain}/msp/signcerts"
                    }
                }

            # add channel
            channels[lower_id] = {
                "peers": {
                    # peer_domain: {}
                },
                "connection": {
                    "timeout": {
                        "peer": {
                            "endorser": "6000",
                            "eventHub": "6000",
                            "eventReg": "6000"
                        }
                    }
                }
            }
            # add peer
            org_peers = self.fabric_network["peer"].get(connect_org, {})
            if not org_peers:
                raise ValueError(f"Peers node not found in organization: {connect_org}")
            for peer_ip in org_peers:
                peer_domain = org_peers[peer_ip]
                channels[lower_id]["peers"][peer_domain] = {}
                if peer_domain not in peers:
                    peers[peer_domain] = {
                        "tlsCACerts": {
                            "path": f"/tmp/crypto-config/peerOrganizations/{connect_org}.{self.domain}/peers/{peer_domain}/tls/ca.crt"
                        },
                        "url": f"grpcs://{peer_ip}:7051",
                        "eventUrl": f"grpcs://{peer_ip}:7053",
                        "grpcOptions": {
                            "ssl-target-name-override": peer_domain
                        }
                    }

        config["network-configs"]["network-1"]["clients"] = clients
        config["network-configs"]["network-1"]["channels"] = channels
        config["network-configs"]["network-1"]["organizations"] = organizations
        config["network-configs"]["network-1"]["peers"] = peers
        config["network-configs"]["network-1"]["orderers"] = orderers
        with open(os.path.join(self.config_output, "config.json"), "w") as fp:
            json.dump(config, fp, indent=4)

    def generate_explorer_compose(self):
        kwargs = {"services.explorer.extra_hosts": self.fabric_network["hosts"]}
        explorer = self.__generate_from_template("", "explorer", None, EXPLORER_TEMPLATE, **kwargs)
        explorer_db = self.__generate_from_template("", "explorer-db", None, EXPLORER_DB_TEMPLATE)
        self.generate_explorer_config()
        command = "\n".join([
            f"docker-compose -f {explorer_db} up -d",
            "sleep 5",
            f'docker exec -it fabric-explorer-db bash -c "./createdb.sh"',
            "sleep 1",
            f'docker-compose -f {explorer} up -d',
            "sleep 1"
        ])
        self.__generate_bash("", f"explorer.{self.domain}", "", command)

    def generate_all(self, virtual_host):
        self.virtual_host = virtual_host
        self.generate_zookeeper_compose()
        self.generate_kafka_compose()
        self.generate_orderer_compose()
        for org in self.fabric_network["peer"]:
            self.generate_org_compose(org)
        self.generate_explorer_compose()

    def clean_output(self):
        """
        清空输出目录
        :return:
        """
        if os.path.exists(self.config_output):
            shutil.rmtree(self.config_output)
