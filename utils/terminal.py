import paramiko
import time
import subprocess
# Define the VM's SSH details

password = None  # Use None if using a private key

def gdb_on_vm(prog, hostname="localhost", port=2024, username="root"):
    subprocess.run("ssh %s@%s -p %s \"%s\""%(username, hostname, port, prog), shell=True)

def login_vm(hostname="localhost", port=2024, username="root"):
    subprocess.run("ssh %s@%s -p %s"%(username, hostname, port), shell=True)
