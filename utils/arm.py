import utils.tools as tool
import os


pkgs="build-essential libncurses-dev bison flex libssl-dev libelf-dev bc qemu-efi-aarch64 gcc-aarch64-linux-gnu"

def build_kernel_arm(kernel, echo=True):
    kernel=os.path.expanduser(kernel)
    if not os.path.exists(kernel):
        print("kernel source code directory not found, exit")
        return
    tool.install_packages(pkgs)
    if not tool.package_installed("gcc-aarch64-linux-gnu"):
        print("No gcc tool for aarch64 installed, exit")
        return
    cmd="cd %s; make defconfig"%kernel
    tool.sh_cmd(cmd, echo=echo);
    cmd="export ARCH=arm64; export CROSS_COMPILE=aarch64-linux-gnu-; cd %s; make -j16"%kernel
    tool.sh_cmd(cmd, echo=echo);
    cmd="cd %s; sudo make modules_install"%kernel
    tool.sh_cmd(cmd, echo=echo);


