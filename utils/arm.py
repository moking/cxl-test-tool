import utils.tools as tool
import os
import time


pkgs="build-essential libncurses-dev bison flex libssl-dev libelf-dev bc qemu-efi-aarch64 gcc-aarch64-linux-gnu"

def setup_kernel_arm(kernel, echo=True):
    kernel=os.path.expanduser(kernel)
    if not os.path.exists(kernel):
        print("kernel source code directory not found, exit")
        return
    tool.install_packages(pkgs)
    if not tool.package_installed("gcc-aarch64-linux-gnu"):
        print("No gcc tool for aarch64 installed, exit")
        return
    cmd="export ARCH=arm64; export CROSS_COMPILE=aarch64-linux-gnu-; cd %s; make defconfig; make -j16"%kernel
    tool.exec_shell_direct(cmd, echo=echo);
    cmd="cd %s; sudo make modules_install"%kernel
    tool.sh_cmd(cmd, echo=echo);

def build_kernel_arm(kernel, echo=True):
    kernel=os.path.expanduser(kernel)
    if not os.path.exists(kernel):
        print("kernel source code directory not found, exit")
        return
    tool.install_packages(pkgs)
    if not tool.package_installed("gcc-aarch64-linux-gnu"):
        print("No gcc tool for aarch64 installed, exit")
        return
    cmd="export ARCH=arm64; export CROSS_COMPILE=aarch64-linux-gnu-; cd %s; make menuconfig; make -j16"%kernel
    tool.exec_shell_direct(cmd, echo=echo);
    cmd="cd %s; sudo make modules_install"%kernel
    tool.sh_cmd(cmd, echo=echo);


extra_opts=""
wait_flag="nowait"
format="qcow2"
num_cpus="8"
accel_mode="tcg"
ssh_port="2024"
status_file="/tmp/qemu-status"
run_log="/tmp/qemu.log"
net_config="-netdev user,id=network0,hostfwd=tcp::%s-:22 -device e1000,netdev=network0"%ssh_port
SHARED_CFG="-qmp tcp:localhost:4444,server,wait=off"
initrd_img="/home/fan/cxl/arm/initrd.img-6.1.0-25-arm64"

def start_vm(qemu_dir, topo, kernel, initrd_img=initrd_img):
    QEMU=qemu_dir+"/build/qemu-system-aarch64"
    if not os.path.exists(QEMU):
        print("QEMU for aarch64 not found, exit")
        return
    if tool.vm_is_running():
        print("VM is running, exit")
        return;
    pkg="qemu-efi-aarch64"
    tool.install_packages(pkg)

    img=os.getenv("QEMU_IMG")
    if not os.path.exists(img):
        print("Qemu image file not found!!!")
        print("Please follow instructions to create one: https://blog.jitendrapatro.me/emulating-aarch64arm64-with-qemu-part-1")
        return
    if not os.path.exists(initrd_img):
        print("The -initrd option is needed to boot arm64 image for me") 
        print("Please follow instructions to create one: https://blog.jitendrapatro.me/emulating-aarch64arm64-with-qemu-part-1")
        return

    #" -initrd %s"%initrd_img + \
    #" -initrd %s"%initrd_img + \
    print("Starting VM...")
    bin=QEMU
    cmd=" "+extra_opts+ \
            " -kernel "+kernel+ \
            " -append "+os.getenv("KERNEL_CMD")+ \
            " -cpu max" + \
            " -smp " + num_cpus + \
            " -accel "+accel_mode + \
            " "+SHARED_CFG+" "+ net_config + " "+\
            " -drive if=none,file="+img+",media=disk,format="+format+",id=hd0" +\
            " -device virtio-blk-device,drive=hd0" + \
            " -M virt,gic-version=3,cxl=on" + \
            " -m 4G,maxmem=8G,slots=8 "+ \
            " -nographic " + \
            " -monitor telnet:127.0.0.1:12345,server,"+wait_flag+\
            " -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped " + topo

    print(bin+cmd)
    tool.write_to_file("/tmp/run-cmd", cmd)
    #tool.bg_cmd(bin+cmd)
    tool.exec_shell_direct(bin+cmd)
    print("Wait for the VM to be ready...")
    cmd = "ssh root@localhost -p 2024 \"ls; echo $?\""
    tool.exec_shell_direct(cmd)
    #tool.bg_cmd(cmd)
    rs = tool.execute_on_vm("ls > /dev/null; echo $?")
    while rs != "0":
        time.sleep(2)
        rs = tool.execute_on_vm("ls > /dev/null; echo $?")
    print("VM is ready!")
    if tool.vm_is_running():
        tool.write_to_file(status_file, "QEMU:running")
        tool.write_to_file("/tmp/topo", topo);
        cmd="mount -t 9p -o trans=virtio modshare /lib/modules"
        tool.execute_on_vm(cmd, echo=True)
        cmd="mount | grep -c modules"
        rs=tool.execute_on_vm(cmd)
        if rs == "0":
            print("WARNING: make sure /lib/modules is mounted if needed")
        print("QEMU instance is up, access it: ssh root@localhost -p %s"%ssh_port)
    else:
        tool.write_to_file(status_file, "")
        print("Start Qemu failed, check /tmp/qemu.log for more information")


