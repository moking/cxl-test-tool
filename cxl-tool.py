#!/usr/bin/env python3
import os
import subprocess
import argparse
import subprocess
import psutil
import time
import signal
import utils.cxl as cxl
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
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0 \
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

    gdb_on_vm("cd %s; gdb --args ./build/%s/%s"%(ndctl_dir, subdir, cmd))

def gdb_qemu():
    #pid=sh_cmd("ps -ef | grep qemu-system | awk '{print $2}'")
    pid=process_id("qemu-system")
    if pid == -1:
        print("Qemu process not found, try to run qemu first")
        return
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

args = vars(parser.parse_args())

user=sh_cmd("whoami")
read_config(".vars.config")
QEMU=os.getenv("QEMU_ROOT")+"/build/qemu-system-x86_64"                                   
KERNEL_PATH=os.getenv("KERNEL_ROOT")+"/arch/x86/boot/bzImage"

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
    install_ndctl(dir=ndctl_dir)
if args["load_drv"]:
    cxl.load_driver()
if args["unload_drv"]:
    cxl.unload_driver()
