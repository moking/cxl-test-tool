# cxl-test-tool: a tool to make cxl test with kernel and qemu setup easier

## create qemu image
bash cxl-tool.sh --create-image --image /tmp/qemu.img

This will generate qcow2 image that can be used by the following steps

## configure and compile qemu
bash cxl-tool.sh --setup-qemu

## build qemu
bash cxl-tool.sh --build-qemu

## git clone, configure and compile linux kernel
bash cxl-tool.sh --setup-kernel

## compile linux kernel and install kernel modules
bash cxl-tool.sh --deploy-kernel

## run qemu
bash cxl-tool.sh --run -A kvm -T m2 

## Install ndctl, install cxl modules, setup cxl memory
bash cxl-tool.sh --cxl

## debug qemu
bash cxl-tool.sh --qdb

## debug kernel
bash cxl-tool.sh --kdb

# debug ndctl
bash cxl-tool.sh --ndb

# send commands to VM
bash cxl-tool.sh --C "commands to execute in vm"

# VM management
bash cxl-tool.sh --reset/run/poweroff/shutdown



