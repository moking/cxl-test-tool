import subprocess;
import time
import psutil
import json

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
    return sh_cmd("ssh root@localhost -p %s \"%s\""%(ssh_port,cmd), echo=echo)

def path_exist_on_vm(path, port="2024"):
    cmd="if [ -e %s ]; then echo 1; else echo 0; fi"%(path)
    rs = execute_on_vm(cmd, ssh_port=port)
    if rs != "0":
        return True
    else:
        return False

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
