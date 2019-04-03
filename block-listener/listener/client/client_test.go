/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/4/3 9:30
*/

package client

import (
	"fmt"
	"github.com/ParcelX/block-listener/listener/config"
	"github.com/ParcelX/block-listener/listener/printer"
	"testing"
	"time"
)

var channelConnections map[string]*ChannelConnection = nil

func getChannelConn(channelId string) *ChannelConnection {
	if channelConnections == nil {
		channelConnections = make(map[string]*ChannelConnection)
		listenCfg := config.NewListenCfgManagement("./config/listen-cfg.yaml")
		network := NewFabricNetwork(listenCfg.GetConfiguration().NetworkCfg.NetworkYamlPath, nil)
		for _, channel := range *listenCfg.GetChannels() {
			c := network.NewChannelConnection(&channel)
			channelConnections[channel.ChannelID] = c
		}
	}
	if c, ok := channelConnections[channelId]; ok {
		return c
	} else {
		panic(fmt.Sprintf("Counld not found channel id:  %s", channelId))
	}
}

func TestNewArgs(t *testing.T) {
	arg := NewArgs("a", "b", "2")
	for i, v := range arg.value {
		t.Log(i)
		t.Log(v)
	}
}

func TestInvokeCC(t *testing.T) {
	channelCoon := getChannelConn("channeldev1")
	ret, err := channelCoon.InvokeChainCode("example2", "set", NewArgs("b", "100"))
	if err != nil {
		t.Error(err)
	}
	t.Log(string(ret.Payload))
}

func TestQueryCC(t *testing.T) {
	channelCoon := getChannelConn("channeldev1")
	ret, err := channelCoon.QueryChainCode("example2", "query", NewArgs("a"))
	if err != nil {
		t.Error(err)
	}
	t.Log(string(ret.Payload))
}

func TestBlockEventListen(t *testing.T) {
	channelCoon := getChannelConn("channeldev1")
	blockReg, blockEventCh, err := channelCoon.RegisterBlockEvent()
	if err != nil {
		t.Error(err)
	}
	defer channelCoon.UnregisterBlockEvent(&blockReg)

	bp := printer.NewBlockPrinterWithOpts(printer.AsOutputFormat("display"),
		printer.AsWriterType("stdout"),
		&printer.FormatterOpts{Base64Encode: false})
	for {
		select {
		case e, ok := <-blockEventCh:
			if !ok {
				t.Fatal("unexpected closed channel while waiting for block event")
			}

			if e.Block == nil {
				t.Fatal("Expecting block in block event but got nil")
			} else {
				bp.PrintBlock(e.Block)
			}
		case <-time.After(time.Second * 20):
			t.Logf("Did NOT receive block event in 20s!")
			break
		}
	}
}
