import utils.tools as tool
import os
import time


pkgs="build-essential libncurses-dev bison flex libssl-dev libelf-dev bc qemu-efi-aarch64 gcc-aarch64-linux-gnu"

def setup_kernel_arm(kernel, echo=True):
    kernel=os.path.expanduser(kernel)
    if not os.path.exists(kernel):
        print("kernel source code directory not found, exit")
        print("call setup_kernel to git clone the kernel repos..")
        url=os.getenv("kernel_url");
        branch=os.getenv("kernel_branch");
        cmd="git clone -b %s --single-branch %s %s"%(branch, url, kernel)
        tool.exec_shell_direct(cmd, echo=True)

    tool.install_packages(pkgs)
    if not tool.package_installed("gcc-aarch64-linux-gnu"):
        print("No gcc tool for aarch64 installed, exit")
        return
    cmd="cd %s; make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig; make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- menuconfig"%kernel
    tool.exec_shell_direct(cmd, echo=echo);
    cmd="cd %s; make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j16" %kernel
    tool.exec_shell_direct(cmd, echo=echo);
    cmd="export ARCH=arm64; export CROSS_COMPILE=aarch64-linux-gnu-;cd %s; sudo make modules_install"%kernel
    tool.exec_shell_direct(cmd, echo=echo);

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
    tool.exec_shell_direct(cmd, echo=echo);

extra_opts="-s"
wait_flag="nowait"
format="raw"
num_cpus="4"
accel_mode="tcg"
ssh_port="2024"
status_file="/tmp/qemu-status"
run_log="/tmp/qemu.log"
net_config="-netdev user,id=network0,hostfwd=tcp::%s-:22 -device e1000,netdev=network0"%ssh_port
SHARED_CFG="-qmp tcp:localhost:4444,server,wait=off"
initrd_img="/home/fan/arm/initrd.img-6.1.0-25-arm64"

def copy_host_ssh_key(img, img_format="raw"):
    rs = False
    if not os.path.exists(img):
        print("%s image not found"%img)
        return False

    cmd = "mkdir /tmp/mnt"
    tool.sh_cmd(cmd)

    if img_format == "raw":
        cmd = "sudo mount %s /tmp/mnt"%img
        tool.sh_cmd(cmd)
    else:
        cmd = "sudo modprobe nbd"
        tool.sh_cmd(cmd)
        cmd = "sudo qemu-nbd --connect=/dev/nbd0 %s"%img
        tool.sh_cmd(cmd, echo=True)
        time.sleep(1)
        cmd = "sudo mount /dev/nbd0p1 /tmp/mnt"
        tool.sh_cmd(cmd, echo=True)

    cmd = "mount | grep -c /tmp/mnt"
    cnt = tool.sh_cmd(cmd)
    if cnt == "0":
        print("Mount image seems failed, please check")
        cmd = "sudo umount /tmp/mnt"
        tool.sh_cmd(cmd, echo=True)
        if img_format != "raw":
            cmd = "sudo qemu-nbd -d /dev/nbd0"
            tool.sh_cmd(cmd, echo=True)
        return False
    cmd = "ls ~/.ssh | grep .pub"
    files = tool.sh_cmd(cmd)
    files=files.split()
    for f in files:
        cmd = "cat ~/.ssh/%s | sudo tee %s;"%(f, "/tmp/mnt/root/.ssh/authorized_keys")
        tool.sh_cmd(cmd,echo=True)
        rs = True
        break

    cmd = "sudo umount /tmp/mnt"
    tool.sh_cmd(cmd, echo=True)
    if img_format != "raw":
        cmd = "sudo qemu-nbd -d /dev/nbd0"
        print(tool.sh_cmd(cmd, echo=True))
    return rs


def start_vm(qemu_dir, topo, kernel, bios=""):
    bin=qemu_dir+"/build/qemu-system-aarch64"

    if tool.vm_is_running():
        print("VM is running, exit")
        return;

    if not os.path.exists(bin):
        print("QEMU for aarch64 not found under %s, exit"%qemu_dir)
        print("try to build it with --setup-qemu-arm")
        return

    pkg="qemu-efi-aarch64"
    tool.install_packages(pkg)

    img=os.getenv("QEMU_IMG")

    if not os.path.exists(img):
        print("Qemu image file not found!!!")
        url="https://cdimage.debian.org/cdimage/cloud/sid/daily/20240923-1879/debian-sid-nocloud-arm64-daily-20240923-1879.qcow2"
        print("Downloading from: %s" %url)
        cmd="wget %s -O %s"%(url, img)
        tool.exec_shell_direct(cmd)
        cmd = "file %s"%img
        tool.exec_shell_direct(cmd)
        rs = input("Continue to boot VM? (Y/N): ")
        if not rs or rs.lower() != "y":
            return

    if not copy_host_ssh_key(img, "qcow2"):
        print("Warning: copy host key to VM failed, need mannual operation for ssh")

    if not bios or not os.path.exists(bios):
        print("Cannot find QEMU_EFI.fd file")
        print("Try to build one...")
        tool.install_packages("iasl acpica-tools")
        cmd=" mkdir /tmp/tianocore; \
                cd /tmp/tianocore; \
                git clone https://git.linaro.org/uefi/uefi-tools.git; \
                git clone https://github.com/tianocore/edk2.git; \
                cd edk2; \
                git submodule update --init --recursive; \
                cd ../uefi-tools; \
                git submodule update --init --recursive; \
                cd ..; \
                uefi-tools/edk2-build.sh armvirtqemu64;"
        tool.exec_shell_direct(cmd)
        file = "/tmp/tianocore/Build/ArmVirtQemu-AARCH64/RELEASE_GCC5/FV/QEMU_EFI.fd"
        if not os.path.exists(file):
            print("Create bios failed, goto /tmp/tianocore and run uefi-tools/edk2-build.sh armvirtqemu64 for more info")
            return
        if not bios:
            bios = file
        else:
            cmd = "cp %s %s"%(file, bios)
            tool.exec_shell_direct(cmd)

    topo_abc= " \
    -object memory-backend-ram,size=4G,id=mem0 \
    -numa node,nodeid=0,cpus=0-3,memdev=mem0 \
    -object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem3,share=on,mem-path=/tmp/cxltest3.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem4,share=on,mem-path=/tmp/cxltest4.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa2,share=on,mem-path=/tmp/lsa2.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa3,share=on,mem-path=/tmp/lsa3.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa4,share=on,mem-path=/tmp/lsa4.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-mem5,share=on,mem-path=/tmp/cxltest5.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem6,share=on,mem-path=/tmp/cxltest6.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem7,share=on,mem-path=/tmp/cxltest7.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-mem8,share=on,mem-path=/tmp/cxltest8.raw,size=256M,align=256M \
    -object memory-backend-file,id=cxl-lsa5,share=on,mem-path=/tmp/lsa5.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa6,share=on,mem-path=/tmp/lsa6.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa7,share=on,mem-path=/tmp/lsa7.raw,size=1M,align=1M \
    -object memory-backend-file,id=cxl-lsa8,share=on,mem-path=/tmp/lsa8.raw,size=1M,align=1M \
    -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
    -device cxl-rp,port=0,bus=cxl.1,id=root_port0,chassis=0,slot=2 \
    -device cxl-rp,port=1,bus=cxl.1,id=root_port2,chassis=0,slot=3 \
    -device virtio-rng-pci,bus=root_port2 -device cxl-upstream,port=33,bus=root_port0,id=us0,multifunction=on,addr=0.0 \
    -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
    -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
    -device cxl-downstream,port=2,bus=us0,id=swport2,chassis=0,slot=6 \
    -device cxl-downstream,port=3,bus=us0,id=swport3,chassis=0,slot=7 \
    -device cxl-type3,bus=swport0,memdev=cxl-mem1,id=cxl-pmem0,lsa=cxl-lsa1,sn=3 \
    -device cxl-type3,bus=swport1,memdev=cxl-mem2,id=cxl-pmem1,lsa=cxl-lsa2,sn=4 \
    -device cxl-type3,bus=swport2,memdev=cxl-mem3,id=cxl-pmem2,lsa=cxl-lsa3,sn=5 \
    -device cxl-type3,bus=swport3,memdev=cxl-mem4,id=cxl-pmem3,lsa=cxl-lsa4,sn=6 \
    -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k "

    #kernel="/home/fan/arm/vmlinuz-6.1.0-25-arm64"
    usr=tool.sh_cmd("whoami")
    print("Starting VM...")
    if ".qcow" in img:
        format = "qcow2"
    else:
        format="raw"
    args = " %s"%extra_opts +\
            " -M virt,nvdimm=on,gic-version=3,cxl=on,ras=on"+\
            " -m 4G,maxmem=8G,slots=8"+\
            " -cpu max -smp %s"%num_cpus + \
            " -kernel %s"%kernel +\
            " -bios %s "%bios + \
            " -device pcie-root-port,id=root_port1" +\
            " -drive if=none,file=%s,format=qcow2,id=hd"%img +\
            " -device virtio-blk-pci,drive=hd" + \
            " %s"%SHARED_CFG + \
            " %s"%net_config + \
            " -append "+os.getenv("KERNEL_CMD")+ \
            " -nographic -no-reboot" +\
            " -monitor telnet:127.0.0.1:12345,server,"+wait_flag+\
            " -virtfs local,path=/home/%s,mount_tag=homeshare,security_model=mapped "%usr+ \
            " -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped " + topo
            #" -machine ras=on"
#-M virt,nvdimm=on,gic-version=3,cxl=on -m 4g,maxmem=8G,slots=8 -cpu max -smp 4 -kernel Image -drive if=none,file=debian.qcow2,format=qcow2,id=hd -device pcie-root-port,id=root_port1 -device virtio-blk-pci,drive=hd -netdev type=user,id=mynet,hostfwd=tcp::5555-:22 -qmp tcp:localhost:4445,server=on,wait=off -device virtio-net-pci,netdev=mynet,id=bob -nographic -no-reboot -append 'earlycon root=/dev/vda1 fsck.mode=skip tp_printk maxcpus=4' -monitor telnet:127.0.0.1:1234,server,nowait -bios QEMU_EFI.fd -object memory-backend-ram,size=4G,id=mem0 -numa node,nodeid=0,cpus=0-3,memdev=mem0

    print(bin+args)
    tool.write_to_file("/tmp/run-cmd", bin+args)

    run_mode = input("Do you want to run VM in current terminal (Y/N): ")
    if run_mode and run_mode.lower() == "y":
        # comment above and uncomment this line if need to login directly
        tool.exec_shell_direct(bin+args)
        return
    else:
        tool.bg_cmd(bin+args)
    print("INFO: if cannot ssh to VM after boot, make sure the ssh service is enabled on the VM, Try to login directly by using exec_shell_direct as comment above!!!")
    print("Wait for the VM to be ready...")
    cmd = "ssh root@localhost -p 2024 \"ls; echo $?\""
    tool.exec_shell_direct(cmd)
    rs = tool.execute_on_vm("ls > /dev/null; echo $?")
    while rs != "0":
        time.sleep(2)
        if not tool.vm_is_running():
            return
        rs = tool.execute_on_vm("ls > /dev/null; echo $?")
    print("VM is ready!")
    if tool.vm_is_running():
        tool.write_to_file(status_file, "QEMU:running")
        tool.write_to_file("/tmp/topo", topo);
        cmd="mount -t 9p -o trans=virtio modshare /lib/modules"
        tool.execute_on_vm(cmd, echo=True)
        cmd="mount | grep -c modules"
        rs=tool.execute_on_vm(cmd)
        cmd = "mkdir /tmp/home/; mount -t 9p -o trans=virtio homeshare /tmp/home/"
        tool.execute_on_vm(cmd, echo=True)
        if rs == "0":
            print("WARNING: make sure /lib/modules is mounted if needed")

        print("QEMU instance is up, access it: ssh root@localhost -p %s"%ssh_port)
    else:
        tool.write_to_file(status_file, "")
        print("Start Qemu failed, check /tmp/qemu.log for more information")


