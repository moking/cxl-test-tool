import subprocess;
import time
import psutil

def sh_cmd(cmd):
    output = subprocess.getoutput(cmd)
    #print(cmd, " cmd out:", output)
    return output

def bg_cmd(cmd, run_log="/tmp/qemu.log"):
    fd=open(run_log, "w")
    process = subprocess.Popen(cmd, shell=True, stdout=fd, stderr=fd)  
    time.sleep(2)
    subprocess.run(['stty', 'sane'])

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

def execute_on_vm(cmd, ssh_port="2024"):
    return sh_cmd("ssh root@localhost -p %s \"%s\""%(ssh_port,cmd))

def path_exist_on_vm(path, port="2024"):
    cmd="if [ -d %s ]; then echo 1; else echo 0; fi"%(path)
    rs = execute_on_vm(cmd, ssh_port=port)
    if rs != "0":
        return True
    else:
        return False


