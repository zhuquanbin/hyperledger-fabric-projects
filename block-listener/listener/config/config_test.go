/*
 Copyright 2019 The Go Authors. All rights reserved.

 Created by quanbin.zhu at 2019/4/9 14:59
*/

package config

import "testing"

var listenerContext = NewListenerContext("./config/listen-cfg.yaml")
var cfg = listenerContext.GetConfiguration()

func testGetMethod(t *testing.T, method string) {
	url, err := cfg.ThirdService.GetMethod(method)
	if err != nil {
		t.Logf("get method <%s> err: %v", method, err)
	} else {
		t.Logf("get method <%s>: %s", method, url)
	}
}

func TestThirdService_GetMethod(t *testing.T) {
	testGetMethod(t, "collect")
	testGetMethod(t, "clearancestart")
}
