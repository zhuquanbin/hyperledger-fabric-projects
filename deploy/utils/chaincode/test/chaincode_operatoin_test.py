#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
@Author     : luzhao
@Email      : zhao.lu@parcelx.io
@date       : 2/27/2019 3:57 PM
@Description:
-------------------------------------------------
"""
import unittest

from utils.chaincode.operation import Operation, ChaincodeInstallOperator, ChaincodeInstantiateOperator, \
    ChaincodeUpgradeOperator, ChaincodeQueryOperator


class ChaincodeOperationTest(unittest.TestCase):

    def setUp(self):
        self.operation = Operation()

    def test_install_chaincode(self):
        cc_install_operator = ChaincodeInstallOperator(channel_name="channeldev1",
                                                        peer_names=["peer0.orgEast.parcelx.io","peer1.orgEast.parcelx.io"],
                                                        chaincode_names=["parcel7"])
        cc_install_operators = [cc_install_operator]
        self.operation.chaincode_install(cc_install_operators)

    def test_instantiate_chaincode(self):
        cc_instantiate_operator = ChaincodeInstantiateOperator(channel_name="channeldev1",
                                                                peer_names=["peer0.orgEast.parcelx.io","peer1.orgEast.parcelx.io"],
                                                                chaincode_names=["parcel7"])
        cc_instantiate_operators = [cc_instantiate_operator]
        self.operation.chaincode_instantiate(cc_instantiate_operators)

    def test_upgrade_chaincode(self):
        cc_upgrade_operator = ChaincodeUpgradeOperator(channel_name="channeldev1",
                                                            peer_names=["peer0.orgEast.parcelx.io","peer1.orgEast.parcelx.io"],
                                                            chaincode_names=["parcel7"])
        cc_upgrade_operators = [cc_upgrade_operator]
        self.operation.chaincode_upgrade(cc_upgrade_operators)

    def test_query_chaincode_installed(self):
        cc_query_operator = ChaincodeQueryOperator(peer_names=["peer0.orgEast.parcelx.io","peer0.orgNorth.parcelx.io"])
        cc_query_operators = [cc_query_operator]
        self.operation.query_chaincode(cc_query_operators)