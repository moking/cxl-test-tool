#!/usr/bin/env python3
import os
import subprocess
import argparse
import subprocess
import psutil
import time
import signal
import utils.cxl as cxl
import utils.dcd as dcd
import utils.tools as tools
from utils.tools import sh_cmd as sh_cmd
from utils.tools import bg_cmd as bg_cmd
from utils.tools import append_to_file as append_to_file
from utils.tools import write_to_file as write_to_file
from utils.tools import process_id as process_id
from utils.tools import execute_on_vm as execute_on_vm
from utils.tools import path_exist_on_vm as path_exist_on_vm
from utils.terminal import login_vm as login_vm
from utils.terminal import gdb_on_vm as gdb_on_vm
from utils.debug import gdb_process as gdb_process
from utils.cxl_topology_parser import gen_cxl_topology

extra_opts=""
wait_flag="nowait"
format="raw"
num_cpus="8"
accel_mode="kvm"
ssh_port="2024"
status_file="/tmp/qemu-status"
run_log="/tmp/qemu.log"
net_config="-netdev user,id=network0,hostfwd=tcp::%s-:22 -device e1000,netdev=network0"%ssh_port
SHARED_CFG="-qmp tcp:localhost:4444,server,wait=off"
ndctl_dir="~/ndctl"

RP1="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=512M \
     -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
     -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0,sn=0xabcd \
     -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

topo=RP1

def expend_variable(value):
    if "$" not in value:
        return value;
    i=0;
    rs=""
    items=value.split()
    for item in items:
        item=item.strip()
        item=item.strip("\"")
        if not item:
            continue
        if item[0] == "$":
            name=item[1:]
            item=os.getenv(name.strip("\"")).strip("\"")
        rs += item + " "
    
    return rs

def read_config(conf):
    with open(conf, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                pos=line.find("=")
                name = line[:pos].strip()
                val = line[pos+1:].strip()
                has_quote=False
                if "\"" in val:
                    has_quote=True
                    val=val.strip("\"")
                new=expend_variable(val)
                if has_quote:
                    os.environ[name]="\""+new+"\""
                else:
                    os.environ[name]=new

def vm_is_running():
    """Check if any process with the given name is alive."""
    # Iterate over all running processes
    name="qemu-system"
    for process in psutil.process_iter(['name']):
        try:
            # Check if the process name matches
            if name in process.info['name']: 
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Handle the cases where the process might terminate during iteration
            continue
    return False

def shutdown_vm():
    if vm_is_running():
        execute_on_vm("poweroff")
        time.sleep(2)
        if not vm_is_running():
            print("VM is powerered off")
    else:
        print("No VM is alive, skip shutdown")

def run_qemu(topo):
    if vm_is_running():
        print("VM is running, exit")
        return;
    
    print("Starting VM...")
    bin=QEMU
    cmd=" -s "+extra_opts+ " -kernel "+KERNEL_PATH+" -append "+os.getenv("KERNEL_CMD")+ \
            " -smp " +num_cpus+ \
            " -accel "+accel_mode + \
            " -serial mon:stdio "+ \
            " -nographic " + \
            " "+SHARED_CFG+" "+ net_config + " "+\
            " -monitor telnet:127.0.0.1:12345,server,"+wait_flag+\
            " -drive file="+os.getenv("QEMU_IMG")+",index=0,media=disk,format="+format+\
            " -machine q35,cxl=on -m 8G,maxmem=32G,slots=8 "+ \
            " -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped "+\
            " -virtfs local,path=/home/"+user+",mount_tag=homeshare,security_model=mapped "+ topo

    write_to_file("/tmp/run-cmd", cmd)
    bg_cmd(bin+cmd)
    if vm_is_running():
        write_to_file(status_file, "QEMU:running")
        print("QEMU instance is up, access it: ssh root@localhost -p %s"%ssh_port)
    else:
        write_to_file(status_file, "")
        print("Start Qemu failed, check /tmp/qemu.log for more information")


def compile_ndctl(dir):
    cmd = "cd %s;\
        meson setup build;\
        meson compile -C build;\
        meson install -C build" %dir
    print(cmd)
    return execute_on_vm(cmd)

def install_ndctl(url="https://github.com/pmem/ndctl.git", dir="/tmp/ndctl"):
    cmd= "apt-get install -y git meson bison pkg-config cmake libkmod-dev libudev-dev uuid-dev libjson-c-dev libtraceevent-dev libtracefs-dev asciidoctor keyutils libudev-dev libkeyutils-dev libiniparser-dev 1>&/dev/null"
    print(cmd)
    out=execute_on_vm(cmd)
    print(out)
    cmd="git clone %s %s"%(url, dir)
    print(cmd)
    out=execute_on_vm("git clone %s %s"%(url, dir))
    print(out)
    out=compile_ndctl(dir)
    print(out)


def gdb_ndctl(cmd):
    subdir=cmd.split()[0]
    if not vm_is_running():
        print("VM is not running, skip debug")
        return
    if not path_exist_on_vm(ndctl_dir):
        print("ndctl directory not found")
        return

    gdb_on_vm("gdb --args %s/build/%s/%s"%(ndctl_dir, subdir, cmd))

def gdb_qemu():
    #pid=sh_cmd("ps -ef | grep qemu-system | awk '{print $2}'")
    pid=process_id("qemu-system")
    if pid == -1:
        print("Qemu process not found, try to run qemu first")
        return
    cmd="cat /proc/sys/kernel/yama/ptrace_scope"
    rs=sh_cmd(cmd)
    if rs == "1":
        cmd="echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope"
        rs=sh_cmd(cmd)
    gdb_process(pid)

def gdb_kernel():
    if not vm_is_running:
        print("VM is not running, skip debug")
        return
    path=os.getenv("KERNEL_ROOT")
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        subprocess.run(["gdb", "--tui", "%s/vmlinux"%path] )
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)

def setup_qemu(url, branch, qemu_dir):
    git_clone=True
    if os.path.exists(qemu_dir):
        print("%s exists, please take care of it first before proceeding"%qemu_dir)
        cmd=input("Do you want to continue and skip git clone (Y/N):")
        if cmd.lower() == "y":
            git_clone=False
        else:
            return
    package_str="libglib2.0-dev libgcrypt20-dev zlib1g-dev \
        autoconf automake libtool bison flex libpixman-1-dev bc\
        make ninja-build libncurses-dev libelf-dev libssl-dev debootstrap \
        libcap-ng-dev libattr1-dev libslirp-dev libslirp0 python3-venv"

    tools.install_packages(package_str)
    if git_clone:
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, qemu_dir)
        rs=tools.sh_cmd(cmd, echo=True)
        print(rs)
    cmd="cd %s;./configure --target-list=x86_64-softmmu --enable-debug"%(qemu_dir)
    tools.sh_cmd(cmd, echo=True)
    cmd="cd %s; make -j 16"%qemu_dir
    tools.sh_cmd(cmd, echo=True)

def build_qemu(url, branch, qemu_dir):
    if not os.path.exists(qemu_dir):
        print("No qemu source code found, may need run --setup-qemu")
        return
    cmd="cd %s; make -j 16"%qemu_dir
    tools.sh_cmd(cmd, echo=True)

def setup_kernel(url, branch, kernel_dir):
    git_clone=True
    if os.path.exists(kernel_dir):
        print("%s exists, please take care of it first before proceeding"%kernel_dir)
        cmd=input("Do you want to continue and skip git clone (Y/N):")
        if not cmd:
            cmd="Y"
        if cmd.lower() == "y":
            git_clone=False
        else:
            return
    if git_clone:
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, kernel_dir)
        tools.sh_cmd(cmd, echo=True)
    else:
        cmd=input("Want to pull updates from remote repo for branch %s (Y/N):"%branch)
        if not cmd:
            cmd="Y"
        if cmd.lower() == "y":
            cmd="git pull"
            tools.sh_cmd(cmd, echo=True)

    if os.path.exists("%s/.config"%kernel_dir):
        rs=input("Found .config under %s, use it for kernel config without change (Y/N): "%kernel_dir)
        if not rs:
            rs="Y";
        if rs.lower() == "n":
            rs=input("Configure mannually (1) or copy the example config (2): ")
            if not rs:
                rs="1"
            if rs == "1":
                subprocess.run("cd %s; make menuconfig"%kernel_dir, shell=True)
            elif rs == "2":
                too_dir=os.getenv("cxl_test_tool_dir").stri("\"")
                cmd="cp %s/kconfig.example %s/.config"%(tool_dir, kernel_dir)
                tools.sh_cmd(cmd, echo=True)
            else:
                print("Unknown choice, exit")
                return
    else:
        rs=input(".config not found, configure mannually (1) or copy the example config (2): ")
        if not rs:
            rs="1"
        if rs == "1":
            subprocess.run("cd %s; make menuconfig"%kernel_dir, shell=True)
        elif rs == "2":
            cmd="cp %s/kconfig.example %s/.config"%(os.getenv("cxl_test_tool_dir"), kernel_dir)
            tools.sh_cmd(cmd, echo=True)
        else:
            print("Unknown choice, exit")
            return

    tools.exec_shell_direct("cd %s; make -j 16"%kernel_dir, echo=True)
    tools.exec_shell_direct("cd %s; sudo make modules_install"%kernel_dir, echo=True)

def build_kernel(url, branch, kernel_dir):
    if not os.path.exists(kernel_dir):
        print("No kernel source code found, may need run --setup-kernel")
        return
    cmd="cd %s; make -j 16"%kernel_dir
    tools.exec_shell_direct("cd %s; make -j 16"%kernel_dir, echo=True)
    tools.exec_shell_direct("cd %s; sudo make modules_install"%kernel_dir, echo=True)



def create_qemu_image(img_path):
    if not img_path:
        print("No qemu image path given")
        return
    if os.path.exists(img_path):

        rs=input("File already exists, wait to create again (Y/N):")
        if not rs or rs.lower() != "y":
           return
    else:
        tools.exec_shell_direct("dir=$(dirname %s); mkdir -p $dir"%img_path)

    cmd='''network:
    version: 2
    renderer: networkd
    ethernets:
        enp0s2:
            dhcp4: true
    '''
    file="/tmp/netplan-config.yaml"
    write_to_file(file, cmd)
    sh_cmd("chmod 600  %s"%file)
    qemu_tool=os.getenv("QEMU_ROOT") + "/build/qemu-img"
    if not os.path.exists(qemu_tool):
        print("qemu-img tool not found")
        return

    cmd="%s create %s 16g"%(qemu_tool, img_path)
    tools.exec_shell_direct(cmd)
    cmd="sudo mkfs.ext4 %s"%img_path
    tools.exec_shell_direct(cmd, echo=True)
    tmp_dir="/tmp/img_dir"
    cmd="mkdir -p %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo mount -o loop %s %s"%(img_path, tmp_dir)
    tools.exec_shell_direct(cmd, echo=True)

    print("Starting to debootstrap for the VM")
    cmd="sudo debootstrap --arch amd64 stable %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="Copy ssh key to guest to skip password login later"
    print(cmd)
    cmd="sudo mkdir %s/root/.ssh"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="cat ~/.ssh/*.pub > /tmp/authorized_keys"
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo cp /tmp/authorized_keys %s/root/.ssh/"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="echo nameserver 8.8.8.8  | sudo tee -a %s/etc/resolv.conf"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    cmd="sudo mkdir -p %s/etc/netplan/"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo cp /tmp/netplan-config.yaml %s/etc/netplan/config.yaml"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    whoami=sh_cmd("whoami")
    rc="/tmp/rc.local"
    write_to_file(rc, '''#! /bin/bash
stty rows 80 cols 132
mount -t 9p -o trans=virtio homeshare /home/%s
mount -t 9p -o trans=virtio modshare /lib/modules
'''%whoami)
    cmd="chmod a+x %s"%rc
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo cp /tmp/rc.local %s/etc/"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo mkdir -p %s/home/%s"%(tmp_dir,whoami)
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo mkdir -p %s/lib/modules/"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    cmd="sudo chroot %s passwd -d root"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo chroot %s apt-get update"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo chroot %s apt-get install -y ssh netplan.io openvswitch-switch"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo umount %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    cmd="ssh-keygen -f ~/.ssh/known_hosts -R [localhost]:2024"
    tools.exec_shell_direct(cmd, echo=True)
    cmd="ls %s -lh"%img_path
    tools.exec_shell_direct(cmd, echo=True)

def cxl_pmem_test(memdev):
    if not vm_is_running():
        print("VM is not running, skip")
        return
    if not path_exist_on_vm(ndctl_dir):
        ndctl_url=os.getenv("ndctl_url")
        install_ndctl(url=ndctl_url, dir=ndctl_dir)

    if not cxl.cxl_driver_loaded():
        cxl.load_driver()

    mode = cxl.find_mode(memdev)
    if mode != "pmem":
        print("%s is not pmem dev"%memdev)
        return
    region=cxl.create_region(memdev)
    time.sleep(1)
    if not region:
        return
    (ns, dax) = cxl.create_namespace(region)
    if not dax:
        print("Create namespace failed")
        return
    cmd="daxctl reconfigure-device --mode=system-ram --no-online %s"%dax
    out = execute_on_vm(cmd)
    print(out)
    cmd = "daxctl online-memory %s"%dax
    out = execute_on_vm(cmd)
    print(out)
    cmd="lsmem"
    out = execute_on_vm(cmd)
    print(out)

def cxl_vmem_test(memdev):
    if not vm_is_running():
        print("VM is not running, skip")
        return
    if not path_exist_on_vm(ndctl_dir):
        ndctl_url=os.getenv("ndctl_url")
        install_ndctl(url=ndctl_url, dir=ndctl_dir)

    if not cxl.cxl_driver_loaded():
        cxl.load_driver()

    mode = cxl.find_mode(memdev)
    if mode != "ram":
        print("%s is not volatile cxl memdev"%memdev)
        return
    region=cxl.create_region(memdev)
    cmd="lsmem"
    out = execute_on_vm(cmd)
    print(out)

def dcd_test(memdev):
    if not vm_is_running():
        print("VM is not running, skip")
        return

    if not path_exist_on_vm(ndctl_dir):
        ndctl_url=os.getenv("ndctl_url")
        install_ndctl(url=ndctl_url, dir=ndctl_dir)

    if not cxl.cxl_driver_loaded():
        print("Load cxl drivers first")
        cxl.load_driver()

    region=cxl.create_dc_region(memdev)
    if not region:
        print("Create DC region failed")
        return

    dev=cxl.find_cmdline_device_id(memdev)
    print(dev)
    dcd.handle_dc_extents_op(memdev)

    ans=input("Do you want to continue to create dax device for DC(Y/N):")
    if not ans or ans.lower() == "n":
        return
    dax=cxl.create_dax_device(region, echo=True)
    if not dax:
        print("Create dax device failed")
        return
    cmd="daxctl reconfigure-device %s -m system-ram"%dax
    execute_on_vm(cmd, echo=True)
    cmd="lsmem"
    rs=execute_on_vm(cmd)
    print(rs)

parser = argparse.ArgumentParser(description='A tool for cxl test with Qemu setup')
parser.add_argument('-R','--run', help='start qemu instance', action='store_true')
parser.add_argument('--create-topo', help='use xml to generate topology', action='store_true')
parser.add_argument('--login', help='login to the VM', action='store_true')
parser.add_argument('--poweroff', help='poweroff the VM', action='store_true')
parser.add_argument('--shutdown', help='poweroff the VM', action='store_true')
parser.add_argument('-C','--cmd', help='command to execute on VM', required=False, default="")
parser.add_argument('--ndb', help='gdb ndctl on VM', required=False, default="")
parser.add_argument('--qdb', help='gdb qemu', action='store_true')
parser.add_argument('--kdb', help='gdb kernel', action='store_true')
parser.add_argument('--install-ndctl', help='install ndctl on VM', action='store_true')
parser.add_argument('--load-drv', help='install cxl driver on VM', action='store_true')
parser.add_argument('--unload-drv', help='uninstall cxl driver on VM', action='store_true')
parser.add_argument('--create-region', help='create cxl region', required=False, default="")
parser.add_argument('--destroy-region', help='destroy cxl region', required=False, default="")
parser.add_argument('--setup-qemu', help='setup qemu', action='store_true')
parser.add_argument('--setup-kernel', help='setup kernel', action='store_true')
parser.add_argument('-BQ', '--build-qemu', help='build qemu', action='store_true')
parser.add_argument('-BK', '--build-kernel', help='build kernel', action='store_true')
parser.add_argument('--create-image', help='create a qemu image', action='store_true')
parser.add_argument('--cxl-pmem-test', help='online pmem as system ram', required=False, default="")
parser.add_argument('--cxl-vmem-test', help='online vmem as system ram', required=False, default="")
parser.add_argument('--create-dcR', help='create a dc Region for a memdev', required=False, default="")
parser.add_argument('--dcd-test', help='dcd test workflow for a memdev', required=False, default="")
parser.add_argument('--issue-qmp', help='Issue QMP command from a file to VM', required=False, default="")

args = vars(parser.parse_args())

user=sh_cmd("whoami")
read_config(".vars.config")
QEMU=os.getenv("QEMU_ROOT")+"/build/qemu-system-x86_64"                                   
KERNEL_PATH=os.getenv("KERNEL_ROOT")+"/arch/x86/boot/bzImage"

if args["setup_qemu"]:
    setup_qemu(url=os.getenv("qemu_url"), branch=os.getenv("qemu_branch"), qemu_dir=os.getenv("QEMU_ROOT"))
if args["setup_kernel"]:
    setup_kernel(url=os.getenv("kernel_url"), branch=os.getenv("kernel_branch"), kernel_dir=os.getenv("KERNEL_ROOT"))
if args["build_qemu"]:
    build_qemu(url=os.getenv("qemu_url"), branch=os.getenv("qemu_branch"), qemu_dir=os.getenv("QEMU_ROOT"))
if args["build_kernel"]:
    build_kernel(url=os.getenv("kernel_url"), branch=os.getenv("kernel_branch"), kernel_dir=os.getenv("KERNEL_ROOT"))

if args["create_image"]:
    create_qemu_image(img_path=os.getenv("QEMU_IMG"))

if args["create_topo"]:
    topo=gen_cxl_topology()

if args["run"]:
    run_qemu(topo)

if args["login"]:
    login_vm()

if args["poweroff"] or args["shutdown"]:
    shutdown_vm()

if args["cmd"]:
    rs=execute_on_vm(args["cmd"])
    if rs:
        print(rs)
if args["ndb"]:
    gdb_ndctl(args["ndb"])
if args["qdb"]:
    gdb_qemu()
if args["kdb"]:
    gdb_kernel()

if args["install_ndctl"]:
    ndctl_url=os.getenv("ndctl_url")
    install_ndctl(url=ndctl_url, dir=ndctl_dir)
if args["load_drv"]:
    cxl.load_driver()
if args["unload_drv"]:
    cxl.unload_driver()
if args["create_region"]:
    region=cxl.create_region(args["create_region"])
if args["destroy_region"]:
    cxl.destroy_region(args["destroy_region"])
if args["cxl_pmem_test"]:
    cxl_pmem_test(args["cxl_pmem_test"])
if args["cxl_vmem_test"]:
    cxl_vmem_test(args["cxl_vmem_test"])
if args["create_dcR"]:
    cxl.create_dc_region(args["create_dcR"])
if args["dcd_test"]:
    dcd_test(args["dcd_test"])
if args["issue_qmp"]:
    tools.issue_qmp_cmd(args["issue_qmp"])
