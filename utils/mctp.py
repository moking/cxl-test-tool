import os
import shutil;
import utils.cxl as cxl
import utils.tools as tools

def install_mctp_pkg():
    url="https://github.com/CodeConstruct/mctp.git"
    mctp_dir="~/mctp"
    
    if not tools.command_found_on_vm("mctp"):
        tools.install_packages_on_vm("libsystemd-dev python3-pytest meson")
    else:
        if tools.path_exist_on_vm("/etc/systemd/system/mctpd.service"):
            print("mctpd service already configured, skip")
            return

    print("install mctp program")
    if not tools.path_exist_on_vm(mctp_dir):
        tools.execute_on_vm("git clone %s %s"%(url, mctp_dir), echo=True)
        tools.execute_on_vm("cd %s; git reset --hard 69ed224ff9b5206ca7f3a5e047a9da61377d2ca7"%mctp_dir, echo=True)

    tools.execute_on_vm("cd %s; meson setup obj; ninja -C obj; meson install -C obj"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cp conf/mctpd-dbus.conf /etc/dbus-1/system.d/"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cat conf/mctpd.service | sed 's/sbin/local\\/sbin/' > /etc/systemd/system/mctpd.service"%mctp_dir, echo=True)

# this is from mctp over usb setup
def install_mctp_pkg_usb():
    url="https://github.com/CodeConstruct/mctp.git"
    mctp_dir="/tmp/mctp"
    
    if not tools.command_found_on_vm("mctp"):
        tools.install_packages_on_vm("libsystemd-dev python3-pytest meson")
    else:
        if tools.path_exist_on_vm("/etc/systemd/system/mctpd.service"):
            print("mctpd service already configured, skip")
            return

    print("install mctp program")
    if not tools.path_exist_on_vm(mctp_dir):
        tools.execute_on_vm("git clone %s %s"%(url, mctp_dir), echo=True)

    tools.execute_on_vm("cd %s; meson setup obj; ninja -C obj; meson install -C obj"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cp conf/mctpd-dbus.conf /etc/dbus-1/system.d/"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cat conf/mctpd.service | sed 's/sbin/local\\/sbin/' > /etc/systemd/system/mctpd.service"%mctp_dir, echo=True)



def mctp_setup(mctp_sh):
    print(mctp_sh)
    if not tools.vm_is_running():
        print("VM is not running")
        return
    if "usb" in mctp_sh:
        install_mctp_pkg_usb()
    else:
        install_mctp_pkg()
    remote_file="/tmp/mctp-setup.sh"
    tools.copy_to_remote(mctp_sh, dst=remote_file)
    tools.execute_on_vm("bash %s"%remote_file, echo=True)

def try_fmapi_test():
    url="https://github.com/moking/cxl-fmapi-tests-clone.git"
    test_dir="/tmp/fmapi-test"
    if not tools.vm_is_running():
        print("VM is not running")
        return
    if not tools.path_exist_on_vm(test_dir):
        tools.execute_on_vm("git clone %s %s"%(url, test_dir))
    cmd="cd %s; gcc cxl-mctp-test.c -o cxl-mctp-test"%test_dir
    tools.execute_on_vm(cmd, echo=True)
    cmd="cd %s; ./cxl-mctp-test 8; ./cxl-mctp-test 9; ./cxl-mctp-test 10"%test_dir
    tools.execute_on_vm(cmd, echo=True)

def prepare_fm_test(topo="FM", qemu_dir=""):
    url="https://github.com/torvalds/linux"
    branch="v6.6-rc6"
    dire=os.path.expanduser("~/cxl/linux-%s"%branch)

    os.environ["KERNEL_ROOT"]=dire

    test_dir=tools.system_path("cxl_test_tool_dir")
    kconfig=test_dir+"/test-workflows/mctp/kernel.config"
    tools.setup_kernel(url=url, branch=branch, kernel_dir=dire, kconfig=kconfig)

    key="i2c-aspeed"
    cmd="cd %s; git log -n 1 | grep -c %s"%(dire, key)
    if tools.sh_cmd(cmd) == "0":
        print("Apply mctp patches ...")
        kpatch=test_dir+"/test-workflows/mctp/mctp-patches-kernel.patch"
        cmd="cd %s; git am --reject %s"%(dire, kpatch)
        tools.sh_cmd(cmd, echo=True)
        tools.build_kernel(dire)
    else:
        print("mctp patches already applied, continue...")

    if not qemu_dir:
        qemu_dir = os.path.expanduser("~/cxl/qemu-mctp")
        url="https://gitlab.com/jic23/qemu.git"
        branch="cxl-2024-08-20"
        tools.setup_qemu(url=url, branch=branch, qemu_dir=qemu_dir, reconfig=True)

    QEMU=qemu_dir+"/build/qemu-system-x86_64"
    #qpatch=test_dir+"/test-workflows/mctp/mctp-patches-qemu.patch"
    #cmd="cd %s; git am --reject %s"%(qemu_dir, qpatch)
    #tools.sh_cmd(cmd, echo=True)
    topo=cxl.find_topology(topo)
    tools.run_qemu(qemu=QEMU,topo=topo, kernel=os.getenv("KERNEL_ROOT")+"/arch/x86/boot/bzImage")
    cxl_test_tool_dir=tools.system_path("cxl_test_tool_dir")
    mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp.sh")

def run_fm_test():
    dcd, mctp = tools.run_with_dcd_mctp()
    if not mctp:
        prepare_fm_test()
    try_fmapi_test()

def install_libcxlmi(url="https://github.com/moking/libcxlmi.git", branch="main", target_dir="/tmp/libcxlmi"):
    need_start=True
    if tools.path_exist_on_vm(target_dir):
        cmd="rm -rf %s"%target_dir
        tools.execute_on_vm(cmd, echo=True)

    tools.install_packages_on_vm("meson libdbus-1-dev git cmake locales")
    cmd="git clone -b %s --single-branch %s %s"%(branch, url, target_dir)
    tools.execute_on_vm(cmd, echo=True)
    cmd="cd %s; meson setup -Dlibdbus=enabled build; meson compile -C build;"%target_dir
    tools.execute_on_vm(cmd, echo=True)
    prog = target_dir+"/build/examples/cxl-mctp"
    if tools.path_exist_on_vm(prog):
        print("INFO: Install libcxlmi succeeded, run %s on VM to test"%prog)
        return 0

    print("ERROR: Install libcxlmi failed!")
    return -1;

def run_libcxlmi_test(url="https://github.com/moking/libcxlmi.git", branch="main", target_dir="/tmp/libcxlmi"):
    need_start=True
    if tools.vm_is_running():
        dcd, mctp = tools.run_with_dcd_mctp()
        if mctp:
            need_start = False
        else:
            tools.shutdown_vm()

    if need_start:
        prepare_fm_test(topo="FM_DCD")

    if install_libcxlmi(url, branch, target_dir):
       return

    cmd = "cd %s; ./build/examples/cxl-mctp"%target_dir
    tools.execute_on_vm(cmd, echo=True)

def setup_kernel(kernel_dir):
    url="https://github.com/torvalds/linux"
    branch="v6.6-rc6"
    dire=os.path.expanduser("~/cxl/linux-%s"%branch)
    os.environ["KERNEL_ROOT"]=dire
    test_dir=tools.system_path("cxl_test_tool_dir")
    kconfig=test_dir+"/test-workflows/mctp/kernel.config"
    tools.setup_kernel(url=url, branch=branch, kernel_dir=dire, kconfig=kconfig)

    key="i2c-aspeed"
    cmd="cd %s; git log -n 1 | grep -c %s"%(dire, key)
    if tools.sh_cmd(cmd) == "0":
        print("Apply mctp patches ...")
        kpatch=test_dir+"/test-workflows/mctp/mctp-patches-kernel.patch"
        cmd="cd %s; git am --reject %s"%(dire, kpatch)
        tools.sh_cmd(cmd, echo=True)
        tools.build_kernel(dire, install = False)
    else:
        print("mctp patches already applied, continue...")

    print("Set FM_KERNEL_ROOT to %s in .vars.config"%dire)

def setup_vm_for_mctp(kernel="~/cxl/linux-v6.6-rc6", qemu_dir="~/cxl/qemu-mctp"):
    print("Setup VM for MCTP")
    cxl_test_tool_dir=tools.system_path("cxl_test_tool_dir")
    if tools.vm_is_running():
        dcd,mctp = tools.run_with_dcd_mctp()
        if mctp:
            print("VM already run with MCTP ...")
            mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp.sh")
        else:
            print("Shut down existing VM ...")
            tools.shutdown_vm()

    dire = os.path.expanduser(kernel)
    qemu_dir = os.path.expanduser(qemu_dir)

    if not dire or not qemu_dir:
        print("Kernel or qemu directory for mctp setup not found")
        return
    cmd = "cd %s; git rev-parse --abbrev-ref HEAD"%qemu_dir
    branch = tools.sh_cmd(cmd)
    if branch != "cxl-2024-08-20":
        rs = input("Qemu branch %s seems not right for MCTP setup, continue (Y/N):"%branch)
        if not rs or rs.lower() != "y":
            return

    topo="FM_DCD"
    topo=cxl.find_topology(topo)
    QEMU=qemu_dir+"/build/qemu-system-x86_64"
    tools.run_qemu(qemu=QEMU,topo=topo, kernel=kernel+"/arch/x86/boot/bzImage")
    mctp_setup(cxl_test_tool_dir+"/test-workflows/mctp.sh")
