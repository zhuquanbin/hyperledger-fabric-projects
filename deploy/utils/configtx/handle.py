#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 15:26
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import uuid
import subprocess
from utils import format_org_msp_id
from utils.tool import FabricRelease
from .config import CustomChannel, ConfigTxConfigure


class ConfigTxHandler(object):
    """
    config tx handler:
        脚本运行所在的工作目录是在 ConfigTxConfigure.output 配置的目录下
        * 注意后续引用配置文件涉及的相对路径
        * Organizations MSP 在 ConfigTxConfigure.output + crypto-config 下， 即相对路径为 ./crypto-config
        * 设置 创世块配置文件目录 configtx/genesis
        * 设置 涉及通道配置文件目录 configtx/channels/<channel_name>
        * 设置 涉及组织证书json目录  configtx/orgs/
    """
    def __init__(self, release, configure):
        if isinstance(release, FabricRelease):
            self.release = release
        else:
            raise AttributeError("release type must be <utils.tool.FabricRelease>")

        if isinstance(configure, ConfigTxConfigure):
            self.configure = configure
        else:
            raise AttributeError("configure type must be <utils.configtxgen.ConfigTxConfigure>")

    def gen_orderer_genesis(self, channel=None):
        """
        生成 fabric 网络 排序节点的创世块
        :param channel:
        :return:
        """
        channel = self.configure.orderer_genesis if channel is None else channel
        if not isinstance(channel, CustomChannel):
            raise AttributeError(f"channel type must be <utils.configtxgen.config,CustomChannel>")

        ret = subprocess.run([
            self.release.configtxgen,
            "-outputBlock",
            self.configure.relative_path(channel.filepath),
            "-profile",
            channel.genesis_profile,
            "-channelID",
            channel.genesis_channel_id,
            # f"--config={self.configure.filepath}"
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()
        return ret

    def gen_channel_genesis(self, channel=None):
        """
        生成 fabric channel 创世块
        :param channel:
        :return:
        """
        if not channel and not isinstance(channel, CustomChannel):
            raise AttributeError(f"channel type must be <utils.configtxgen.config,CustomChannel>")

        ret = subprocess.run([
            self.release.configtxgen,
            "-outputCreateChannelTx",
            self.configure.relative_path(channel.filepath),
            "-profile",
            channel.genesis_profile,
            "-channelID",
            channel.genesis_channel_id,
            # "--configPath",
            # "./"  # self.configure.output
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()
        return ret

    def print_org(self, org):
        """
        打印出组织涉及证书配置信息
        :param org: 组织名
        :return: 组织对应的配置json文件路径
        """
        org_name = format_org_msp_id(org)
        ret = subprocess.run([
                    self.release.configtxgen,
                    "-printOrg",
                    org_name,
                    "--configPath",
                    "./"
                ],
                    stdout=subprocess.PIPE,
                    cwd=self.configure.output)
        ret.check_returncode()
        if ret.returncode == 0 and ret.stdout:
            filepath = self.configure.get_config_tx_org_path(f"{org_name}.json")
            with open(filepath, "w") as fp:
                print(ret.stdout.decode("utf-8"), file=fp)
            return filepath
        return None

    def fetch_configuration(self, pb_name, endpoint, channel_name, cafile, **env):
        """
        获取相应channel的配置文件 .pb
        Example Command:
            peer channel fetch config config_block.pb -o orderer.example.com:7050 -c $CHANNEL_NAME --tls --cafile $ORDERER_CA
        :param pb_name:
        :param endpoint: Ordering service endpoint
        :param channel_name: $CHANNEL_NAME
        :param cafile: Path to file containing PEM-encoded trusted certificate(s) for the ordering endpoint
        :return:
        """
        ret = subprocess.run([
            self.release.peer,
            "channel",
            "fetch",
            "config",
            pb_name,
            "-o",
            endpoint,
            "-c",
            channel_name,
            "--tls",
            "--cafile",
            cafile,
            # "--configPath",
            # "./"
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output,
            env=env)
        ret.check_returncode()
        return ret

    def remote_fetch_config_pb_cmd(self, domain, channel_name, orderer=None, capath=None):
        """
        远程执行命令， 获取相应channel的配置文件 .pb
        :param domain: 主机域名
        :param channel_name:
            channel name
        :param orderer:
            the domain of orderer0
        :param capath:
            orderer tls ca path
        :return: cmd and remote path
        """
        remote_pb = f"{channel_name}-{str(uuid.uuid4())[-12:]}.pb"
        if orderer and capath:
            fetch = f'peer channel fetch config {remote_pb} -c {channel_name} -o {orderer} --tls --cafile {capath}'
        else:
            fetch = f'peer channel fetch config {remote_pb} -c {channel_name}'
        remote_fetch_cmd = f'docker exec {domain} bash -c "' \
            f'cd /root/cli-data/ && ' \
            f'{fetch}"'
        return remote_fetch_cmd, f"/data/fabric/{domain.replace('-cli', '')}/cli-data/{remote_pb}"

    def remote_sign_channel_pb_cmd(self, envelope_file, domain):
        """
        远程执行命令， 签名相应的配置.pb
        :param envelope_file:
            the envelope filename of channel
        :param domain:
            the domain of the host'role

        :return: cmd and remote path
        """
        remote_sign_and_update = f'docker exec {domain} bash -c "' \
            f'cd /root/cli-data/ && ' \
            f'peer channel signconfigtx -f {envelope_file}"'
        return remote_sign_and_update, f"/data/fabric/{domain.replace('-cli', '')}/cli-data/"

    def remote_update_channel_pb_cmd(self, envelope_file, domain, channel_name, orderer, capath):
        """
        远程执行命令， 进行channel update
        :param envelope_file:
            the envelope filename of channel
        :param domain:
            the domain of the host'role
        :param channel_name:
            the name of channel
        :param orderer:
            the domain of orderer0
        :param capath:
            orderer tls ca path

        :return: cmd and remote path
        """
        remote_sign_and_update = f'docker exec {domain} bash -c "' \
            f'cd /root/cli-data/ && ' \
            f'peer channel update -f {envelope_file} -c {channel_name} -o {orderer} --tls true --cafile {capath}' \
            f'"'
        return remote_sign_and_update, f"/data/fabric/{domain.replace('-cli', '')}/cli-data/"

    def proto_encode(self, input_json, output_pb, encode_type="common.Config"):
        """
        转换 .json 到 .pb 文件
        Example Command:
            configtxlator proto_encode --input config.json --type common.Config --output config.pb
        :param input_json: json file path
        :param encode_type:
        :return: pb file path
        """
        # output_pb = f'{os.path.basename(input_json).split(".")[0]}.pb'
        ret = subprocess.run([
            self.release.configtxlator,
            "proto_encode",
            "--input",
            input_json,
            "--output",
            output_pb,
            "--type",
            encode_type
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()
        return ret

    def proto_decode(self, input_pb, output_json, decode_type="common.Block"):
        """
        转换 .pb 文件到json文件
        Example Command:
            configtxlator proto_decode --input config_block.pb --type common.Block | jq .data.data[0].payload.data.config > config.json
        :param input_pb:
        :param output_json:
        :param decode_type:
        :return:
        """
        # output_file = f'{os.path.basename(input_pb).split(".")[0]}.json'
        ret = subprocess.run([
            self.release.configtxlator,
            "proto_decode",
            "--input",
            input_pb,
            "--output",
            output_json,
            "--type",
            decode_type
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()
        return ret

    def compute_update(self, channel_name, original_pb, updated_pb, output_pb):
        """
        计算配置文件增量
        Example Command:
            configtxlator compute_update --channel_id $CHANNEL_NAME --original config.pb --updated modified_config.pb --output org3_update.pb
        :param channel_name:
        :param original_pb:
        :param updated_pb:
        :param output_pb:
        :return:
        """
        ret = subprocess.run([
            self.release.configtxlator,
            "compute_update",
            "--channel_id",
            channel_name,
            "--original",
            original_pb,
            "--updated",
            updated_pb,
            "--output",
            output_pb
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output)
        ret.check_returncode()
        return ret

    def channel_sign(self, org_update_in_envelope_pb, env=None):
        """
        channel 签名
        Without both signatures, the ordering service will reject the transaction for failing to fulfill the policy.
        参考: https://hyperledger-fabric.readthedocs.io/en/release-1.3/channel_update_tutorial.html#sign-and-submit-the-config-update
        Example Command:
            peer channel signconfigtx -f org3_update_in_envelope.pb

        :param org_update_in_envelope_pb:
        :param env:
        :return:
        """
        ret = subprocess.run([
            self.release.peer,
            "channel",
            "signconfigtx",
            "-f",
            org_update_in_envelope_pb
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output,
            env=env)
        ret.check_returncode()
        return ret

    def channel_join(self, channel_block, env=None):
        """
        channel 加入
        Example Command:
            peer channel join -b mychannel.block
        :param channel_block:
        :param env:
        :return:
        """
        ret = subprocess.run([
            self.release.peer,
            "channel",
            "join",
            "-b",
            channel_block
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output,
            env=env)
        ret.check_returncode()
        return ret

    def channel_update(self, org_update_in_envelope_pb, channel_name, endpoint, cafile, env=None):
        """
        channel 更新
        Example Command:
            peer channel update -f org3_update_in_envelope.pb -c $CHANNEL_NAME -o orderer.example.com:7050 --tls --cafile $ORDERER_CA
        :param org_update_in_envelope_pb: updated pb file path
        :param channel_name: $CHANNEL_NAME
        :param endpoint: Ordering service endpoint
        :param cafile: Path to file containing PEM-encoded trusted certificate(s) for the ordering endpoint
        :param env:
        :return:
        """
        ret = subprocess.run([
            self.release.peer,
            "channel",
            "update",
            "-f",
            org_update_in_envelope_pb,
            "-c",
            channel_name,
            "-o",
            endpoint,
            "--tls",
            "--cafile",
            cafile
        ],
            stdout=subprocess.PIPE,
            cwd=self.configure.output,
            env=env)
        ret.check_returncode()
        return ret

