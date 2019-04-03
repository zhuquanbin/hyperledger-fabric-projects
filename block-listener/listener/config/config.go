/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/3/27 15:59
*/

package config

import (
	"fmt"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/logging"
	"gopkg.in/yaml.v2"
	"io/ioutil"
	"os"
)

var logger = logging.NewLogger("listener")

type Configuration struct {
	NetworkCfg     CryptoConfig    `yaml:"crypto"`
	Record         ChannelRecord   `yaml:"record"`
	ListenChannels []ListenChannel `yaml:"listen-channels"`
}

type CryptoConfig struct {
	CryptoConfigPath string `yaml:"crypto-config-path"`
	NetworkYamlPath  string `yaml:"network-yaml-path"`
}
type ListenChannel struct {
	ChannelID    string `yaml:"id"`
	OrgName      string `yaml:"org"`
	OrgUser      string `yaml:"user"`
	FromBlockNum uint64 `yaml:"from"`
}

type ChannelRecord struct {
	Seconds  uint64 `yaml:"seconds"`
	DataPath string `yaml:"data-path"`
}

type ListenCfgManagement struct {
	cfg      Configuration   // yaml 配置
	index    map[string]int  // channel 索引
	logger   *logging.Logger // fabric sdk go logging
	filepath string          // the path of config
}

func (c *Configuration) initConfig() {
	// set env
	if err := os.Setenv("CRYPTO_CONFIG_PATH", c.NetworkCfg.CryptoConfigPath); err != nil {
		logger.Fatalln(err)
	}

	// load record data and merge
	if data, err := ioutil.ReadFile(c.Record.DataPath); err != nil {
		if e, ok := err.(*os.PathError); ok {
			logger.Warn(e)
		} else {
			logger.Fatalln(err)
		}
	} else {
		var lcs []ListenChannel
		if err := yaml.Unmarshal(data, &lcs); err != nil {
			logger.Fatalln(err)
		}

		// read record
		_record := make(map[string]uint64)
		for _, v := range lcs {
			_record[v.ChannelID] = v.FromBlockNum
		}
		// set the max height for channel listener
		for i, v := range c.ListenChannels {
			if n, ok := _record[v.ChannelID]; ok {
				if n > v.FromBlockNum {
					c.ListenChannels[i].FromBlockNum = n
				}
			}
		}
	}
}

func NewListenCfgManagement(yamlPath string) *ListenCfgManagement {

	if data, err := ioutil.ReadFile(yamlPath); err != nil {
		logger.Fatalf("%s %v",yamlPath, err)
	} else {
		lm := ListenCfgManagement{
			filepath: yamlPath,
			logger:   logger,
		}
		if err := yaml.Unmarshal(data, &lm.cfg); err != nil {
			logger.Fatalln(err)
		}

		lm.cfg.initConfig()

		lm.index = make(map[string]int)
		for i, v := range lm.cfg.ListenChannels {
			lm.index[v.ChannelID] = i
		}
		return &lm
	}
	return nil
}

func (m *ListenCfgManagement) GetConfiguration() *Configuration {
	return &m.cfg
}

func (m *ListenCfgManagement) GetChannels() *[]ListenChannel {
	return &m.cfg.ListenChannels
}


func (m *ListenCfgManagement) UpdateChannelBlockFromNum(channel string, num uint64) {
	if index, ok := m.index[channel]; ok {
		m.cfg.ListenChannels[index].FromBlockNum = num
	} else {
		panic(fmt.Sprintf("channel: %s not exist!", channel))
	}
}

func (m *ListenCfgManagement) RecordChannelListenHeight() {
	if bArray, err := yaml.Marshal(m.cfg.ListenChannels); err != nil {
		panic(fmt.Sprintf("dump config error: %v", err))
	} else {
		if wErr := ioutil.WriteFile(m.cfg.Record.DataPath, bArray, 0666); wErr != nil {
			panic(fmt.Sprintf("write config file error: %v", wErr))
		}
	}
}

func (m *ListenCfgManagement) GetLogger() *logging.Logger {
	return m.logger
}

func (m *ListenCfgManagement) RecordEverySeconds() uint64 {
	if m.cfg.Record.Seconds < 3 {
		panic("The record interval is preferably greater than 3 seconds!")
	}
	return m.cfg.Record.Seconds
}
