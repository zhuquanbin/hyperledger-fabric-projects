#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
@Author :   luzhao
@Email :    zhao.lu@parcelx.io
@DateTime ： 2/28/2019 1:05 PM
@Description :
-------------------------------------------------
"""
import json
import logging
import time

from hfc.fabric.transaction.tx_context import create_tx_context
from hfc.fabric.transaction.tx_proposal_request import create_tx_prop_req, CC_UPGRADE, CC_TYPE_GOLANG, TXProposalRequest
from hfc.util import utils
from hfc.util.crypto.crypto import ecies

from utils.chaincode.bean import Chaincode

_logger = logging.getLogger(__name__)

"""
produce existed channel only
"""

logger = logging.getLogger(__name__)


class ChannelUtil(object):
    def __init__(self, client):
        self.client = client

    def channel_create(self, orderer_name, channel_name):
        if self.client.get_channel(channel_name):
            _logger.warning("channel {} already existed when creating".format(
                channel_name))
            return True
        orderer = self.client.get_orderer(orderer_name)
        if not orderer:
            _logger.error("No orderer_name instance found with name {}".format(
                orderer_name))
            return False
        self.client.new_channel(channel_name)


def reproduce_channel(networkconfig, client):
    """
    for every channel in channels section of config file
    :return:
    """
    for per_channel_name, per_channel_value in networkconfig["channels"].items():
        per_exist_channel = client.new_channel(per_channel_name)

        for per_orderer_name in per_channel_value.get("orderers"):
            per_exist_channel.add_orderer(client.get_orderer(per_orderer_name))

        for per_peer_name, per_peer_value in per_channel_value.get("peers").items():
            per_exist_channel.add_peer(client.get_peer(per_peer_name))


def install_chaincode(client, requestor, peer_names, cc_path, cc_name, cc_version):
    chaincodes = query_chaincode(client, requestor, peer_names)
    chaincode = Chaincode(cc_name, cc_version)
    if chaincode.is_in(chaincodes):
        logger.info(f"{json.dumps(peer_names)} has installed {cc_name}.{cc_version}.")
        return True

    response = client.chaincode_install(
        requestor=requestor,
        peers=peer_names,
        cc_path=cc_path,
        cc_name=cc_name,
        cc_version=cc_version
    )
    tran_req = utils.build_tx_req(response)
    if not (tran_req.responses[0].response.status == 200):
        logger.info(f"{json.dumps(peer_names)} install {cc_name}.{cc_version} failed.")
        return False

    logger.info(f"{json.dumps(peer_names)} install {cc_name}.{cc_version} successfully.")
    return True


def upgrade_chaincode(client, requestor, channel_name, peer_names, args, cc_name, cc_version, timeout = 100):
    """
    upgrade chaincode
    :param channel:
    :param org_admin:
    :param cc_name:
    :param cc_version:
    :param args:
    :return:
    """
    tran_prop_req_upg = create_tx_prop_req(
        prop_type= CC_UPGRADE,
        cc_type=CC_TYPE_GOLANG,
        cc_name=cc_name,
        cc_version=cc_version,
        args=args,
        fcn='init')

    crypto = ecies()

    # get
    peers = [client.get_peer(peer_name) for peer_name in peer_names]

    # deploy the chain code
    tx_context_dep = create_tx_context(requestor,
                                       crypto,
                                       tran_prop_req_upg)
    res = client.get_channel(channel_name).send_upgrade_proposal(tx_context_dep, peers)
    tx_context =  create_tx_context(requestor,
                                       requestor.cryptoSuite,
                                       TXProposalRequest())
    tran_req = utils.build_tx_req(res)

    responses = utils.send_transaction(client.orderers, tran_req, tx_context)
    if not (tran_req.responses[0].response.status == 200
            and responses[0].status == 200):
        logger.info(f"{json.dumps(peer_names)} upgrade {cc_name}.{cc_version} failed.")
        return False
    # Wait until chaincode is really instantiated
    # Note : we will remove this part when we have channel event hub
    starttime = int(time.time())
    while int(time.time()) - starttime < timeout:
        try:
            response = client.query_transaction(
                requestor=requestor,
                channel_name=channel_name,
                peers=peers,
                tx_id=tx_context_dep.tx_id,
                decode=False
            )

            if response.response.status == 200:
                logger.info(f"{json.dumps(peer_names)} upgrade {cc_name}.{cc_version} successfully.")
                return True

            time.sleep(1)
        except Exception:
            time.sleep(1)

    logger.info(f"{json.dumps(peer_names)} upgrade {cc_name}.{cc_version} failed.")
    return False


def query_chaincode(client, requestor, peer_names):
    """
    use the requestor user to query chaincodes installed from peer_names
    :param client:
    :param requestor:
    :param peer_names:
    :return:
    """
    query_trans = client.query_installed_chaincodes(requestor, peer_names)

    chaincodes = []
    for cc in query_trans.chaincodes:
        logger.debug('cc name {}, version {} from peer {}'.format(
            cc.name, cc.version, json.dumps(peer_names)))
        chaincodes.append(Chaincode(cc.name, cc.version))
    return chaincodes
