#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/2/27 15:42
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import logging
from optparse import OptionParser
from utils.configuration import Configuration, ExtendConfiguration
from utils.context import DeployContext

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-d", "--directory", dest="config_path", default="./configs/",
                      help="Hyperledger Fabric 配置文件所在目录, default: ./configs/")
    parser.add_option("--install", action="store_true", dest="install", help="Hyperledger Fabric 部署")
    parser.add_option("--config", dest="config_name", default="deployment.yaml",
                      help="Hyperledger Fabric 配置文件名, default: deployment.yaml")
    parser.add_option("--extend", action="store_true", dest="extend", help="Hyperledger Fabric 扩展")
    parser.add_option("--extend-config", dest="extend_filename", default="extend.yaml",
                      help="Hyperledger Fabric 网络扩展配置文件名, default: extend.yaml")
    parser.add_option("--virtual-host", action="store_true", dest="virtual_host",
                      help="服务器是否为虚拟主机, 涉及 docker 网络部署模式")
    parser.add_option("--output", dest="output", default="./gen", help="配置文件输出结果目录,default: ./gen")
    parser.add_option("--gen-sdk-yaml", action="store_true", dest="gen_sdk_yaml",
                      help="Hyperledger Fabric Go SDK Client 配置文件生成")
    parser.add_option("--org-name", dest="sdk_org", help="Hyperledger Fabric Go SDK Client 配置的组织")
    parser.add_option("--clean-all", action="store_true", dest="clean_all", help="Hyperledger Fabric 网络节点清除操作")

    options, args = parser.parse_args()

    deploy = DeployContext(cfg=Configuration(options.config_path, options.config_name, configOutPath=options.output),
                           ext=ExtendConfiguration(options.config_path, options.extend_filename),
                           virtual_host=options.virtual_host)

    try:
        if options.install:
            logger.info(f"[*] Begin to deploy fabric network, configuration depends on: {options.config_name}.")
            deploy.load_network()
            deploy.onekey_deploy()
        elif options.extend and options.extend_filename:
            logger.info(f"[*] Begin to extend fabric network, configuration depends on: {options.extend_filename}.")
            deploy.load_extend()
            deploy.onekey_extend()
            deploy.merge_yaml()
        elif options.gen_sdk_yaml and options.sdk_org:
            logger.info(f"[*] Begin to generate go sdk config yaml, client<{options.sdk_org}>.")
            deploy.load_network()
            deploy.gen_go_sdk_yaml(options.sdk_org)
        elif options.clean_all:
            flag = input("✘ Clear all server deployment scripts, run containers, and mount directories [N/y]:")
            if flag.lower() == "y":
                logger.info(f"[*] Begin to clean fabric network services and output files.")
                deploy.load_network()
                deploy.clean_all()
        else:
            parser.print_help()

    except Exception as e:
        logger.error(e, exc_info=True)
