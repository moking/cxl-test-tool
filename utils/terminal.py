import time
import subprocess
import utils.tools as tool
# Define the VM's SSH details

password = None  # Use None if using a private key

def gdb_on_vm(prog, hostname="localhost"):
    username = tool.system_env("vm_usr")
    if not username:
        username = "root"
    if not tool.vm_is_running():
        print("VM is not running, exit")
        return
    port = tool.system_env("ssh_port")
    if not port:
        port = 2024
    subprocess.run("ssh %s@%s -p %s \"%s\""%(username, hostname, port, prog), shell=True)

def login_vm(hostname="localhost", ssh_port = ""):
    username = tool.system_env("vm_usr")
    if not username:
        username = "root"
    if not tool.vm_is_running():
        print("VM is not running, exit")
        return
    if not ssh_port:
        ssh_port = tool.system_env("ssh_port")
    if not ssh_port:
        ssh_port = 2024
    print("login with %s@localhost: %s"%(username,ssh_port))
    subprocess.run("ssh %s@%s -p %s"%(username, hostname, ssh_port), shell=True)
