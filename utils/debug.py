import subprocess
import time

def gdb_process(pid):
    gdb_command = ["gdb","-tui", "-p", "%s"%pid]
    subprocess.run(gdb_command)
