# Block Listener
**TODO:** 监听链路（channel）上的所有区块（block），从区块中获取有效的包裹交易（transaction）发送至第三方服务；

# Program RunTime
## Windows
```go
// hyperledger/fabric-sdk-go/pkg/msp/filekeystore.go
import (
	"path"
)
// 修改为如下， 或使用 Cygwin 运行
import (
	path "path/filepath"
)
```