#!/usr/bin/env python3
import os
import subprocess
import argparse
import subprocess
import psutil
import shutil
import filecmp
import time
import signal
import utils.cxl as cxl
import utils.dcd as dcd
import utils.tools as tools
import utils.mctp as mctp
import utils.ras as ras
from utils.tools import system_path as system_path
from utils.tools import run_qemu as run_qemu
from utils.tools import shutdown_vm as shutdown_vm
from utils.tools import vm_is_running as vm_is_running
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
import utils.arm as arm
from utils.config import parse_config as parse_config

ndctl_dir="~/ndctl"

topo=""

def expend_variable(value):
    if "$" not in value:
        return value;
    i=0;
    rs=""
    items=value.split()
    for item in items:
        if not item:
            continue
        item=item.strip()
        if item:
            item=item.strip("\"")
        if item and item[0] == "$":
            name=item[1:]
            item=os.getenv(name.strip("\""))
            if not item:
                continue
            item = item.strip("\"")
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
                #if new.startswith("~"):
                    #new=os.environ.get('HOME')+new[1:]
                if has_quote:
                    os.environ[name]="\""+new+"\""
                else:
                    os.environ[name]=new
                print(os.environ[name])


def compile_ndctl(dir):
    cmd = "cd %s;\
        meson setup build;\
        meson compile -C build;\
        meson install -C build" %dir
    print(cmd)
    if tools.is_bare_metal():
        tools.exec_shell_direct(cmd)
    else:
        tools.exec_shell_remote_direct(cmd)

def ndctl_installed():
    cmds = "cxl daxctl ndctl"
    for cmd in cmds.split():
        if tools.is_bare_metal():
            rs = tools.sh_cmd("which %s"%cmd)
        else:
            rs = execute_on_vm("which %s"%cmd)
        if not rs:
            return False
    print("ndctl tools are already installed!")
    return True

def install_ndctl(dir="/tmp/ndctl"):
    cmd= "git meson bison pkg-config cmake libkmod-dev libudev-dev uuid-dev libjson-c-dev libtraceevent-dev libtracefs-dev asciidoctor keyutils libudev-dev libkeyutils-dev libiniparser-dev libsystemd-dev"
    url = tools.system_env("ndctl_url")
    if not url:
        url="https://github.com/pmem/ndctl.git",
    branch = tools.system_env("ndctl_branch")
    if not branch:
        branch = "main"
    if tools.is_bare_metal():
        tools.install_packages(cmd)
        tools.git_clone(url = url, branch = branch, dst_dir = dir)
    else:
        tools.install_packages_on_vm(cmd, echo = True)
        tools.git_clone_on_vm(url = url, branch = branch, dst_dir = dir)

    compile_ndctl(dir)
    return ndctl_installed();

def gdb_ndctl(cmd):
    subdir=cmd.split()[0]
    if not vm_is_running():
        print("VM is not running, skip debug")
        return
    if not path_exist_on_vm(ndctl_dir):
        print("ndctl directory not found")
        return

    tools.install_packages_on_vm("gdb")
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
        cmd="cat /proc/sys/kernel/yama/ptrace_scope"
        rs=sh_cmd(cmd)
        if rs == "1":
            print("ptrace_scope not correctly set")
            return
    gdb_process(pid)

def gdb_kernel():
    if not vm_is_running:
        print("VM is not running, skip debug")
        return
    path=system_path("KERNEL_ROOT")
    original_sigint_handler = signal.getsignal(signal.SIGINT)
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        cmd="cd %s; gdb ./vmlinux"%path
        subprocess.run(cmd, shell=True)
    finally:
        signal.signal(signal.SIGINT, original_sigint_handler)


def create_qemu_image(img_path, size="16g", ubuntu=False):
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
    qemu_tool=system_path("QEMU_ROOT") + "/build/qemu-img"
    if not os.path.exists(qemu_tool):
        print("qemu-img tool not found")
        return

    cmd="%s create %s %s"%(qemu_tool, img_path, size)
    tools.exec_shell_direct(cmd)
    cmd="sudo mkfs.ext4 %s"%img_path
    tools.exec_shell_direct(cmd, echo=True)
    tmp_dir="/tmp/img_dir"
    cmd="mkdir -p %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo mount -o loop %s %s"%(img_path, tmp_dir)
    tools.exec_shell_direct(cmd, echo=True)

    tools.install_packages("debootstrap")
    cmd = "whereis debootstrap"
    rs = sh_cmd(cmd)
    rs.replace("debootstrap:", "")
    if not rs:
        print("tool: debootstrap not found, exit")
        return
    print("Starting to debootstrap for the VM")
    if ubuntu:
        url="http://us.archive.ubuntu.com/ubuntu/ubuntu/"
        cmd="sudo debootstrap --arch amd64 bionic %s %s"%(tmp_dir,url)
    else:
        cmd="sudo debootstrap --arch amd64 stable %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="Copy ssh key to guest to skip password login later"
    print(cmd)
    cmd="sudo mkdir %s/root/.ssh"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    if not os.path.exists(os.path.expanduser("~/.ssh")):
        print("Note: .ssh not found on the host, continue to generate ssh key")
        cmd = "ssh-keygen"
        tools.exec_shell_direct(cmd, echo=True)

    pub_files = [f for f in os.listdir(os.path.expanduser("~/.ssh")) if f.endswith('.pub')]
    if not pub_files:
        print("Warning: ssh public key file not found on the host, need to mount the image and added to authorized_keys on the VM")
    else:
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
    cmd="sudo chroot %s apt-get install -y ssh git"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo chroot %s apt-get install -y ssh git netplan.io cmake meson locales"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)
    cmd="sudo umount %s"%tmp_dir
    tools.exec_shell_direct(cmd, echo=True)

    port = tools.system_env("ssh_port")
    cmd="ssh-keygen -f ~/.ssh/known_hosts -R [localhost]:%s"%port
    tools.exec_shell_direct(cmd, echo=True)
    cmd="ls %s -lh"%img_path
    tools.exec_shell_direct(cmd, echo=True)

def cxl_pmem_test(memdev):
    if not vm_is_running():
        print("VM is not running, skip")
        return
    if not path_exist_on_vm(ndctl_dir) or not ndctl_installed():
        ndctl_url=os.getenv("ndctl_url")
        rs = install_ndctl(dir=ndctl_dir)
        if not rs:
            return

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
        rs = install_ndctl(dir=ndctl_dir)
        if not rs:
            return


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
        rs = install_ndctl(url=ndctl_url, dir=ndctl_dir)
        if not rs:
            return

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

    ans = "N"
    try:
        ans=input("Do you want to continue to create dax device for DC(Y/N):")
    except EOFError:
        pass
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
parser.add_argument('-v','--verbose', help='show more message', action='store_true')
parser.add_argument('-R','--run', help='start qemu instance in background', action='store_true')
parser.add_argument('--run-direct', help='start qemu instance', action='store_true')
parser.add_argument('-T','--topo', help='cxl topology to use', required=False, default="")
parser.add_argument('--raw', action='store_true', help='The raw QEMU topology string. Only used with T/--topo')
parser.add_argument('-A','--accel', help='accel mode: kvm/tcg', required=False, default="kvm")
parser.add_argument('-E','--extra', help='extra options when run qemu', required=False, default="")
parser.add_argument('--create-topo', help='use xml to generate topology', action='store_true')
parser.add_argument('--login', help='login to the VM', action='store_true')
parser.add_argument('--login-fm', help='login to the FM VM', action='store_true')
parser.add_argument('--poweroff', help='poweroff the VM', action='store_true')
parser.add_argument('--shutdown', help='poweroff the VM', action='store_true')
parser.add_argument('--poweroff-fm', help='poweroff the FM VM', action='store_true')
parser.add_argument('--shutdown-fm', help='poweroff the FM VM', action='store_true')
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
parser.add_argument('--setup-qemu-arm', help='setup qemu for aarch64', action='store_true')
parser.add_argument('--setup-kernel', help='setup kernel', action='store_true')
parser.add_argument('--setup-kernel-fm', help='setup kernel for fm', action='store_true')
parser.add_argument('--kconfig', help='configure kernel with menuconfig', action='store_true')
parser.add_argument('-BQ', '--build-qemu', help='build qemu', action='store_true')
parser.add_argument('-BK', '--build-kernel', help='build kernel', action='store_true')
parser.add_argument('--create-image', help='create a qemu image', action='store_true')
parser.add_argument('--cxl-pmem-test', help='online pmem as system ram', required=False, default="")
parser.add_argument('--cxl-vmem-test', help='online vmem as system ram', required=False, default="")
parser.add_argument('--create-dcR', help='create a dc Region for a memdev', required=False, default="")
parser.add_argument('-M','--mode', help='DC decoder mode (ram_a)',
                    required=False, default="ram_a")
parser.add_argument('--dcd-test', help='dcd test workflow for a memdev', required=False, default="")
parser.add_argument('--issue-qmp', help='Issue QMP command from a file to VM', required=False, default="")
parser.add_argument('--setup-mctp', help='setup mctp test software', action='store_true')
parser.add_argument('--setup-mctp-usb', help='setup mctp test software for mctp over usb setup', action='store_true')
parser.add_argument('--setup-mctp-fm', help='setup mctp test software on FM', action='store_true')
parser.add_argument('--try-mctp', help='try mctp test', action='store_true')
# ras related commands
parser.add_argument('--install-ras-tools', help='install ras related tool', action='store_true')
parser.add_argument('--inject-aer', help='inject aer', required=False, default="")
parser.add_argument('--test-fm', help='run FMAPI test workflow', action='store_true')
parser.add_argument('--test-libcxlmi', help='run libcxlmi test workflow', action='store_true')
parser.add_argument('--install-libcxlmi', help='install libcxlmi on VM', action='store_true')
parser.add_argument('--install-libcxlmi-fm', help='install libcxlmi on FM VM', action='store_true')
parser.add_argument('--start-vm', help='start vm with specified setup (regular, mctp)', required=False, default="")
parser.add_argument('--setup-kernel-arm', help='configure and build kernel for aarch64', action='store_true')
parser.add_argument('--build-kernel-arm', help='only build kernel for aarch64', action='store_true')
parser.add_argument('--start-arm', help='start a VM for aarch64', action='store_true')
parser.add_argument('--test-einj', help='workflow: testing aer inject with [topo] as parameter', required=False, default="")
parser.add_argument('--attach-fm', help='Attach FM VM to an existing VM', action='store_true')

parser.add_argument('--set-vars', help='choose a config file as .vars.config',
                    required = False, default="")

args = vars(parser.parse_args())

if args["verbose"]:
    print(args)

if args["set_vars"]:
    f = args["set_vars"]
    print("This will copy %s as .vars.config"%f)
    if os.path.exists(f):
        cmd = "cp %s .vars.config"%f
        sh_cmd(cmd, echo = True)
    else:
        print("Error: file %s not found!!"%f);
    exit(0)

user=sh_cmd("whoami")
tmp_config="/tmp/.vars.config-%s"%user
config=".vars.config"
env_dict = {}
if os.path.exists(config):
    env_dict = parse_config(config)
    if not os.path.exists(tmp_config) or not filecmp.cmp(config, tmp_config):
        shutil.copy(config, tmp_config)
elif os.path.exists(tmp_config):
    env_dict = parse_config(tmp_config)
    config = system_path("cxl_test_tool_dir")+"/.vars.config"
    if args["verbose"]:
        print("Note: We always use config in %s if current directoy does not have one"%config)
    env_dict = parse_config(config)
else:
    print("No .vars.config file found! Use run_vars.example as an example to create one")
    exit(1)
if args["verbose"]:
    print("\nPrint out the environment variable:")
    print(env_dict)
    print("\n")

QEMU=system_path("QEMU_ROOT")+"/build/qemu-system-x86_64"
KERNEL_PATH=system_path("KERNEL_ROOT")+"/arch/x86/boot/bzImage"

if args["extra"]:
    os.environ["qemu_extra_opt"] = args["extra"]
if args["mode"]:
    os.environ["dc_mode"] = "dynamic_" + args["mode"]

if args["setup_qemu"]:
    tools.setup_qemu(url=os.getenv("qemu_url"), branch=os.getenv("qemu_branch"), qemu_dir=system_path("QEMU_ROOT"))
if args["setup_qemu_arm"]:
    print("NOTE: arm cxl support for Qemu has not upstreamed yet, make sure you use jonathans local tree and branch")
    print("url: https://gitlab.com/jic23/qemu.git")
    print("branch: cxl-2024-08-20")
    ch=input("Are you want to continue without update .vars.config? (Y/N):")
    if not ch or ch.lower() != "y":
        exit(0)

    tools.setup_qemu(url=os.getenv("qemu_url"), branch=os.getenv("qemu_branch"), qemu_dir=system_path("QEMU_ROOT"), arch="aarch64-softmmu", debug=False)
if args["setup_kernel"]:
    tools.setup_kernel(url=os.getenv("kernel_url"), branch=os.getenv("kernel_branch"), kernel_dir=system_path("KERNEL_ROOT"))
if args["setup_kernel_fm"]:
    mctp.setup_kernel(kernel_dir=system_path("FM_KERNEL_ROOT"))
if args["build_qemu"]:
    tools.build_qemu(qemu_dir=system_path("QEMU_ROOT"))
if args["build_kernel"]:
    tools.build_kernel(kernel_dir=system_path("KERNEL_ROOT"))
if args["kconfig"]:
    tools.configure_kernel(kernel_dir=system_path("KERNEL_ROOT"))

if args["create_image"]:
    create_qemu_image(img_path=system_path("QEMU_IMG"))

if args["raw"] and not args["topo"]:
    parser.error('--raw requires --topo/-T')

if args["topo"]:
    if args["raw"]:
        topo = args["topo"]
    else:
        topo = cxl.find_topology(args["topo"])
        if not topo:
            print("No valid static topology found!")
            exit(1)

if args["create_topo"]:
    file = tools.system_path("cxl_test_tool_dir") + "/.cxl-topology.xml"
    topo=gen_cxl_topology(file=file)

if args["run"] or args["run_direct"]:
    if not topo:
        topo=cxl.find_topology("RP1")
    direct = False
    if args["run_direct"]:
        direct = True
    run_qemu(qemu=QEMU, topo=topo, kernel=KERNEL_PATH, accel_mode=args["accel"], run_direct = direct)

if args["login"]:
    login_vm()
if args["login_fm"]:
    port = tools.system_env("ssh_port")
    port = int(port) + 1
    login_vm(ssh_port = port)

if args["poweroff"] or args["shutdown"]:
    shutdown_vm()
if args["poweroff_fm"] or args["shutdown_fm"]:
    port = tools.system_env("ssh_port")
    port = int(port) + 1
    shutdown_vm(ssh_port = port)

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
    install_ndctl(dir=ndctl_dir)
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

cxl_test_tool_dir=system_path("cxl_test_tool_dir")
if args["setup_mctp"]:
    mctp.mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp.sh")

if args["setup_mctp_usb"]:
    mctp.mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp-usb.sh")

if args["setup_mctp_fm"]:
    os.environ["ssh_port"] = str(int(tools.system_env("ssh_port")) + 1)
    mctp.mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp.sh")
    os.environ["ssh_port"] = str(int(tools.system_env("ssh_port")) - 1)
if args["try_mctp"]:
    mctp.try_fmapi_test()

if args["install_ras_tools"]:
    ras.install_ras_tools();
if args["inject_aer"]:
    ras.inject_aer(args["inject_aer"])
if args["test_fm"]:
    mctp.run_fm_test()
if args["test_libcxlmi"]:
    libcxlmi_branch=tools.system_env("libcxlmi_branch")
    libcxlmi_url=tools.system_env("libcxlmi_url")
    if not libcxlmi_branch:
        libcxlmi_branch = "main"
    if not libcxlmi_url:
        mctp.run_libcxlmi_test(branch=libcxlmi_branch)
    else:
        mctp.run_libcxlmi_test(url=libcxlmi_url, branch=libcxlmi_branch)

if args["install_libcxlmi"]:
    libcxlmi_branch=tools.system_env("libcxlmi_branch")
    libcxlmi_url=tools.system_env("libcxlmi_url")
    if not libcxlmi_branch:
        libcxlmi_branch = "main"
    if not libcxlmi_url:
        mctp.install_libcxlmi(branch=libcxlmi_branch)
    else:
        mctp.install_libcxlmi(url=libcxlmi_url, branch=libcxlmi_branch)

if args["install_libcxlmi_fm"]:
    os.environ["ssh_port"] = str(int(tools.system_env("ssh_port")) + 1)
    libcxlmi_branch=tools.system_env("libcxlmi_branch")
    libcxlmi_url=tools.system_env("libcxlmi_url")
    if not libcxlmi_branch:
        libcxlmi_branch = "main"
    if not libcxlmi_url:
        mctp.install_libcxlmi(branch=libcxlmi_branch)
    else:
        mctp.install_libcxlmi(url=libcxlmi_url, branch=libcxlmi_branch)
    os.environ["ssh_port"] = str(int(tools.system_env("ssh_port")) - 1)

if args["start_vm"]:
    if args["start_vm"] == "mctp":
        mctp.setup_vm_for_mctp()
    else:
        if not topo:
            topo=cxl.find_topology("RP1")
        run_qemu(qemu=QEMU, topo=topo, kernel=KERNEL_PATH)

if args["setup_kernel_arm"]:
    kernel_dir=system_path("KERNEL_ROOT")
    arm.setup_kernel_arm(kernel=kernel_dir)
if args["build_kernel_arm"]:
    kernel_dir=system_path("KERNEL_ROOT")
    arm.build_kernel_arm(kernel=kernel_dir)
if args["start_arm"]:
    if not topo:
        topo=cxl.find_topology("RP1")
    qemu_dir=system_path("QEMU_ROOT")
    kernel_img=system_path("KERNEL_ROOT")+"/arch/arm64/boot/Image"
    bios=system_path("BIOS")
    arm.start_vm(qemu_dir=qemu_dir, topo=topo, kernel=kernel_img, bios=bios)
if args["test_einj"]:
    ras.test_aer_inject(args['test_einj'])

if args["attach_fm"]:
    topo_file = tools.system_env("cxl_test_log_dir") + "/topo0"
    port_offset = 1
    if not os.path.exists(topo_file):
        print("No VM has been started yet")
        exit(1)
    topo = sh_cmd("cat %s"%topo_file)
    if "allow-fm-attach=on" not in topo or "mctp-buf-init=on" not in topo:
        print("The target VM must have share-mb and mb-share-init on")
        exit(1)

    qemu_dir=system_path("QEMU_ROOT")
    kernel_img=system_path("FM_KERNEL_ROOT")+"/arch/x86_64/boot/bzImage"
    qemu_img = system_path("FM_QEMU_IMG")
    topo = cxl.find_topology(args["topo"])
    run_qemu(qemu=QEMU, topo=topo, kernel=kernel_img, qemu_img = qemu_img, port_offset = 1, allow_multivm=True)
