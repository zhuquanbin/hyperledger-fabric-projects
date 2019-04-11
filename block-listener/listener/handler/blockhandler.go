/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/4/11 10:49
*/

package handler

import (
	"fmt"
	"gopkg.in/fatih/set.v0"

	"github.com/ParcelX/block-listener/listener/config"
	"github.com/ParcelX/block-listener/listener/printer"
	"github.com/golang/protobuf/proto"
	"github.com/hyperledger/fabric-sdk-go/pkg/common/logging"
	cb "github.com/hyperledger/fabric-sdk-go/third_party/github.com/hyperledger/fabric/protos/common"
	"github.com/hyperledger/fabric-sdk-go/third_party/github.com/hyperledger/fabric/protos/peer"
	putils "github.com/hyperledger/fabric-sdk-go/third_party/github.com/hyperledger/fabric/protos/utils"
	"github.com/hyperledger/fabric/core/ledger/kvledger/txmgmt/rwsetutil"
	"github.com/hyperledger/fabric/core/ledger/util"
)

func NewBlockHandler(context *config.ListenerContext, logger *logging.Logger) *BlockHandler {
	var _log *logging.Logger
	if _log = logger; _log == nil {
		_log = context.GetLogger()
	}

	_bp := printer.NewBlockPrinterWithOpts(printer.AsOutputFormat("json"),
		printer.AsWriterType("stdout"),
		&printer.FormatterOpts{Base64Encode: false})

	systemCC := set.New(set.NonThreadSafe)
	systemCC.Add("lscc", "qscc", "cscc")

	return &BlockHandler{
		logger:       _log,
		blockPrinter: _bp,
		thirdService: &context.GetConfiguration().ThirdService,
		systemCC:     systemCC,
	}
}

type BlockHandler struct {
	logger       *logging.Logger
	blockPrinter *printer.BlockPrinter
	thirdService *config.ThirdService
	systemCC     set.Interface
}

// handler block
func (h *BlockHandler) Do(block *cb.Block) {
	// do something ...
	method := "collect"
	url, _ := h.thirdService.GetMethod(method)
	h.logger.Infof("get method <%s>: %s", method, url)

	h.logger.Infof("Block Number: %d.  Block: %v", block.Header.GetNumber(), block)
	// print test
	//h.blockPrinter.PrintBlock(block)
	h.extractTransactions(block)

}

// handler block
func (h *BlockHandler) extractTransactions(block *cb.Block) {
	// do something ...

	// Get the invalidation byte array for the block
	txsFilter := util.TxValidationFlags(block.Metadata.Metadata[cb.BlockMetadataIndex_TRANSACTIONS_FILTER])
	// Set the starting tranNo to 0
	var tranNo uint64
	// get txs
	for _, envBytes := range block.Data.Data {

		// If the tran is marked as invalid, skip it
		if txsFilter.IsInvalid(int(tranNo)) {
			h.logger.Debugf("Skipping history write for invalid transaction number %d", tranNo)
			tranNo++
			continue
		}

		env, err := putils.GetEnvelopeFromBlock(envBytes)
		if err != nil {
			h.logger.Error(err)
			continue
		}

		payload, err := putils.GetPayload(env)
		if err != nil {
			h.logger.Error(err)
			continue
		}
		transaction, err := putils.GetTransaction(payload.Data)
		if err != nil {
			h.logger.Error(err)
			continue
		}

		chdr, err := putils.UnmarshalChannelHeader(payload.Header.ChannelHeader)
		if err != nil {
			h.logger.Error(err)
			continue
		}

		if cb.HeaderType(chdr.Type) == cb.HeaderType_ENDORSER_TRANSACTION {
			for _, action := range transaction.Actions {
				actionPayload, respPayload, err := putils.GetPayloads(action)
				if err != nil {
					h.logger.Error(err)
					continue
				}
				cpp, err := putils.GetChaincodeProposalPayload(actionPayload.ChaincodeProposalPayload)
				if err != nil {
					h.logger.Error(err)
					continue
				}
				cis := &peer.ChaincodeInvocationSpec{}
				err = proto.Unmarshal(cpp.Input, cis)
				if err != nil {
					h.logger.Error(err)
					continue
				}

				inputArgs := "Input: "
				for _, value := range cis.ChaincodeSpec.Input.Args {
					inputArgs = fmt.Sprintf("%s %s", inputArgs, string(value))
				}
				h.logger.Info(inputArgs)

				//preparation for extracting RWSet from transaction
				txRWSet := &rwsetutil.TxRwSet{}
				// Get the Result from the Action and then Unmarshal
				// it into a TxReadWriteSet using custom unmarshalling
				if err = txRWSet.FromProtoBytes(respPayload.Results); err != nil {
					h.logger.Error(err)
					continue
				}
				// for each transaction, loop through the namespaces and writesets
				// and add a history record for each write
				for _, nsRWSet := range txRWSet.NsRwSets {
					if h.systemCC.Has(nsRWSet.NameSpace) {
						continue
					}
					for _, kvWrite := range nsRWSet.KvRwSet.Writes {
						h.logger.Infof("KvRwSet k: %s, v: %s, d: %v", string(kvWrite.Key), string(kvWrite.Value), kvWrite.IsDelete)
					}
				}
			}
		} else {
			h.logger.Debugf("Skipping transaction [%d] since it is not an endorsement transaction\n", tranNo)
		}
		tranNo++
	}

}

// http post data
func (h *BlockHandler) postData() {
	// do something ...
}
