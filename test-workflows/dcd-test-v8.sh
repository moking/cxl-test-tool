#! /bin/bash
#
if [ ! -f /tmp/qemu-status ];then                                           
    echo "Warning: qemu is not running, bring up qemu with DCD topology first!"                     
    exit
fi                                                                          
running=`cat /tmp/qemu-status | grep -c "QEMU:running"`                     
if [ $running -eq 0 ];then                                                  
    echo "Warning: qemu is not running, bring up qemu with DCD topology first!"                     
    exit
fi

#cxl-tool --run -A kvm --create-topo
cxl-tool --create-dcR

bash test-workflows/process-qmp-op-v8.sh
