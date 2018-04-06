#!/bin/bash
echo $PYTHONPATH
python -m  tvm.exec.rpc_server --load-library ${CK_ENV_LIB_VTA_SERVER_LIB_FULL}
