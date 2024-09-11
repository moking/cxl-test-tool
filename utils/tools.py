import subprocess;
import time
import psutil
import json
import os

def sh_cmd(cmd, echo=False):
    if echo:
        print(cmd)
    output = subprocess.getoutput(cmd)
    #print(cmd, " cmd out:", output)
    if echo:
        print(output)
    return output

def exec_shell_direct(cmd, echo=False):
    if echo:
        print(cmd)
    subprocess.run(cmd, shell=True)

def exec_shell_remote_direct(cmd, ssh_port="2024", echo=False):
    cmd="ssh root@localhost -p %s \"%s\""%(ssh_port,cmd)
    if echo:
        print(cmd)
    subprocess.run(cmd, shell=True)

def bg_cmd(cmd, run_log="/tmp/qemu.log", echo=False):
    fd=open(run_log, "w")
    if echo:
        print(cmd)
    process = subprocess.Popen(cmd, shell=True, stdout=fd, stderr=fd)  
    time.sleep(2)
    subprocess.run(['stty', 'sane'])

def copy_to_remote(src, dst="/tmp/", user="root", host="localhost", port="2024"):
    if not src:
        return;
    cmd="scp -r -P %s %s %s@%s:%s 2>&1 1>/dev/null"%(port, src, user, host, dst)
    sh_cmd(cmd, echo=True)

def package_installed(package):
    if not package:
        return False
    cmd="apt-cache policy %s | grep -w Installed"%package
    rs=sh_cmd(cmd)
    if rs:
        version=rs.split(":")[1].strip()
        if "none" in version:
            return False
        return True
    else:
        return False

def install_packages(package_str):
    packages=[]
    for i in package_str.split():
        if not package_installed(i):
            packages.append(i)
    if not packages:
        print("All packages are already installed, skip installing!")
        return;
    cmd="sudo apt-get install -y %s"%" ".join(packages)
    print(cmd)
    rs=sh_cmd(cmd)
    for i in packages:
        if not package_installed(i):
            print("%s not installed"%i)
            return
    print("All packages installed successfully")

def package_installed_on_vm(package):
    if not package:
        return False
    cmd="apt-cache policy %s | grep -w Installed"%package
    rs=execute_on_vm(cmd)
    if rs:
        version=rs.split(":")[1].strip()
        if "none" in version:
            return False
        return True
    else:
        return False


def install_packages_on_vm(package_str, user="root", host="localhost", port="2024"):
    packages=[]
    for i in package_str.split():
        if not package_installed_on_vm(i):
            packages.append(i)
    if not packages:
        print("All packages are already installed on VM, skip installing!")
        return;
    cmd="apt-get install -y %s"%" ".join(packages)
    rs=execute_on_vm(cmd)
    print(rs)

def append_to_file(file, s):
    with open(file, "a") as f:
        f.write(s)

def write_to_file(file, s):
    with open(file, "w") as f:
        f.write(s)

def process_id(name):
    for process in psutil.process_iter(['name']):
        try:
            # Check if the process name matches
            if name in process.info['name']: 
                return process.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Handle the cases where the process might terminate during iteration
            continue
    return -1

def execute_on_vm(cmd, ssh_port="2024", echo=False):
    if not vm_is_running():
        print("VM is not running, exit")
        return ""
    return sh_cmd("ssh root@localhost -p %s \"%s\""%(ssh_port,cmd), echo=echo)

def path_exist_on_vm(path, port="2024"):
    if not vm_is_running():
        print("VM is not running, exit")
        return False
    cmd="if [ -e %s ]; then echo 1; else echo 0; fi"%(path)
    rs = execute_on_vm(cmd, ssh_port=port)
    if rs != "0":
        return True
    else:
        return False

def command_found_on_vm(cmd, port="2024"):
    if not vm_is_running():
        print("VM is not running, exit")
        return False
    s="which %s | grep -c %s"%(cmd, cmd)
    rs = execute_on_vm(s, ssh_port=port)
    if rs == "0":
        return False
    return True

def parse_json(file):
    with open(file, 'r') as file:
        # Parse the JSON data into a Python dictionary
        data=[]
        try:
            data = json.load(file)
        finally:
            return data

def output_to_json_data(output):
    file="/tmp/tmp.json"
    write_to_file(file, output)
    data=parse_json(file)
    return data

def qmp_port():
    name="qemu-system"
    key="qmp"
    for process in psutil.process_iter(['name', 'cmdline']):
        try:
            # Check if the process name matches
            if name in process.info['name']:
                found=False
                cmd=process.info['cmdline']
                for c in cmd:
                    if found:
                        #ATTENTION: depends on how cmdline looks like
                        return c.split(":")[-1].split(",")[0]
                    if key in c:
                        found=True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue;

def issue_qmp_cmd(file):
    if not file:
        print("No qmp input file")
        return

    port=qmp_port()

    if not package_installed("ncat"):
        install_packages("ncat")

    cmd="cat %s|ncat localhost %s"%(file, port)
    sh_cmd(cmd, echo=True)

def setup_qemu(url, branch, qemu_dir):
    git_clone=True
    qemu_dir=os.path.expanduser(qemu_dir)
    if not qemu_dir:
        return

    package_str="libglib2.0-dev libgcrypt20-dev zlib1g-dev \
        autoconf automake libtool bison flex libpixman-1-dev bc\
        make ninja-build libncurses-dev libelf-dev libssl-dev debootstrap \
        libcap-ng-dev libattr1-dev libslirp-dev libslirp0 python3-venv"

    install_packages(package_str)

    if os.path.exists(qemu_dir):
        print("%s exists, please take care of it first before proceeding"%qemu_dir)
        cmd=input("Do you want to delete the directory and continue (Y/N):")
        if cmd and cmd.lower() == "y":
            rs=input("Do you want to continue to delete (Y/N): ")
            if rs and rs.lower() == "y":
                cmd = "rm -rf %s"%qemu_dir
                sh_cmd(cmd, echo = True)
            else:
                git_clone = False
        else:
            git_clone=False

    if git_clone:
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, qemu_dir)
        rs=sh_cmd(cmd, echo=True)
        print(rs)
        cmd="cd %s;./configure --target-list=x86_64-softmmu --enable-debug"%(qemu_dir)
        sh_cmd(cmd, echo=True)
    cmd="cd %s; make -j 16"%qemu_dir
    sh_cmd(cmd, echo=True)


def setup_kernel(url, branch, kernel_dir, kconfig=""):
    git_clone=True
    recompile=True
    kernel_dir=os.path.expanduser(kernel_dir)
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
        sh_cmd(cmd, echo=True)
    else:
        cmd=input("Want to pull updates from remote repo for branch %s (Y/N):"%branch)
        if not cmd:
            cmd="N"
        if cmd.lower() == "y":
            cmd="git pull"
            sh_cmd(cmd, echo=True)
        else:
            recompile = False
    if not kconfig:
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
                    tool_dir=os.getenv("cxl_test_tool_dir").strip("\"")
                    cmd="cp %s/kconfig.example %s/.config"%(tool_dir, kernel_dir)
                    sh_cmd(cmd, echo=True)
                else:
                    print("Unknown choice, exit")
                    return
            else:
                recompile = False
        else:
            rs=input(".config not found, configure mannually (1) or copy the example config (2): ")
            if not rs:
                rs="1"
            if rs == "1":
                subprocess.run("cd %s; make menuconfig"%kernel_dir, shell=True)
            elif rs == "2":
                cmd="cp %s/kconfig.example %s/.config"%(os.getenv("cxl_test_tool_dir"), kernel_dir)
                sh_cmd(cmd, echo=True)
            else:
                print("Unknown choice, exit")
                return
    else:
        cmd="cp %s %s/.config"%(kconfig, kernel_dir)
        sh_cmd(cmd, echo=True)

    if recompile:
        exec_shell_direct("cd %s; make -j 16"%kernel_dir, echo=True)
        exec_shell_direct("cd %s; sudo make modules_install"%kernel_dir, echo=True)

def build_qemu(qemu_dir):
    qemu_dir=os.path.expanduser(qemu_dir)
    if not os.path.exists(qemu_dir):
        print("No qemu source code found, may need run --setup-qemu")
        return
    cmd="cd %s; make -j 16"%qemu_dir
    sh_cmd(cmd, echo=True)

def build_kernel(kernel_dir):
    kernel_dir=os.path.expanduser(kernel_dir)
    if not os.path.exists(kernel_dir):
        print("No kernel source code found, may need run --setup-kernel")
        return
    cmd="cd %s; make -j 16"%kernel_dir
    exec_shell_direct("cd %s; make -j 16"%kernel_dir, echo=True)
    exec_shell_direct("cd %s; sudo make modules_install"%kernel_dir, echo=True)

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

def run_with_dcd_mctp():
    name="qemu-system"
    key1="volatile-dc-memdev"
    key2="i2c_mctp_cxl"
    has_dcd = False
    has_mctp = False
    for process in psutil.process_iter(['name', 'cmdline']):
        try:
            # Check if the process name matches
            if name in process.info['name']:
                args=process.info['cmdline']
                for arg in args:
                    if key1 in arg:
                        has_dcd = True
                    if key2 in arg:
                        has_mctp = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue;
    return has_dcd,has_mctp

def run_qemu(qemu, topo, kernel):
    user=sh_cmd("whoami")
    if vm_is_running():
        print("VM is running, exit")
        return;
    
    print("Starting VM...")
    bin=qemu
    cmd=" -s "+extra_opts+ " -kernel "+kernel+" -append "+os.getenv("KERNEL_CMD")+ \
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
        write_to_file("/tmp/topo", topo);
        print("QEMU instance is up, access it: ssh root@localhost -p %s"%ssh_port)
    else:
        write_to_file(status_file, "")
        print("Start Qemu failed, check /tmp/qemu.log for more information")


