# cxl-test-tool: a tool to make cxl test with kernel and qemu setup easier

# run configuration file
All the run configuration options are defined in .vars.config. This options will control where the directory of qemu, kernel, and which qemu image we want to use.
Also, all the URLs related to git clone operation is defined there.
The easiest way to generate the file is to copy run_vars.example and make the change as needed.

## create qemu image
bash cxl-tool.sh --create-image --image /tmp/qemu.img

This will generate qcow2 image under /tmp/ that can be used by the following steps.

## git clone, configure and compile qemu
bash cxl-tool.sh --setup-qemu

## build qemu
bash cxl-tool.sh --build-qemu

## git clone, configure and compile linux kernel
bash cxl-tool.sh --setup-kernel

## compile linux kernel and install kernel modules
bash cxl-tool.sh --deploy-kernel

## run qemu
bash cxl-tool.sh --run -A kvm -T m2 

## run qemu with cxl topology generated from .cxl-topology.xml file
bash cxl-tool.sh --run -A kvm --create-topo

## Install ndctl to the VM
bash cxl-tool.sh --install-ndctl

## Install ndctl, install cxl modules, setup cxl memory
bash cxl-tool.sh --cxl

## debug qemu
bash cxl-tool.sh --qdb

## debug kernel
bash cxl-tool.sh --kdb

# debug ndctl
bash cxl-tool.sh --ndb "cxl list"

# send commands to VM
bash cxl-tool.sh --C "commands to execute in vm"

# VM management
bash cxl-tool.sh --reset/run/poweroff/shutdown

# print out help information to show all available options
bash cxl-tool.sh --help

