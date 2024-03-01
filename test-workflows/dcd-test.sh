#! /bin/bash
#
cxl-tool --run -A kvm --create-topo
cxl-tool --create-dcR

bash test-workflows/process-qmp-op.sh

cxl-tool --shutdown
