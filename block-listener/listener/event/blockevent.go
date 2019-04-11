/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/3/27 17:10
*/

package event

import (
	"github.com/ParcelX/block-listener/listener/client"
	"github.com/ParcelX/block-listener/listener/config"
	"github.com/ParcelX/block-listener/listener/handler"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/logging"
	"github.com/jasonlvhit/gocron"
	"time"
)

func BlockListenerAction() {
	options := config.GetOptions()
	listenerContext := config.NewListenerContext(options.ConfigFilepath)

	defer func() {
		if err := recover(); err != nil {
			listenerContext.GetLogger().Errorf("recover: %v", err)
		}
	}()
	// 开启定时记录
	gocron.Every(listenerContext.RecordEverySeconds()).Seconds().Do(recordChanged, listenerContext.GetLogger(), listenerContext)

	// 对 channel 建立 block 事件监听
	network := client.NewFabricNetwork(listenerContext.GetConfiguration().NetworkCfg.NetworkYamlPath, listenerContext.GetLogger())
	channels := *listenerContext.GetChannels()
	for index, channel := range channels {
		listenerContext.GetLogger().Infof("create goroutine to listen channel: %v", channel)
		go startBlockEventListener(network, &channels[index], listenerContext)
	}

	<-gocron.Start()
}

func recordChanged(logger *logging.Logger, lm *config.ListenerContext) {
	logger.Infof("current channel block height: %v", *lm.GetChannels())
	lm.RecordChannelListenHeight()
}

func startBlockEventListener(network *client.FabricNetwork, channel *config.ListenChannel, context *config.ListenerContext) {
	logger := logging.NewLogger(channel.ChannelID)
	logger.Infof("start listen from %d", channel.FromBlockNum)

	conn := network.NewChannelConnection(channel)
	blockReg, blockEventCh, err := conn.RegisterBlockEvent()
	if err != nil {
		logger.Fatalln(err)
	}
	defer conn.UnregisterBlockEvent(&blockReg)

	blockHandler := handler.NewBlockHandler(context, logger)

	for {
		select {
		case e, ok := <-blockEventCh:
			if !ok {
				logger.Fatalln("unexpected closed channel while waiting for block event")
			}
			if e.Block == nil {
				logger.Error("Expecting block in block event but got nil")
			} else {
				// handle block
				blockHandler.Do(e.Block)

				// update channel block number
				context.UpdateChannelBlockFromNum(channel.ChannelID, e.Block.Header.GetNumber())
			}
		case <-time.After(time.Second * 300):
			logger.Warn("Did NOT receive block event in 300s!")
		}
	}
}
