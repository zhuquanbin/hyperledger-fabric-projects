/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/3/27 14:45
*/

package cmd

import (
	"github.com/ParcelX/block-listener/listener/config"
	"github.com/ParcelX/block-listener/listener/event"
	"github.com/spf13/cobra"
	"os"
)

var newBlockListenerCmd = &cobra.Command{
	Use:   "listener",
	Short: "Listen to block events.",
	Long:  "Listen to block events",
	Run: func(cmd *cobra.Command, args []string) {
		event.BlockListenerAction()
	},
}

func getBlockListenerCmdCmd() *cobra.Command {
	flags := newBlockListenerCmd.PersistentFlags()
	config.GetOptions().InitConfigFilePath(flags)
	return newBlockListenerCmd
}

func Execute() {
	if err := getBlockListenerCmdCmd().Execute(); err != nil {
		os.Exit(1)
	}
}
