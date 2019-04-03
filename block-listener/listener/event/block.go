/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/3/27 17:10
*/

package event

import (
	"github.com/ParcelX/block-listener/listener/config"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/logging"
	"github.com/jasonlvhit/gocron"
)

func BlockListenerAction() {
	options := config.GetOptions()
	listenCfg := config.NewListenCfgManagement(options.ConfigFilepath)

	defer func() {
		if err := recover(); err != nil {
			listenCfg.GetLogger().Errorf("recover: %v", err)
		}
	}()
	// 开启定时记录
	gocron.Every(listenCfg.RecordEverySeconds()).Seconds().Do(recordChanged, listenCfg.GetLogger(), listenCfg)
	// 对 channel 建立 block 事件监听
	for _, channel := range *listenCfg.GetChannels() {
		go startBlockEventListener(channel.ChannelID, channel.FromBlockNum, listenCfg)
	}

	<-gocron.Start()
}

func recordChanged(logger *logging.Logger, lm *config.ListenCfgManagement) {
	logger.Infof("current channel block height: %v", *lm.GetChannels())
	lm.RecordChannelListenHeight()
}

func startBlockEventListener(channelId string, startFrom uint64, manager *config.ListenCfgManagement) {
	logger := logging.NewLogger(channelId)
	logger.Infof("start listen from %d", startFrom)
	manager.UpdateChannelBlockFromNum(channelId, startFrom+1)
}
