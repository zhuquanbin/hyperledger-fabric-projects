/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/3/27 15:57
*/

package config

import "github.com/spf13/pflag"

const (
	usageConfigFilepath   = "listener config file path."
	defaultConfigFilepath = "./config/listen-cfg.yaml"
)

var opts *Options = nil

type Options struct {
	// 配置文件路径
	ConfigFilepath string
}

func GetOptions() *Options {
	if opts != nil {
		return opts
	}
	opts = &Options{}
	return opts
}

func (o *Options) InitConfigFilePath(flags *pflag.FlagSet) {
	flags.StringVarP(&o.ConfigFilepath, "config", "c", defaultConfigFilepath, usageConfigFilepath)
}
