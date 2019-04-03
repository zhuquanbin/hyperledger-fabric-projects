#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/25 17:10
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

import os
import unittest

from utils.configtx import *
from utils.configuration import Configuration, ExtendConfiguration
from utils.context import DeployContext
from utils.tool import *


class MyTestCase(unittest.TestCase):
    def setUp(self):
        # self.cfg = Configuration("./configs/", "deployment.yaml", configOutPath="./gen")
        self.deploy = DeployContext(cfg=Configuration("./configs/", "deployment.yaml", configOutPath="./gen"),
                                    ext=ExtendConfiguration(),
                                    virtual_host=True)
        self.deploy.load_network()

    def test_gen_crypto(self):
        self.deploy.crypto_gen()

    def test_compose_gen(self):
        self.deploy.compose_gen()

    def test_compose_package(self):
        self.deploy.compose_zip("zookeeper", "kafka", "orderer", "orderer-cli", "peer", "peer-cli", "explorer")

    def test_configtx_gen_orderer_org(self):
        self.deploy.configtx_handler.gen_orderer_genesis()

    def test_configtx_gen_channel_org(self):
        self.deploy.configtx_handler.gen_channel_genesis(CustomChannel("parcelxchannel1.block", "ParcelXOrgsChannel", "parcelxchannel1"))
    #
    # def test_configtx_proto_decode(self):
    #     self.cfg.configtx_handler.proto_decode("config_block.pb")

    def test_configtx_print_org(self):
        filepath = self.deploy.configtx_handler.print_org("orgEast")
        print(filepath)

    def test_config_zip(self):
        cz = ConfigZipFile(os.path.join(self.deploy.cfg.config_output, "test.zip"))
        cz.add_directory("./utils/cryptogen", "scripts")
        cz.add_file("./README.md", "file")

    def test_zip_cp(self):
        self.deploy.scp_zip()

    def test_exec_json(self):
        print(self.deploy.get_exec_status("fabric_network_nodes"))
        self.deploy.set_exec_status(fabric_network_nodes=2)

    def test_config_tx_ext_channel(self):
        self.deploy.channel(extend=True, channel_id="channeldev1", extend_orgname="orgWest")

    def test_config_tx_ext_system(self):
        self.deploy.config_tx_ext_consortium("ParcelXConsortium2")


if __name__ == '__main__':
    unittest.main()
