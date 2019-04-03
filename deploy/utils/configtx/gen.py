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
from collections import OrderedDict
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from utils import format_org_name, format_org_domain, format_org_msp_id

OrganizationsComment = """
# Copyright IBM Corp. All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

---
################################################################################
#
#   Section: Organizations
#
#   - This section defines the different organizational identities which will
#   be referenced later in the configuration.
#
################################################################################
"""

CapabilitiesComment = """
################################################################################
#
#   SECTION: Capabilities
#
################################################################################
"""
ApplicationComment = """
################################################################################
#
#   SECTION: Application
#
#   - This section defines the values to encode into a config transaction or
#   genesis block for application related parameters
#
################################################################################
"""
OrdererComment = """
################################################################################
#
#   SECTION: Orderer
#
#   - This section defines the values to encode into a config transaction or
#   genesis block for orderer related parameters
#
################################################################################
"""
ChannelComment = """
################################################################################
#
#   CHANNEL
#
#   This section defines the values to encode into a config transaction or
#   genesis block for channel related parameters.
#
################################################################################
"""
ProfilesComment = """
################################################################################
#
#   Profile
#
#   - Different configuration profiles may be encoded here to be specified
#   as parameters to the configtxgen tool
#
################################################################################
"""


class ConfigTxGenerator(object):

    def __init__(self, outputPath, **fabric_network):
        self.yaml = YAML()
        self.yaml.indent(mapping=4, sequence=4, offset=2)
        self.fabric_network = fabric_network
        self.outputPath = outputPath

    def run(self):
        config = CommentedMap()
        # 1 Organizations
        organizations = CommentedSeq()
        # 1.1 Orderer
        orderer_org_cfg = self.fabric_network["orderer_org"]
        orderer_name = orderer_org_cfg["name"]
        orderer_domain = orderer_org_cfg["domain"]
        orderer_org_id = format_org_msp_id(orderer_name)
        orderer_org = CommentedMap(
            Name="OrdererOrg",
            ID=orderer_org_id,
            MSPDir=f"crypto-config/ordererOrganizations/{orderer_domain}/msp",
            Policies=CommentedMap(
                Readers=CommentedMap(
                    Type="Signature",
                    Rule=f"OR('{orderer_org_id}.member')"
                ),
                Writers=CommentedMap(
                    Type="Signature",
                    Rule=f"OR('{orderer_org_id}.member')"
                ),
                Admins=CommentedMap(
                    Type="Signature",
                    Rule=f"OR('{orderer_org_id}.admin')"
                )
            )
        )
        orderer_org.yaml_set_anchor(orderer_org["Name"], True)
        organizations.append(orderer_org)

        # 1.2 Add Org
        org_anchor_map = OrderedDict()
        for peerOrgName, peerOrgData in self.fabric_network["organization"].items():
            peer_org_domain = peerOrgData.domain
            peer_org_msp = format_org_msp_id(peerOrgName)
            peer_org = CommentedMap(
                Name=peer_org_msp,
                ID=peer_org_msp,
                MSPDir=f"crypto-config/peerOrganizations/{peer_org_domain}/msp",
                Policies=CommentedMap(
                    Readers=CommentedMap(
                        Type="Signature",
                        Rule=f"OR('{peer_org_msp}.admin', '{peer_org_msp}.peer', '{peer_org_msp}.client')"
                    ),
                    Writers=CommentedMap(
                        Type="Signature",
                        Rule=f"OR('{peer_org_msp}.admin', '{peer_org_msp}.client')"
                    ),
                    Admins=CommentedMap(
                        Type="Signature",
                        Rule=f"OR('{peer_org_msp}.admin')"
                    )
                ),
                AnchorPeers=CommentedSeq([
                    CommentedMap(
                        Host=f"peer0.{peer_org_domain}",
                        Port=7051)])
            )

            orgName = format_org_name(peerOrgName)
            peer_org.yaml_set_anchor(orgName, True)
            org_anchor_map[orgName] = peer_org
            organizations.append(peer_org)

        config["Organizations"] = organizations

        # 2. Capabilities
        capabilities = CommentedMap(
            Global=CommentedMap(V1_1=True),
            Orderer=CommentedMap(V1_1=True),
            Application=CommentedMap(V1_2=True)
        )
        capabilities["Global"].yaml_set_anchor("ChannelCapabilities", True)
        capabilities["Orderer"].yaml_set_anchor("OrdererCapabilities", True)
        capabilities["Application"].yaml_set_anchor("ApplicationCapabilities", True)
        config["Capabilities"] = capabilities

        # 3. Application
        application = CommentedMap(
            Organizations=None,
            Policies=CommentedMap(
                Readers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Readers"
                ),
                Writers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Writers"
                ),
                Admins=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="MAJORITY Admins"
                )
            ),
            Capabilities=CommentedMap()
        )
        application["Capabilities"].merge.extend([(0, capabilities["Application"])])
        application.yaml_set_anchor("ApplicationDefaults")
        config["Application"] = application

        # 4. Orderer
        orderer = CommentedMap(
            OrdererType='kafka',
            Addresses=CommentedSeq(list(map(lambda d: f"{d}:7050", self.fabric_network["orderer"].values()))),
            BatchTimeout='5s',
            BatchSize=CommentedMap(
                MaxMessageCount=200,
                AbsoluteMaxBytes='98 MB',
                PreferredMaxBytes='512 KB',
            ),
            Kafka=CommentedMap(
                # Brokers: A list of Kafka brokers to which the orderer connects. Edit
                # this list to identify the brokers of the ordering service.
                # NOTE: Use IP:port notation.
                Brokers=CommentedSeq(list(map(lambda d: f"{d}:9092", self.fabric_network["kafka"].values())))
            ),
            Organizations=None,
            Policies=CommentedMap(
                Readers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Readers"
                ),
                Writers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Writers"
                ),
                Admins=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="MAJORITY Admins"
                ),
                BlockValidation=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Writers"
                )
            ),
            Capabilities=CommentedMap()
        )
        orderer["Capabilities"].merge.extend([(0, capabilities["Orderer"])])
        orderer.yaml_set_anchor("OrdererDefaults", True)
        config["Orderer"] = orderer

        # 5. Channel
        channel = CommentedMap(
            Policies=CommentedMap(
                Readers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Readers"
                ),
                Writers=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="ANY Writers"
                ),
                Admins=CommentedMap(
                    Type="ImplicitMeta",
                    Rule="MAJORITY Admins"
                )
            ),
            Capabilities=CommentedMap()
        )
        channel["Capabilities"].merge.extend([(0, capabilities["Global"])])
        channel.yaml_set_anchor("ChannelDefaults", True)
        config["Channel"] = channel

        # 6. Profiles
        profiles = CommentedMap()
        profiles[self.fabric_network["genesis"]] = CommentedMap()
        system_genesis = profiles[self.fabric_network["genesis"]]
        system_genesis.merge.extend([(0, config["Channel"])])
        system_genesis["Orderer"] = CommentedMap()
        system_genesis["Orderer"].merge.extend([(0, orderer)])
        system_genesis["Orderer"]["Organizations"] = CommentedSeq([orderer_org])

        system_genesis["Consortiums"] = CommentedMap()
        consortiums = system_genesis["Consortiums"]
        for _, channel_cfg in self.fabric_network['channels'].items():
            org_seq = CommentedSeq()
            for org_name in channel_cfg['orgs']:
                org_seq.append(org_anchor_map[format_org_name(org_name)])
            consortiums[channel_cfg["consortium"]] = CommentedMap(
                Organizations=org_seq
            )
            # profiles[channel_cfg["profile"]] = CommentedMap()
            channel_application = CommentedMap()
            channel_application.merge.extend([(0, application)])
            channel_application["Organizations"] = org_seq.copy()
            profiles[channel_cfg["profile"]] = CommentedMap(
                Consortium=channel_cfg["consortium"],
                Application=channel_application,
            )

        config["Profiles"] = profiles

        config.yaml_set_comment_before_after_key('Organizations', OrganizationsComment, after_indent=2)
        config.yaml_set_comment_before_after_key('Capabilities', CapabilitiesComment, after_indent=2)
        config.yaml_set_comment_before_after_key('Application', ApplicationComment, after_indent=2)
        config.yaml_set_comment_before_after_key('Orderer', OrdererComment, after_indent=2)
        config.yaml_set_comment_before_after_key('Channel', ChannelComment, after_indent=2)
        config.yaml_set_comment_before_after_key('Profiles', ProfilesComment, after_indent=2)

        with open(self.outputPath, "w") as fp:
            self.yaml.dump(config, fp)
