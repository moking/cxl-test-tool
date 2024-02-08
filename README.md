# cxl-test-tool: a tool to make cxl test with kernel and qemu setup easier

# run configuration file
All the run configuration options are defined in .vars.config. This options will control where the directory of qemu, kernel, and which qemu image we want to use.
Also, all the URLs related to git clone operation is defined there.
The easiest way to generate the file is to copy run_vars.example and make the change as needed.

* qemu launch command string is stored: /tmp/cmd
* qemu topology used: /tmp/topo
* qemu run output: /tmp/qemu.log

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

# create dc region
bash cxl-tool.sh --create-dcR

# Issue qmp commands through qmp file
bash cxl-tool.sh --issue-qmp qmp_file

This command can be used for poison injection, dc extent add/release

# print out help information to show all available options
bash cxl-tool.sh --help

# instructions for DCD related test
1. run qemu with DCD topology;
2. create DC region: cxl-tool.sh --dcR
3. test add/release dc extents through qmp interface: cxl-tool.sh --issue-qmp qmp-command.example
4. check extents: cxl-tool.sh --login
<pre>
root@DT:~# ls /sys/bus/cxl/devices/decoder0.0/region0/dax_region0/ -lh
total 0
drwxr-xr-x 3 root root    0 Feb  8 20:09 dax0.0
drwxr-xr-x 2 root root    0 Feb  8 20:14 dax_region
-r--r--r-- 1 root root 4.0K Feb  8 20:14 devtype
lrwxrwxrwx 1 root root    0 Feb  8 20:14 driver -> ../../../../../../../bus/cxl/drivers/cxl_dax_region
drwxr-xr-x 2 root root    0 Feb  8 20:14 extent0
drwxr-xr-x 2 root root    0 Feb  8 20:14 extent64
-r--r--r-- 1 root root 4.0K Feb  8 20:14 modalias
lrwxrwxrwx 1 root root    0 Feb  8 20:09 subsystem -> ../../../../../../../bus/cxl
</pre>
