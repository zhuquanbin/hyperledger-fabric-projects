#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/23 14:35
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import platform
import wget
import tarfile

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
TEMP_PATH = os.path.join(BASE_PATH, "_tmp")
FABRIC_BINARIES_RELEASE = "https://nexus.hyperledger.org/content/repositories/releases/org/hyperledger/fabric/hyperledger-fabric/"
SUPPORTED_FABRIC_VERSIONS = ["1.3.0", "1.4.0"]

class FabricRelease(object):
    PEER = "peer"
    CONFIGTXGEN = "configtxgen"
    CRYPTOGEN = "cryptogen"
    CONFIGTXLATOR = "configtxlator"

    def __init__(self, release, auto=False):
        """
        :param release:  fabric release version, example: 1.3.0 or 1.4.0
        :param auto:  auto download fabric release binaries version
        """
        self.isWindows = False
        self.isMac = False
        self.isLinux = False

        platformName = platform.system().lower()
        if "windows" == platformName:
            self.isWindows = True
        elif "darwin" == platformName:
            self.isMac = True
        elif "linux" == platformName:
            self.isLinux = True
        else:
            raise NotImplementedError(f"Platform not supported: {platformName}")

        if release not in SUPPORTED_FABRIC_VERSIONS:
            raise NotImplementedError(f"Fabric release version not supported: {release}")

        self.extensionForExe = ".exe" if self.isWindows else ""
        self.release = release
        self.release_path = os.path.join(BASE_PATH, platformName, self.release)
        self.bin_path = os.path.join(self.release_path, "bin")
        if auto and not self.is_exist_binaries():
            self.download_binaries_release()

    @property
    def peer(self):
        return os.path.join(self.bin_path, f"{FabricRelease.PEER}{self.extensionForExe}") 

    @property
    def configtxgen(self):
        return os.path.join(self.bin_path, f"{FabricRelease.CONFIGTXGEN}{self.extensionForExe}")

    @property
    def cryptogen(self):
        return os.path.join(self.bin_path, f"{FabricRelease.CRYPTOGEN}{self.extensionForExe}") 

    @property
    def configtxlator(self):
        return os.path.join(self.bin_path, f"{FabricRelease.CONFIGTXLATOR}{self.extensionForExe}") 

    def is_exist_binaries(self):
        return os.path.isfile(self.cryptogen) \
               and os.path.isfile(self.peer) \
               and os.path.isfile(self.configtxgen)

    def extract_zip(self, filename, dest="."):
        print(f"extracting fabric binaries to: {self.release_path} from: {filename}")
        if filename.endswith(".tar.gz"):
            mode = "r|gz"
        else:
            raise NotImplementedError(f"Do not support unzip {filename} type!")
        with tarfile.open(filename, mode) as fp:
            for member in fp:
                if not member.name.startswith("bin"):
                    continue
                fp.extract(member, dest)
                _src = os.path.join(dest, member.name)
                print(f"extracting: {_src}")

                # append extension for executables as needed
                if len(self.extensionForExe) > 0 and not member.isdir() and not _src.endswith(".sh"):
                    _dest = f"{_src}{self.extensionForExe}"
                    os.rename(_src, _dest)
                
    def __get_release_binaries_path(self):
        platformName = platform.system().lower()
        return f"{FABRIC_BINARIES_RELEASE}{platformName}-amd64-{self.release}/hyperledger-fabric-{platformName}-amd64-{self.release}.tar.gz"

    def download_binaries_release(self):
        if self.is_exist_binaries():
            return

        fabric_binaries_path =  self.__get_release_binaries_path()
        download_filename = os.path.basename(fabric_binaries_path)
        filename = os.path.join(TEMP_PATH, download_filename)
        # download to temp directory
        if not os.path.exists(TEMP_PATH):
            os.mkdir(TEMP_PATH)
        
        print(f"checking fabric binaries at location: {filename}")
        if not os.path.exists(filename):
            print(f"downloading fabric binaries: {fabric_binaries_path}")
            wget.download(fabric_binaries_path, TEMP_PATH)
        else:
            print(f"skip downloading fabric binaries")

        # extract fabric binaries from tar file
        self.extract_zip(filename, self.release_path)


if __name__ == "__main__":
    FabricRelease("1.3.0").download_binaries_release()
