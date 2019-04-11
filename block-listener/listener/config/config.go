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
	"net/url"
	"os"
	"path"
)

var logger = logging.NewLogger("listener")

// the struct of the listen-cfg.yaml config
type Configuration struct {
	NetworkCfg     CryptoConfig    `yaml:"crypto"`
	Record         ChannelRecord   `yaml:"record"`
	ThirdService   ThirdService    `yaml:"third-service"`
	ListenChannels []ListenChannel `yaml:"listen-channels"`
}

// the path of th crypto-config yaml
type CryptoConfig struct {
	CryptoConfigPath string `yaml:"crypto-config-path"`
	NetworkYamlPath  string `yaml:"network-yaml-path"`
}

// listen channels configuration
type ListenChannel struct {
	ChannelID    string `yaml:"id"`
	OrgName      string `yaml:"org"`
	OrgUser      string `yaml:"user"`
	FromBlockNum uint64 `yaml:"from"`
}

// the service of transaction handing's configuration
type ThirdService struct {
	Url     string            `yaml:"url"`
	Version string            `yaml:"version"`
	Methods map[string]string `yaml:"methods"`
}

// the record of the channel block listens to
type ChannelRecord struct {
	Seconds  uint64 `yaml:"seconds"`
	DataPath string `yaml:"data-path"`
}

// the config manager of the block-listener service
type ListenerContext struct {
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

func (t *ThirdService) GetMethod(method string) (string, error) {
	if v, ok := t.Methods[method]; ok {
		u, err := url.Parse(t.Url)
		if err != nil {
			return "", fmt.Errorf("get method <%s> error: %v", method, err)
		}
		u.Path = path.Join(u.Path, t.Version)
		u.Path = path.Join(u.Path, v)
		return u.String(), nil
	} else {
		return "", fmt.Errorf("not found method: %s", method)
	}
}

func NewListenerContext(yamlPath string) *ListenerContext {

	if data, err := ioutil.ReadFile(yamlPath); err != nil {
		logger.Fatalf("%s %v", yamlPath, err)
	} else {
		lm := ListenerContext{
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

func (m *ListenerContext) GetConfiguration() *Configuration {
	return &m.cfg
}

func (m *ListenerContext) GetChannels() *[]ListenChannel {
	return &m.cfg.ListenChannels
}

func (m *ListenerContext) UpdateChannelBlockFromNum(channel string, num uint64) {
	if index, ok := m.index[channel]; ok {
		m.cfg.ListenChannels[index].FromBlockNum = num
	} else {
		panic(fmt.Sprintf("channel: %s not exist!", channel))
	}
}

func (m *ListenerContext) RecordChannelListenHeight() {
	if bArray, err := yaml.Marshal(m.cfg.ListenChannels); err != nil {
		panic(fmt.Sprintf("dump config error: %v", err))
	} else {
		if wErr := ioutil.WriteFile(m.cfg.Record.DataPath, bArray, 0666); wErr != nil {
			panic(fmt.Sprintf("write config file error: %v", wErr))
		}
	}
}

func (m *ListenerContext) GetLogger() *logging.Logger {
	return m.logger
}

func (m *ListenerContext) RecordEverySeconds() uint64 {
	if m.cfg.Record.Seconds < 3 {
		panic("The record interval is preferably greater than 3 seconds!")
	}
	return m.cfg.Record.Seconds
}
