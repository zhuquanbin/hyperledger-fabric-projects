The Python3 project for depolying ParcelX Hyper Ledger Fabric.
# Catalog
* [Requirements](#requirements)
* [Setup](#setup)
* [Commands](#commands)
    * [Integrated commands](#integrated-commands)
    * [Sub commands](#sub-commands)

# Requirements

* Python3
* pip3
* Fabric - more info at http://www.fabfile.org/

# Setup
* Make sure python3, pip3 are installed if they are not preloaded with your OS.
* Open a terminal window, go to the folder conatining this file, run "pip3 install --user -r requirements.txt"


# Commands
## Integrated-commands
```bash
Usage: fabric-install.py [options]

Options:
  -h, --help            show this help message and exit
  -d CONFIG_PATH, --directory=CONFIG_PATH
                        Hyperledger Fabric 配置文件所在目录, default: ./configs/
  --install             Hyperledger Fabric 部署
  --config=CONFIG_NAME  Hyperledger Fabric 配置文件名, default: deployment.yaml
  --extend              Hyperledger Fabric 扩展
  --extend-config=EXTEND_FILENAME
                        Hyperledger Fabric 网络扩展配置文件名
  --virtual-host        服务器是否为虚拟主机, 涉及 docker 网络部署模式
  --output=OUTPUT       配置文件输出结果目录,default: ./gen
  --clean-all           Hyperledger Fabric 网络节点清除操作

```
### usage
```bash
# 安装
python fabric-install.py --install --virtual-host

# 卸载
python fabric-install.py --clean-all

```
## sub-commands
```bash
Usage: fabfile.py [options]

Options:
  -h, --help            show this help message and exit
  -p                    根据Hyperledger Fabric配置文件生成docker-compose 和 scripts
  -r                    根据Hyperledger Fabric配置文件 crypto-config.yaml 生成 MSP
  -t                    根据Hyperledger Fabric配置文件 configtx.yaml 生成 Genesis
                        Block
  -s                    传输指定服务配置文件至远程服务器
  -i                    远程安装指定服务
  --chaincode           链码的创建和初始化

  Common Options:
    通用配置选项

    -d CONFIGPATH, --directory=CONFIGPATH
                        Hyperledger Fabric 配置文件所在目录, default: ./configs/
    -c CONFIGNAME, --config=CONFIGNAME
                        Hyperledger Fabric 配置文件名, default: deployment.yaml
    --output=OUTPUT     配置文件输出结果目录,default: ./gen

  Generate Options:
    生成Docker-Compose选项

    --gen               生成所有配置文件
    --virtual-host      服务器是否为虚拟主机, 涉及 docker 网络部署模式
    --zip               根据配置文件中服务器对应角色进行scp相应的zip包
    --zip-modules=ZIP_MODULES
                        指定服务项打包, eg: zookeeper;kafka , default:
                        zookeeper;kafka;orderer;peer;peer-cli
    --clean-compose     删除生成的 .sh 和 .yaml 文件
    --clean-zip         删除生成的 .zip 文件
    --show              列出所有 crypto-config & docker compose zip

  Crypto Options:
    生成配置文件选项

    --list-msp          列出已经创建的MSP
    --show-msp          展示所有组织信息
    --gen-crypto        生成Hyperledger Fabric MSP 根据配置文件
    --extend-crypto     扩展Hyperledger Fabric MSP 根据配置文件
    --add-org           添加组织选项
    --add-peer          添加节点选项
    --peer=PEERSNUM     添加的节点数

  ConfigTx Options:
    生成配置交易选项

    --list-config-tx    列出所有已经生成的创世区块
    --show-config-tx    展示配置文件中的创世块结构
    --system            生成System Orderer创世块
    --cfg-channel       配置Channel
    --gen-channel       生成Channel
    --ext-channel       扩展Channel
    --id=CHANNEL_ID     cfg/gen/ext channel 需填写 channel id, 必须为小写
    --org=ORGANIZATIONS
                        cfg/ext Channel 需填写加入channel的组织. eg: org1;org2

  Remote Copy Options:
    远程拷贝选项

    --scp-zip           根据配置文件中服务器对应角色进行scp相应的zip包
    --modules=SCP_MODULES
                        指定服务项拷贝, eg: zookeeper;kafka
    --scp-channel       拷贝指定的channel tx至指定的服务器
    --channel-name=CHANNEL_NAME
                        指定待拷贝的channel名, eg: dev1
    --remote-org=REMOTE_ORG
                        复制到指定组织下的所有节点上, eg: orgEast;不支持和 --remote-hosts 一起使用

  Install Options:
    安装服务选项

    --name=SERVICE      服务名, eg:
                        docker/zookeeper/kafka/orderer/peer/cli/explorer
    --install-org=INSTALL_ORG
                        安装组织下的所有节点, 仅支持服务: peer和peer-cli eg: orgeast; 不支持和
                        --remote-hosts 一起使用
    --remote-hosts=REMOTE_HOSTS
                        远程服务器IP地址, eg: 192.168.0.10;192.168.0.11
    --uninstall         卸载指定服务
    --reinstall         重新安装指定服务
    --detect            检查服务
    --clean-all         清空服务器所有docker container 脚本文件及映射目录
    
  Chaincode Options:
    链码操作选项
    
    --channel           指定操作的channel, 
                        eg:parcelxdevchannel, 适用类型: 链码安装,链码初始化和链码升级
    --peernames         指定链码操作的peernames, 
                        eg:peer0.orgEast.parcelx.io;peer1.orgEast.parcelx.io, 适用类型: 链码安装
    --peername          指定链码操作的peername, 
                        eg:peer0.orgEast.parcelx.io, 适用类型: 链码初始化和链码升级
    --chaincodenames    指定操作的chaincodenames, eg:example, 适用类型: 链码安装,链码初始化和链码升级
```

### usage
- 安装docker & docker-compose
```bash
# 安装
python fabfile.py -i --install-modules docker
# 检查
python fabfile.py -i --install-modules docker --detect
# 重新安装
python fabfile.py -i --install-modules docker --reinstall
```

- 生成证书
```bash
python fabfile.py -r --gen-crypto
```
- 生成运行脚本
```bash
python fabfile.py -p --gen --virtual-host
```

- 打包配置文件生成压缩包
```bash
python fabfile.py -p --zip
```

- 安装zookeeper & kafka
```bash
# 拷贝依赖
python fabfile.py -s --scp-zip --scp-modules  zookeeper;kafka

# 安装 注意: zookeeper > kafka 顺序
python fabfile.py -i --install-modules zookeeper;kafka

# 卸载
python fabfile.py -i --install-modules kafka;zookeeper --uninstall

# 重装
python fabfile.py -i --install-modules kafka;zookeeper --reinstall
```

- 生成排序节点创世块&拷贝至远程
```bash
# 生成排序节点创世块
python fabfile.py -t --system

# 拷贝
python fabfile.py -s --scp-channel --channel-name orderersystemchannel --remote-org orderer 
```

- 安装排序节点
```bash
# 拷贝
python fabfile.py -s --scp-zip --scp-modules orderer

# 安装
python fabfile.py -i --name orderer
```
- 安装组织
```bash
# 拷贝 peer and peer-cli 压缩包
python fabfile.py -s --scp-zip --scp-modules peer;peer-cli --remote-org orgeast
# 安装 peer and peer-cli
python fabfile.py -i --install-modules peer;peer-cli --install-org orgeast
# 检查服务
python fabfile.py -i --install-modules peer;peer-cli --install-org orgeast --detect

# 单台主机安装
# 拷贝 peer 压缩包
python fabfile.py -s --scp-zip --scp-modules peer --remote-org orgnorth --remote-host h10
# 安装 peer
python fabfile.py -i --install-modules peer --install-org orgnorth --remote-hosts h10

# 拷贝 peer-cli 压缩包
python fabfile.py -s --scp-zip --scp-modules peer-cli --remote-org orgnorth --remote-host h10
# 安装 peer-cli
python fabfile.py -i --install-modules peer-cli --install-org orgnorth --remote-hosts h10

```

- 创建channel
```bash
python fabfile.py -t --gen-channel --id parcelxdevchannel
```
- 拷贝channel至指定服务
```bash
python fabfile.py -s --scp-channel --channel-name parcelxdevchannel --remote-org orgeast;orgnorth
```
- 为组织添加指定 channel
```bash
python fabfile.py -c --install --id parcelxdevchannel
```


- 安装chaincode
```bash
python fabfile.py --chaincode --install --channel parcelxdevchannel --peernames peer0.orgEast.parcelx.io;peer1.orgEast.parcelx.io --chaincodenames parcel3;common1
```
- 初始化chaincode
```bash
python fabfile.py --chaincode --instantiate --channel parcelxdevchannel --peername peer0.orgEast.parcelx.io --chaincodenames parcel3;common1
```
- 升级chaincode
```bash
python fabfile.py --chaincode --upgrade --channel parcelxdevchannel --peername peer0.orgEast.parcelx.io --chaincodenames parcel3;common1
```