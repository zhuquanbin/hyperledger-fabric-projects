# block-listener
解析区块中每一次的交易，根据调用的链码方法名，向后端发送对应的api请求。为了达到该目的，现在有三方面工作需要做

1. 为调用提供对应的api请求，在spring工程中分出一个微服务
2. 在block-listener解析交易，并增加调用api部分。
3. 根据实际业务要求，修改[链码](https://github.com/ParcelX/chaincode.git)


# Windows Running

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