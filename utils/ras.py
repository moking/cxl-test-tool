import utils.tools as tools
import os
import re
import utils.cxl as cxl

ras_service="""
[Unit]
Description=Rasdaemon Daemon
After=syslog.target

[Service]
ExecStart=/usr/local/sbin/rasdaemon
ExecReload=/bin/kill -HUP $MAINPID
KillMode=process
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""

# start: below are rasdaemon related
def install_rasdaemon(url="https://github.com/moking/rasdaemon-clone", branch="scrub_control", dire="~/rasdaemon"):
    if not tools.vm_is_running():
        print("VM is not running, exit")
        return
    cmd="install rasdaemon..."
    print(cmd)

    if tools.path_exist_on_vm(dire):
        choice=input("%s exists, delete it before git clone (Y/N): "%dire)
        if choice and choice.lower() == "y":
            cmd="rm -rf %s"%dire
            tools.execute_on_vm(cmd, echo=True)
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)
    else:
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)

    cmd="cd %s; bash ./run-me.sh"%(dire)
    tools.execute_on_vm(cmd, echo=True)
    path="%s/rasdaemon"%dire
    if not tools.path_exist_on_vm(path):
        print("rasdaemon not createed, exit")
        return

    f="/tmp/rasdaemon.service"
    dst="/etc/systemd/system/rasdaemon.service"
    if not tools.path_exist_on_vm(dst):
        tools.write_to_file(f, ras_service)
        tools.copy_to_remote(f, dst);
        cmd="systemctl daemon-reload"
        tools.execute_on_vm(cmd)
        cmd = "systemctl enable rasdaemon"
        tools.execute_on_vm(cmd)
    cmd = "systemctl start rasdaemon"
    tools.execute_on_vm(cmd, echo=True)
    cmd = "systemctl status rasdaemon"
    tools.execute_on_vm(cmd, echo=True)

def install_mce_inject(url="https://git.kernel.org/pub/scm/utils/cpu/mce/mce-inject.git",
                   branch="master", dire="~/mce-inject"):

    cmd="install mce inject"
    print(cmd)
    if tools.path_exist_on_vm(dire):
        choice=input("%s exists, delete it before git clone (Y/N): "%dire)
        if choice and choice.lower() == "y":
            cmd="rm -rf %s"%dire
            tools.execute_on_vm(cmd, echo=True)
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)
    else:
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)

    if tools.package_installed_on_vm("flex bison"):
        tools.install_packages_on_vm("flex bison")

    cmd="cd %s; make 1>&/dev/null"%dire
    tools.execute_on_vm(cmd, echo=True)


def install_mce_test(url="https://git.kernel.org/pub/scm/linux/kernel/git/gong.chen/mce-test.git", branch="master", dire="~/mce-test"): 
    cmd="install mce test"
    print(cmd)

    if tools.path_exist_on_vm(dire):
        choice=input("%s exists, delete it before git clone (Y/N): "%dire)
        if choice and choice.lower() == "y":
            cmd="rm -rf %s"%dire
            tools.execute_on_vm(cmd, echo=True)
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)
    else:
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
        tools.execute_on_vm(cmd, echo=True)

    cmd="cd %s; make 1>&/dev/null"%dire
    tools.execute_on_vm(cmd, echo=True)


def install_aer_inject(url="https://git.kernel.org/pub/scm/linux/kernel/git/gong.chen/aer-inject.git", branch="master", dire="~/aer-inject"):
    cmd="install aer inject"
    print(cmd)

    if tools.path_exist_on_vm(dire):
        choice=input("%s exists, delete it before git clone (Y/N): "%dire)
        if choice and choice.lower() == "y":
            cmd="rm -rf %s"%dire
            tools.execute_on_vm(cmd, echo=True)
            cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
            tools.execute_on_vm(cmd, echo=True)
    else:
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, dire)
        tools.execute_on_vm(cmd, echo=True)

    cmd="cd %s; make 1>&/dev/null"%dire
    tools.execute_on_vm(cmd, echo=True)


def install_ras_tools():
    tools.install_packages_on_vm("git libtraceevent-dev libtraceevent1 pkg-config dh-autoreconf dmidecode flex")
    install_rasdaemon();
    install_mce_inject()
    install_mce_test()
    install_aer_inject();

def inject_aer(file, aer_tool_path="~/aer-inject"):
    print("Job: inject aer")
    if not os.path.exists(file):
        print("EINJ config file not found!")
        print("Example files can be found in einj-examples under the tool directory")
        return
    
    cmd = "cat %s | grep PCI_ID | tail -1 | awk \'{print $2}\'"%file
    pci_id = tools.sh_cmd(cmd)
    cmd = "lspci -v -s %s | grep 'Advanced Error' "%pci_id
    rs = tools.execute_on_vm(cmd)
    match = re.search(r'\[(\d+)\]', rs)
    offset=""
    if match:
        offset = match.group(1)
    else:
        print("Advanced Error Reporting not found for the device:%s."%pci_id)
        return
    cmd = "setpci -s %s 0x%d.l=0"%(pci_id, int(offset) + 0xe)
    rs = tools.execute_on_vm(cmd, echo = True)
    print(rs)
    cmd = "setpci -s %s 0x%d.l=0"%(pci_id, int(offset) + 0x8)
    rs = tools.execute_on_vm(cmd, echo = True)
    print(rs)
    tools.copy_to_remote(src=file, dst="/tmp/aer.input")
    cmd="dmesg -C"
    tools.execute_on_vm(cmd, echo=True)
    cmd="cd %s; ./aer-inject /tmp/aer.input"%aer_tool_path
    tools.execute_on_vm(cmd, echo=True)
    cmd="dmesg"
    tools.execute_on_vm(cmd, echo=True)

def test_aer_inject(topo):
    print("Info: testing aer with  %s topology"%topo)
    prog = tools.system_path("cxl_test_tool_dir")+"/cxl-tool.py"
    cmd = "%s --run -T %s"%(prog, topo)
    tools.exec_shell_direct(cmd)
    if not tools.vm_is_running():
        return
    tools.install_packages_on_vm("pciutils")
    cmd = "lspci"
    tools.execute_on_vm(cmd, echo = True)

    aer_tool_path="~/aer-inject"
    if not tools.path_exist_on_vm(aer_tool_path):
        install_aer_inject(dire=aer_tool_path);
    
    patch = tools.system_path("cxl_test_tool_dir") + "/test-workflows/0001-aer-inject-Add-internal-error-injection.patch"
    if not os.path.exists(patch):
        print("%s not found, skip applying"%patch)
    else:
        key = "aer-inject: Add internal error injection"
        rs = tools.execute_on_vm("cd %s; git log --oneline | head -1"%aer_tool_path)
        print(rs)
        if key in rs:
            print("Patch already applied, skip")
        else:
            tools.copy_to_remote(patch,"/tmp/aer.patch") 
            cmd = "git config --global user.email root@vm"
            rs = tools.execute_on_vm(cmd, echo = True)
            cmd = "git config --global user.name root@vm"
            rs = tools.execute_on_vm(cmd, echo = True)
            cmd = "cd %s; git am --reject %s"%(aer_tool_path, "/tmp/aer.patch")
            rs = tools.execute_on_vm(cmd, echo = True)
            print(rs)
        cmd = "cd %s; make"%aer_tool_path
        rs = tools.execute_on_vm(cmd, echo = True)
        print(rs)
        cmd = "%s/aer-inject"%aer_tool_path
        if not tools.path_exist_on_vm(cmd):
            print("%s not found"%cmd)
            return
        print("Now ready to inject error for testing...")
        cmd = "modprobe aer_inject"
        rs = tools.execute_on_vm(cmd, echo = True)
        print(rs)
        cmd = "lsmod"
        rs = tools.execute_on_vm(cmd, echo = True)
        print(rs)

