#! /bin/bash
#
if [ -f /tmp/qemu-status ];then
    echo "Warning: qemu is running, power off first!"
    running=`cat /tmp/qemu-status | grep -c "QEMU:running"`
    if [ $running -ne 0 ];then
        cxl-tool --poweroff
        sleep 2
    fi
    echo "Before bring up, edit .cxl-topology.xml to have DCD topology"
    cxl-tool --run -A kvm --create-topo
fi                                                                          
cxl-tool --create-dcR

export `cat /tmp/.vars.config | grep "cxl_test_tool_dir"`
bash $cxl_test_tool_dir/test-workflows/process-qmp-op.sh "$1"

cxl-tool --poweroff
