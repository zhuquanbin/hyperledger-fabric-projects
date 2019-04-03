/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/4/1 16:40
*/

package client

import (
	"fmt"
	listenercfg "github.com/ParcelX/block-listener/listener/config"
	"github.com/hyperledger/fabric-sdk-go/pkg/client/channel"
	"github.com/hyperledger/fabric-sdk-go/pkg/client/event"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/errors/retry"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/logging"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/providers/fab"
	"github.com/hyperledger/fabric-sdk-go/pkg/core/config"
	"github.com/hyperledger/fabric-sdk-go/pkg/fab/events/deliverclient/seek"
	"github.com/hyperledger/fabric-sdk-go/pkg/fabsdk"
)

type FabricNetwork struct {
	fabricSdk *fabsdk.FabricSDK
	logger    *logging.Logger
}

type ChannelConnection struct {
	client *channel.Client
	event  *event.Client
}

func NewFabricNetwork(yamlConf string, logger *logging.Logger) *FabricNetwork {
	var log = logger
	if log == nil {
		log = logging.NewLogger("fabric-network")
	}
	configOpt := config.FromFile(yamlConf)
	sdk, err := fabsdk.New(configOpt)
	if err != nil {
		log.Fatalf("Failed to create new fabric sdk: %v", err)
	}
	return &FabricNetwork{fabricSdk: sdk, logger: log}
}

func (net *FabricNetwork) NewChannelConnection(cfg *listenercfg.ListenChannel) *ChannelConnection {
	// prepare channel client context
	channelClientContext := net.fabricSdk.ChannelContext(
		cfg.ChannelID,
		fabsdk.WithUser(cfg.OrgUser),
		fabsdk.WithOrg(cfg.OrgName))

	// get channel client (used to generate transactions)
	chClient, err := channel.New(channelClientContext)
	if err != nil {
		net.logger.Fatalf("Failed to create new channel client: %s", err)
	}

	// create event client with block events
	eventClient, err := event.New(
		channelClientContext,
		event.WithBlockEvents(),
		event.WithSeekType(seek.FromBlock),
		event.WithBlockNum(cfg.FromBlockNum))
	if err != nil {
		net.logger.Fatalf("Failed to create new events client with block events: %s", err)
	}

	return &ChannelConnection{chClient, eventClient}
}

type mockDiscoveryFilter struct {
	called bool
}

// Accept returns true if this peer is to be included in the target list
func (df *mockDiscoveryFilter) Accept(peer fab.Peer) bool {
	df.called = true
	return true
}

// ChainCode args struct
type ChainCodeInvokeArgs struct {
	value [][]byte
}

func NewArgs(args ...interface{}) *ChainCodeInvokeArgs {
	ccArgs := make([][]byte, len(args))
	for i, arg := range args {
		switch t := arg.(type) {
		case string:
			ccArgs[i] = []byte(t)
		case []byte:
			ccArgs[i] = t
		default:
			panic(fmt.Sprintf("chaincode do not support args type: %T", arg))
		}
	}
	return &ChainCodeInvokeArgs{value: ccArgs}
}

func (cc *ChannelConnection) QueryChainCode(chainCodeID, method string, ccArg *ChainCodeInvokeArgs) (*channel.Response, error) {
	discoveryFilter := &mockDiscoveryFilter{called: false}
	response, err := cc.client.Query(
		channel.Request{
			ChaincodeID: chainCodeID,
			Fcn:         method,
			Args:        ccArg.value},
		channel.WithTargetFilter(discoveryFilter),
		channel.WithRetry(retry.DefaultChannelOpts))

	return &response, err
}

func (cc *ChannelConnection) InvokeChainCode(chainCodeID, method string, ccArg *ChainCodeInvokeArgs) (*channel.Response, error) {
	response, err := cc.client.Execute(
		channel.Request{
			ChaincodeID: chainCodeID,
			Fcn:         method,
			Args:        ccArg.value},
		channel.WithRetry(retry.DefaultChannelOpts))
	return &response, err
}

func (cc *ChannelConnection) RegisterBlockEvent() (fab.Registration, <-chan *fab.BlockEvent, error) {
	return cc.event.RegisterBlockEvent()
}

func (cc *ChannelConnection) UnregisterBlockEvent(blockReg fab.Registration) {
	cc.event.Unregister(blockReg)
}
