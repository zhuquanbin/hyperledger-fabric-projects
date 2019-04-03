# 往Channel中添加组织测试

参考： https://hyperledger-fabric.readthedocs.io/en/release-1.4/channel_update_tutorial.html#adding-an-org-to-a-channel

- 装备 OrgWest 配置文件
```bash
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# cryptogen generate --config=./orgWest-crypto.yaml 
orgWest.parcelx.io
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# export FABRIC_CFG_PATH=$PWD && configtxgen -printOrg OrgWestMSP > orgwest.json
2019-02-02 15:13:13.399 CST [common.tools.configtxgen] main -> INFO 001 Loading configuration
2019-02-02 15:13:13.399 CST [common.tools.configtxgen.localconfig] LoadTopLevel -> INFO 002 Loaded configuration: /root/parcelx-fabric-dev/fabric-kafka/addorg/configtx.yaml
2019-02-02 15:13:13.400 CST [common.tools.configtxgen.encoder] NewOrdererOrgGroup -> WARN 003 Default policy emission is deprecated, please include policy specifications for the orderer org group OrgWestMSP in configtx.yaml

```

- 获取channel配置文件
```bash
# install jq tool
root@parcelx-1-1:~# apt install jq -y


# fetch channel config
root@parcelx-1-1:~/parcelx-fabric-dev# docker exec -it cli /bin/bash
root@399e462286f2:~# peer channel fetch config config_block.pb -o orderer0.parcelx.io -c parcelxdevchannel
2019-02-02 06:59:53.085 UTC [channelCmd] InitCmdFactory -> INFO 001 Endorser and orderer connections initialized
2019-02-02 06:59:53.090 UTC [cli.common] readBlock -> INFO 002 Received block: 137
2019-02-02 06:59:53.092 UTC [cli.common] readBlock -> INFO 003 Received block: 0


# pb to json
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator proto_decode --input config_block.pb --type common.Block > config_block.json
# get config from json file
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# cat config_block.json | jq .data.data[0].payload.data.config > config.json
```

- 添加组织
```bash
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# jq -s '.[0] * {"channel_group":{"groups":{"Application":{"groups": {"OrgWestMSP":.[1]}}}}}' config.json  orgwest.json > modified_config.json

# First, translate config.json back into a protobuf called config.pb:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator proto_encode --input config.json --type common.Config --output config.pb
# Next, encode modified_config.json to modified_config.pb:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator proto_encode --input modified_config.json --type common.Config --output modified_config.pb

# Now use configtxlator to calculate the delta between these two config protobufs. This command will output a new protobuf binary named org3_update.pb:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator compute_update --channel_id parcelxdevchannel --original config.pb --updated modified_config.pb --output orgwest_update.pb

# First, let’s decode this object into editable JSON format and call it org3_update.json:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator proto_decode --input orgwest_update.pb --type common.ConfigUpdate | jq . > orgwest_update.json

# Now, we have a decoded update file – org3_update.json – that we need to wrap in an envelope message. This step will give us back the header field that we stripped away earlier. We’ll name this file org3_update_in_envelope.json:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# echo '{"payload":{"header":{"channel_header":{"channel_id":"parcelxdevchannel", "type":2}},"data":{"config_update":'$(cat orgwest_update.json)'}}}' | jq . > orgwest_update_in_envelope.json

# Using our properly formed JSON – org3_update_in_envelope.json – we will leverage the configtxlator tool one last time and convert it into the fully fledged protobuf format that Fabric requires. We’ll name our final update object org3_update_in_envelope.pb:
root@parcelx-1-1:~/parcelx-fabric-dev/fabric-kafka/addorg# configtxlator proto_encode --input orgwest_update_in_envelope.json --type common.Envelope --output orgwest_update_in_envelope.pb
```
