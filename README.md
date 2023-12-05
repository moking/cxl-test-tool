# cxl-test-tool: a tool to make cxl test with kernel and qemu setup easier

## create qemu image
bash cxl-tool.sh --create-image --image /tmp/qemu.img

This will generate qcow2 image that can be used by the following steps

## configure and compile qemu
bash cxl-tool.sh --setup-qemu

## configure and compile linux kernel
bash cxl-tool.sh --setup-kernel

## run qemu
bash cxl-tool.sh --run -A kvm -T m2 

## Install ndctl, install cxl modules, setup cxl memory
bash cxl-tool.sh --cxl



