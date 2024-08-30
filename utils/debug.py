import subprocess
import time
import pexpect

def gdb_process(pid):
    gdb_command = ["gdb","-tui", "-p", "%s"%pid]
    subprocess.run(gdb_command)
