#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/21 12:10
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""

import logging
import os
from pathlib import Path

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="INFO")
logger = logging.getLogger(__name__)
POSIX = lambda p: Path(p).as_posix()
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def convert_project_abs_path(path=None):
    """
    return project abspath, eg: D:\Files\project\github\ParcelX\Deployment\bootstrap
    """
    if path:
        return os.path.abspath(os.path.join(project_path, path))
    else:
        return os.path.abspath(project_path)


def format_org_name(org):
    """
    格式化 orgName  例如： orgabc => OrgAbc
    :param org: 
    :return:
    """
    if len(org) > 3 and org[:3].lower() == "org":
        return f"Org{org[3].upper()}{org[4:]}"
    else:
        return f"{org[0].upper()}{org[1:]}"


def format_org_msp_id(org):
    """
    格式化 orgName 转换为 orgID  例如： org2 => Org2MSP
    :param org:  org[...]
    :return:  Org{Upper[...]]MSP
    """
    if len(org) > 3:
        org_name = format_org_name(org)
        if org[-3:].lower() == "msp":
            return f"{org_name[:-3]}MSP"
        else:
            return f"{org_name}MSP"
    else:
        raise ValueError(f"Invalid org name {org}")


def format_org_domain(org):
    """
    格式化 orgName 转化为域名中使用或文件路径 例如： OrgEast/orgEast/orgEastMSP => orgEast
    :param org:  org[...]
    :return:  org{Upper[...]]
    """
    if len(org) > 3 and org[:3].lower() == "org":
        org_name = f"org{org[3].upper()}{org[4:]}"
        if org[-3:].lower() == "msp":
            return f"{org_name[:-3]}"
        else:
            return org_name
    else:
        raise ValueError("organization name format org[...]")


def split_value(value, sep=";"):
    """
    对参数进行分割出来， eg: "a;b;;c;" => ["a","b","c"]
    :param value:
    :param sep: 分割符
    :return:
    """
    if isinstance(value, str):
        items = value.strip(sep).split(sep)
        return [v for v in filter(lambda x: x not in(None, ""), items)]
    else:
        return []


def split_line(log):
    """
    分割线
    """
    log.info(f"*" * 45)
    log.info(f'{"-" * 20} Done {"-" * 20}')
    log.info(f"*" * 45)


def to_array(value, to_lower=True, param=""):
    """
    将字符串、数组转换为数组
    :param value: str / list<str>
    :param to_lower: 将所有成员变为小写， default: True
    :param param: 参数名称
    :return: list([str])
    """

    if not value:
        return []

    _v = value
    if not isinstance(value, (list, tuple)):
        if isinstance(value, str):
            _v = list([value])
        else:
            raise AttributeError(f"param '{param}' type must be tuple/list/str !")
    else:
        for item in value:
            if not isinstance(item, str):
                raise AttributeError(f"param '{param}' values must be str !")
    if to_lower:
        return list(map(lambda v: v.lower(), _v))
    else:
        return _v


class Dict2Obj(object):
    """
    Turns a dictionary into a class
    """
    def __init__(self, dictionary):
        """Constructor"""
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __repr__(self):
        """"""
        return "<Dict2Obj: %s>" % self.__dict__
