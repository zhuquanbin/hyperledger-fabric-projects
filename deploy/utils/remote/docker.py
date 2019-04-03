#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Time:   2019/1/21 12:10
@Author: quanbin_zhu
@Email:  quanbin@parcelx.io
"""
import os
import tempfile
from utils.remote import SshHost


class Docker(object):
    bash = """#!/bin/bash
installDocker() {
    echo 'INFO: ready to Install docker!'
    sudo apt-get install apt-transport-https ca-certificates curl software-properties-common -y
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    sudo apt-get update && apt-get install docker-ce -y
}

installDockerCompose() {
    echo 'INFO: ready to Install docker-compose!'
    sudo curl -L "https://github.com/docker/compose/releases/download/1.23.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
}

main(){
    if ! [ -x "$(command -v docker)" ]
    then
        installDocker
    else
        echo 'INFO: docker had been installed!'    
    fi
    
    if ! [ -x "$(command -v docker-compose)" ]
    then
        installDockerCompose
    else
        if [ "$1" = "reinstall" ]; then
            echo 'INFO: docker-compose will be reinstalled!'
            sudo rm -f /usr/local/bin/docker-compose
            installDockerCompose
        else
            echo 'INFO: docker-compose had been installed!'
        fi
    fi
    docker -v
    docker-compose -v
}

main $*

"""

    def __init__(self):
        self.tempBashFile = None
        fp = tempfile.NamedTemporaryFile(mode='w', prefix='docker', suffix='.sh', encoding='utf-8', delete=False)
        self.tempBashFile = fp.name
        fp.close()

        with open(self.tempBashFile, "wb") as bf:
            bf.write(bytes(Docker.bash, "utf8"))

    def install(self, remote_ssh, reinstall=False, **kwargs):
        if isinstance(remote_ssh, SshHost):
            filename = os.path.basename(self.tempBashFile)
            remote_ssh.upload(self.tempBashFile, "/tmp/")
            if reinstall:
                remote_ssh.sudo(f"sh /tmp/{filename} reinstall", )
            else:
                remote_ssh.sudo(f"sh /tmp/{filename}")
            remote_ssh.sudo(f"rm -f /tmp/{filename}")

        if self.tempBashFile and os.path.exists(self.tempBashFile):
            os.remove(self.tempBashFile)
