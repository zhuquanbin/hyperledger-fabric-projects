#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
-------------------------------------------------
@Author :   luzhao
@Email :    zhao.lu@parcelx.io 
@DateTime ： 3/29/2019 7:44 PM
@Description :
-------------------------------------------------
"""

class Chaincode(object):

    def __init__(self, cc_name, cc_version):
        self.cc_name = cc_name
        self.cc_version = cc_version

    def is_empty(self):
        return not self.cc_name and not self.cc_version

    def is_in(self, chaincodes):
        for chaincode in chaincodes:
            if chaincode.cc_name == self.cc_name and chaincode.cc_version == self.cc_version:
                return True
        return False