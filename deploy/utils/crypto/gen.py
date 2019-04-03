#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/2/14
@Author: ericw
@Email:  eric.wang@parcelx.io
"""

import os
import sys
from pathlib import Path
from ruamel.yaml import YAML
from utils import format_org_name, format_org_domain, format_org_msp_id

class ConfigCryptoGenerator(object):

    def __init__(self, outputPath, **fabric_network):
        self.yaml = YAML()
        self.yaml.indent(sequence=4, offset=2)
        self.fabric_network = fabric_network
        self.outputPath = outputPath
    
    def run(self):
        ordererOrgCfg = self.fabric_network["orderer_org"]
        orderOrgName = ordererOrgCfg["name"]
        orderOrgDomain = ordererOrgCfg["domain"]
        ordererOrg = dict(
            Name = format_org_name(orderOrgName),
            Domain = orderOrgDomain,
            CA = dict(
                Country = ordererOrgCfg.get('country', 'CN'),
                Province = ordererOrgCfg.get('province', 'Shanghai'),
                Locality = ordererOrgCfg.get('province', 'Shanghai')
            ),
            Specs = None,
            Users=dict(Count=1)
        )
        specs = []
        for index in range(len(self.fabric_network['orderer'])):
            specs.append(dict(Hostname = f'orderer{index}'))
        
        ordererOrg['Specs'] = specs
        # self.yaml.dump(ordererOrg, sys.stdout)

        peerOrgs = []
        for peerOrgName, peerOrgData in self.fabric_network["organization"].items():
            peerOrgDomain = peerOrgData.domain
            peerOrg = dict(
                Name = format_org_name(peerOrgName),
                Domain = peerOrgDomain,
                EnableNodeOUs = True,
                CA = dict(
                    Country = peerOrgData.country,
                    Province = peerOrgData.province,
                    Locality = peerOrgData.province
                ),
                Template = dict(Count = len(peerOrgData.peers)),
                Users = dict(Count = peerOrgData.usersCount)
            )
            peerOrgs.append(peerOrg)
        # self.yaml.dump(peerOrgs, sys.stdout)

        output = dict(
            OrdererOrgs = [ordererOrg],
            PeerOrgs = peerOrgs
        )
        # self.yaml.dump(output, sys.stdout)

        with open(self.outputPath, "w") as fp:
            self.yaml.dump(output, fp)
