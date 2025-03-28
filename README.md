# cxl-test-tool: a tool to make cxl test with kernel and qemu setup easier

* NOTE: cxl-tool.sh is not maintained anymore, always use cxl-tool.py.

* For feedback, please email nifan.cxl@gmail.com.
* If you like the tool, please star it to attract more people's interests.

# Recent important changes.

* **ADD suppot for archlinux (tested on my laptop, may need more fix);**

* Now you can test bare metal with simple configuration, see commit 87697211e3a96aaec946baa57e9b18f6d31401f8

* Done: recently I started to move the code to python so it is easier to support more complicated use workflow. cxl-tool.py is the new main file.*
<pre>
1. Updated DCD test workflow;
2. Add mctp setup;
3. Add ras related test support;
4. ...
</pre>

NOTE:

* the tool needs python3 and some other packages.  Before starting to use it.
* Make sure you have git, ssh, python3, python-is-python3, gdb, gcc installed.
* Also, before creating the qemu image, generate ssh key first with ssh-keygen on the host if not already exist.
* The created image uses the public key to enable passwordless access.

# Instruction for first time users (Debian based release + archlinux (need more test))
1. download cxl-test-tool from github;
2. Install packages needed (python3, python-is-python3, ssh);
3. Generate ssh key if not already (for keyless access to the VM) on the host;
4. cp run_vars.example .vars.config;
5. Configure .vars.config as needed;
6. setup QEMU: ./cxl-tool.py --setup-qemu (If ninja not found, check if the right location is pointed for ninja)
7. Create Qemu image for VM: ./cxl-tool.py --create-image
8. setup Kernel: ./cxl-tool.py --setup-kernel
9. Start a VM with basic CXL topology: ./cxl-tool.py --run
10. login to the VM by: ./cxl-tool.py --login
11. Enjoy and explore more with the tool ...

# run configuration file
All the run configuration options are defined in .vars.config. This options will control where the directory of qemu, kernel, and which qemu image we want to use.
Also, all the URLs related to git clone operation is defined there.
The easiest way to generate the file is to copy run_vars.example and make the change as needed.

* qemu launch command string is stored: /tmp/cxl-logs/cmd
* qemu topology used: /tmp/cxl-logs/topo
* qemu run output: /tmp/cxl-logs/qemu.log

## create qemu image
cxl-tool.py --create-image

This will generate qemu image under at location "QEMU_IMG"  that can be used by the following steps.

## git clone, configure and compile qemu
cxl-tool.py --setup-qemu

## build qemu
cxl-tool.py --build-qemu

## git clone, configure and compile linux kernel
cxl-tool.py --setup-kernel

## run qemu
cxl-tool.py --run -A kvm -T m2 

## run qemu with cxl topology generated from .cxl-topology.xml file
cxl-tool.py --run -A kvm --create-topo

## Install ndctl to the VM
cxl-tool.py --install-ndctl

## Install ndctl, install cxl modules, setup cxl memory
cxl-tool.py --cxl-pmem-test mem0

## debug qemu
cxl-tool.py --qdb

## debug kernel
cxl-tool.py --kdb

# debug ndctl
cxl-tool.py --ndb "cxl list"

# send commands to VM
cxl-tool.py --C "commands to execute in vm"

# VM management
cxl-tool.py --run/poweroff/shutdown

# create dc region
cxl-tool.py --create-dcR mem0

# Issue qmp commands through qmp file
cxl-tool.py --issue-qmp qmp_file

This command can be used for poison injection, dc extent add/release

# print out help information to show all available options
cxl-tool.py --help

# Instructions for DCD related test
1. Apply the patch test-workflows/0001-qapi-cxl.json-Add-QMP-interfaces-to-print-out-accept.patch on top of qemu source code which have DCD emulation support;
2. Create a cxl topology that has DCD support (only single dcd device tested) in .cxl-topology.xml;
3. run test:  cxl-tool.py --dcd-test
