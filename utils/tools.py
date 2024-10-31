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

def system_env(name):
    if not name:
        return ""
    value = os.getenv(name)
    if not value:
        if name == "ssh_port":
            return "2024"
        if name == "vm_usr":
            return "root"
        elif "branch" in name:
            return "master"
        elif name == "cxl_test_log_dir":
            return "/tmp/cxl-logs"
        else:
            print("env[%s] undefined, return empty"%name)
            return ""
    else:
        return value.strip("\"")

def exec_shell_remote_direct(cmd, echo=False):
    ssh_port=system_env("ssh_port")
    usr = system_env("vm_usr")
    cmd="ssh %s@localhost -p %s \"%s\""%(usr, ssh_port,cmd)
    if echo:
        print(cmd)
    subprocess.run(cmd, shell=True)

def bg_cmd(cmd, echo=False):
    log_dir=system_path("cxl_test_log_dir")
    if not log_dir:
        log_dir = "/tmp/"
    run_log = log_dir+"/qemu.log"
    fd=open(run_log, "w")
    if echo:
        print(cmd)
    process = subprocess.Popen(cmd, shell=True, stdout=fd, stderr=fd)  
    time.sleep(2)
    subprocess.run(['stty', 'sane'])

def copy_to_remote(src, dst="/tmp/", user="root", host="localhost"):
    port=system_env("ssh_port")
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
    #rs=sh_cmd(cmd)
    exec_shell_direct(cmd)
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


def install_packages_on_vm(package_str, user="root", host="localhost"):
    ssh_port=system_env("ssh_port")
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

def system_path(name):
    path=os.getenv(name)
    if not path:
        return ""
    return os.path.expanduser(path.strip("\""))

def append_to_file(file, s):
    with open(file, "a") as f:
        f.write(s)

def write_to_file(file, s):
    with open(file, "w") as f:
        f.write(s)

def process_id(name):
    for process in psutil.process_iter(['name', 'username']):
        try:
            # Check if the process name matches
            if name in process.info['name'] and process.info['username'] == sh_cmd("whoami"): 
                return process.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Handle the cases where the process might terminate during iteration
            continue
    return -1

def execute_on_vm(cmd, echo=False):
    ssh_port = system_env("ssh_port")
    usr = system_env("vm_usr")
    if not vm_is_running():
        print("VM is not running, exit")
        return ""
    return sh_cmd("ssh %s@localhost -p %s \"%s\""%(usr, ssh_port,cmd), echo=echo)

def path_exist_on_vm(path):
    ssh_port=system_env("ssh_port")
    if not vm_is_running():
        print("VM is not running, exit")
        return False
    cmd="if [ -e %s ]; then echo 1; else echo 0; fi"%(path)
    rs = execute_on_vm(cmd)
    if rs != "0":
        return True
    else:
        return False

def command_found_on_vm(cmd):
    if not vm_is_running():
        print("VM is not running, exit")
        return False
    s="which %s | grep -c %s"%(cmd, cmd)
    rs = execute_on_vm(s)
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

def setup_qemu(url, branch, qemu_dir, arch="x86_64-softmmu", debug=True, reconfig=True):
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
    if reconfig:
        if debug:
            cmd="cd %s;./configure --target-list=%s --enable-debug"%(qemu_dir, arch)
        else:
            cmd="cd %s;./configure --target-list=%s --disable-debug-info"%(qemu_dir, arch)
        sh_cmd(cmd, echo=True)
    cmd="cd %s; make -j 16"%qemu_dir
    sh_cmd(cmd, echo=True)
    cmd="cd %s; ls build/qemu-system-*"%qemu_dir
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
        exec_shell_direct(cmd, echo=True)
    else:
        cmd=input("Want to pull updates from remote repo for branch %s (Y/N):"%branch)
        if not cmd:
            cmd="N"
        if cmd.lower() == "y":
            cmd="git pull"
            exec_shell_direct(cmd, echo=True)
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
                    tool_dir=system_path("cxl_test_tool_dir")
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
                cmd="cp %s/kconfig.example %s/.config"%(system_path("cxl_test_tool_dir"), kernel_dir)
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
    else:
        print("Run --build-kernel to configure and compile kernel")

def build_qemu(qemu_dir):
    qemu_dir=os.path.expanduser(qemu_dir)
    if not os.path.exists(qemu_dir):
        print("No qemu source code found, may need run --setup-qemu")
        return
    cmd="cd %s; make -j 16"%qemu_dir
    sh_cmd(cmd, echo=True)
    cmd="cd %s; ls build/qemu-system-*"%qemu_dir
    sh_cmd(cmd, echo=True)

def is_bare_metal():
    ssh_port = system_env("ssh_port")
    return ssh_port == "22"
def build_kernel(kernel_dir):
    kernel_dir=os.path.expanduser(kernel_dir)
    if not os.path.exists(kernel_dir):
        print("No kernel source code found, may need run --setup-kernel")
        return
    ans = input("Do you want to run make menuconfig first before buidling (Y/N): ")
    if ans.lower() == "y":
        cmd = "cd %s; make menuconfig"%kernel_dir
        exec_shell_direct(cmd, echo=True)
    cmd="cd %s; make -j 16"%kernel_dir
    exec_shell_direct(cmd, echo=True)
    exec_shell_direct("cd %s; sudo make modules_install"%kernel_dir, echo=True)
    if is_bare_metal():
        rs = input("Install new kernel to the host (Y/N): ")
        if rs.lower() == "y":
            exec_shell_direct("cd %s; sudo make install"%kernel_dir, echo=True)

def configure_kernel(kernel_dir):
    kernel_dir=os.path.expanduser(kernel_dir)
    if not os.path.exists(kernel_dir):
        print("No kernel source code found, may need run --setup-kernel")
        return
    cmd="cd %s; make menuconfig"%kernel_dir
    exec_shell_direct(cmd, echo=True)

def vm_is_running():
    # Check bare metal if ssh port is 22.
    ssh_port = system_env("ssh_port")
    if ssh_port == "22":
        print("Notice: You are using bare metal, be carefully!!!")
        return True
    """Check if any process with the given name is alive."""
    # Iterate over all running processes
    name="qemu-system"
    usr=sh_cmd("whoami")
    for process in psutil.process_iter(['name', 'username']):
        if usr != process.info["username"]:
            continue
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

def run_qemu(qemu, topo, kernel, accel_mode=accel_mode):
    if vm_is_running():
        print("VM is running, exit")
        return;
    
    extra_opts = system_env("qemu_extra_opt")
    # update the image directory
    host_dir=system_env("cxl_host_dir")
    if host_dir:
        topo = topo.replace("/tmp",host_dir)
        if not os.path.exists(host_dir):
            sh_cmd("mkdir -p %s"%host_dir)

    ssh_port=system_env("ssh_port")
    net_config = system_env("net_config")
    log_dir = system_path("cxl_test_log_dir")
    if not log_dir:
        log_dir = "/tmp/"
    elif not os.path.exists(log_dir):
        sh_cmd("mkdir %s"%log_dir, echo=True)
    print("Starting VM...")
    bin=qemu
    home=os.getenv("HOME")

    if accel_mode == "kvm":
        cmd = "sudo chmod 666 /dev/kvm"
        sh_cmd(cmd,echo=True)

    cmd=" -s "+extra_opts+ " -kernel "+kernel+" -append "+os.getenv("KERNEL_CMD")+ \
            " -smp " +num_cpus+ \
            " -accel "+accel_mode + \
            " -serial mon:stdio "+ \
            " -nographic " + \
            " "+SHARED_CFG+" "+ net_config + " "+\
            " -monitor telnet:127.0.0.1:12345,server,"+wait_flag+\
            " -drive file="+system_path("QEMU_IMG")+",index=0,media=disk,format="+format+\
            " -machine q35,cxl=on -cpu qemu64,mce=on -m 8G,maxmem=32G,slots=8 "+ \
            " -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped "+\
            " -virtfs local,path=%s"%home+",mount_tag=homeshare,security_model=mapped "+ topo

    write_to_file("%s/run-cmd"%log_dir, cmd)
    bg_cmd(bin+cmd)
    status_file="%s/qemu-status"%log_dir
    if vm_is_running():
        write_to_file(status_file, "QEMU:running")
        write_to_file("%s/topo"%log_dir, topo);
        usr = system_path("vm_usr")
        print("QEMU instance is up, access it: ssh %s@localhost -p %s"%(usr, ssh_port))
    else:
        write_to_file(status_file, "")
        print("Start Qemu failed, check %s/qemu.log for more information"%log_dir)

def git_clone(url, branch, dst_dir):
    if os.path.exists(dst_dir) and len(os.listdir(dst_dir)) > 0:
        ch = input("%s exists, do you want to delete it before processing(y/n):")
        if ch and ch.lower() == "y":
            cmd = "rf -rf %s"%dst_dir
            exec_shell_direct(cmd)
        else:
            return False
    cmd="git clone -b %s --single-branch %s %s"%(branch, url, dst_dir)
    exec_shell_direct(cmd)
    if os.path.exists(dst_dir) and len(os.listdir(dst_dir)) > 0:
        return True;
    else:
        return False

def remote_directory_empty(path):
    if not path_exist_on_vm(path):
        return True
    cmd = "ls -A %s | wc -l"%path
    rs = execute_on_vm(cmd, echo=True)
    if rs != "0":
        return False
    return True

def git_clone_on_vm(url, branch, dst_dir):
    if not remote_directory_empty(dst_dir):
        ch = input("%s exists, do you want to delete it before processing(y/n):"%dst_dir)
        if ch and ch.lower() == "y":
            cmd = "rm -rf %s"%dst_dir
            exec_shell_remote_direct(cmd)
        else:
            return False
    cmd="git clone -b %s --single-branch %s %s"%(branch, url, dst_dir)
    exec_shell_remote_direct(cmd)
    if remote_directory_empty(dst_dir):
        return True
    else:
        return False
