#!/usr/bin/env python3
"""Build a kernel tree, boot it in QEMU with a CXL topology, and check the CXL drivers.

Usage: test-workflows/kernel-test.py <kernel_dir> [-T RP1] [-A kvm] [--skip-build] [--keep-vm]

Exits 0 when every check passes and 1 otherwise, so it can be used from scripts or CI.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import psutil
import utils.cxl as cxl
import utils.tools as tools
from utils.config import parse_config

CXL_LOAD_MODULES = "cxl_acpi cxl_pci cxl_port cxl_mem"
CXL_UNLOAD_ORDER = "cxl_pmem dax_cxl cxl_pmu cxl_mem cxl_port cxl_pci cxl_acpi cxl_core"
WAIT_FOR_MEMDEV = ("for i in $(seq 20); do "
                   "ls /sys/bus/cxl/devices 2>/dev/null | grep -q '^mem' && exit 0; sleep 0.5; "
                   "done; exit 1")
DMESG_ERRORS = ("Oops", "BUG:", "WARNING:", "Call Trace:", "general protection fault", "Kernel panic")

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print("[%s] %s" % ("PASS" if ok else "FAIL", name), flush=True)
    if detail and not ok:
        print("       " + detail.replace("\n", "\n       "), flush=True)
    return ok


def run(cmd, cwd=None):
    print("+ " + cmd, flush=True)
    return subprocess.run(cmd, shell=True, cwd=cwd).returncode == 0


class Guest:
    def __init__(self, user, port):
        self.user = user
        self.port = str(port)
        self.sudo = "" if user == "root" else "sudo "

    def run(self, cmd, timeout=120):
        ssh = ["ssh", "-p", self.port,
               "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
               "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
               "-o", "LogLevel=ERROR",
               "%s@localhost" % self.user, cmd]
        try:
            p = subprocess.run(ssh, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 255, "timed out after %ds" % timeout
        return p.returncode, (p.stdout + p.stderr).strip()


def find_config(path):
    if path:
        return path if os.path.exists(path) else ""
    for c in (".vars.config",
              os.path.join(TOOL_DIR, ".vars.config"),
              "/tmp/.vars.config-%s" % tools.sh_cmd("whoami")):
        if os.path.exists(c):
            return c
    return ""


def kconfig_value(kernel_dir, name):
    with open(os.path.join(kernel_dir, ".config")) as f:
        for line in f:
            if line.startswith(name + "="):
                return line.strip().split("=", 1)[1]
    return ""


def prepare_config(kernel_dir):
    config = os.path.join(kernel_dir, ".config")
    if not os.path.exists(config):
        print("No .config in %s, starting from kconfig.example" % kernel_dir)
        shutil.copy(os.path.join(TOOL_DIR, "kconfig.example"), config)
    if not run("make olddefconfig", cwd=kernel_dir):
        return False
    if kconfig_value(kernel_dir, "CONFIG_CXL_BUS") not in ("y", "m"):
        print("CONFIG_CXL_BUS is not enabled in %s" % config)
        return False
    return True


def build_kernel(kernel_dir, jobs):
    if not run("make -j%d" % jobs, cwd=kernel_dir):
        return False
    return run("sudo make modules_install INSTALL_MOD_PATH=/opt/", cwd=kernel_dir)


def kernel_release(kernel_dir):
    p = subprocess.run(["make", "-s", "kernelrelease"], cwd=kernel_dir,
                       capture_output=True, text=True)
    return p.stdout.strip()


def our_qemu(gdb_port):
    key = "tcp::%s" % gdb_port
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if "qemu-system" in (p.info["name"] or "") and key in (p.info["cmdline"] or []):
                return p
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def boot_vm(qemu, topo, bzimage, accel):
    saved_stdin = sys.stdin
    with open(os.devnull) as devnull:
        # run_qemu asks whether to delete backing files from a previous run; EOF answers yes.
        sys.stdin = devnull
        try:
            tools.run_qemu(qemu=qemu, topo=topo, kernel=bzimage, accel_mode=accel)
        finally:
            sys.stdin = saved_stdin


def wait_for_ssh(guest, gdb_port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not our_qemu(gdb_port):
            print("QEMU exited while the guest was booting")
            return False
        rc, _ = guest.run("true", timeout=15)
        if rc == 0:
            return True
        time.sleep(5)
    print("Guest did not answer SSH within %ds" % timeout)
    return False


def shutdown_vm(guest, gdb_port):
    guest.run(guest.sudo + "poweroff", timeout=15)
    for _ in range(60):
        if not our_qemu(gdb_port):
            print("VM is powered off")
            return
        time.sleep(1)
    p = our_qemu(gdb_port)
    if p:
        print("QEMU did not exit after poweroff, killing pid %d" % p.pid)
        p.kill()


def tail(path, lines=40):
    if not os.path.exists(path):
        return ""
    with open(path, errors="replace") as f:
        return "".join(f.readlines()[-lines:])


def run_cxl_checks(guest, release, cxl_modular, log_dir):
    rc, out = guest.run("uname -r")
    check("guest runs the new kernel (%s)" % release, rc == 0 and out == release,
          "guest reports: %s" % out)

    rc, _ = guest.run("test -d /lib/modules/$(uname -r)")
    if not check("kernel modules are visible in the guest", rc == 0,
                 "/opt/lib/modules on the host must be mounted at /lib/modules in the guest "
                 "(modshare 9p mount, set up by ./cxl-tool.py --create-image)"):
        return

    rc, out = guest.run(guest.sudo + "modprobe -a " + CXL_LOAD_MODULES)
    check("load CXL drivers", rc == 0, out)

    rc, _ = guest.run(WAIT_FOR_MEMDEV)
    _, devices = guest.run("ls /sys/bus/cxl/devices")
    check("CXL memdev appears in /sys/bus/cxl/devices", rc == 0, "devices: %s" % devices)

    rc, _ = guest.run("command -v cxl")
    if rc != 0:
        print("[SKIP] cxl list: cxl CLI not installed in the guest (./cxl-tool.py --install-ndctl)")
    else:
        rc, out = guest.run("cxl list -M")
        check("cxl list reports memdevs", rc == 0 and '"memdev"' in out, out)

    if not cxl_modular:
        print("[SKIP] unload/reload: CONFIG_CXL_BUS=y, CXL core is built in")
    else:
        unload = ("for m in %s; do grep -q \"^$m \" /proc/modules || continue; "
                  "%smodprobe -r $m || exit 1; done; ! grep -q '^cxl_' /proc/modules"
                  % (CXL_UNLOAD_ORDER, guest.sudo))
        rc, out = guest.run(unload)
        _, left = guest.run("grep '^cxl_' /proc/modules | cut -d' ' -f1")
        check("unload CXL drivers", rc == 0, "%s\nstill loaded: %s" % (out, left))

        rc, out = guest.run(guest.sudo + "modprobe -a " + CXL_LOAD_MODULES)
        if rc == 0:
            rc, out = guest.run(WAIT_FOR_MEMDEV)
        check("reload CXL drivers and re-enumerate memdev", rc == 0, out)

    rc, dmesg = guest.run(guest.sudo + "dmesg")
    dmesg_log = os.path.join(log_dir, "kernel-test-dmesg.log")
    tools.write_to_file(dmesg_log, dmesg + "\n")
    hits = [l for l in dmesg.splitlines() if any(e in l for e in DMESG_ERRORS)]
    check("no oops/BUG/WARNING in dmesg", rc == 0 and not hits,
          "\n".join(hits[:40]) + "\nfull log: %s" % dmesg_log)


def main():
    parser = argparse.ArgumentParser(
        description="Build a kernel, boot it in QEMU with a CXL topology, and check the CXL drivers")
    parser.add_argument("kernel_dir", help="Linux source tree to build and test")
    parser.add_argument("-T", "--topo", default="RP1",
                        help="built-in topology name from utils/cxl.py (default: RP1)")
    parser.add_argument("-A", "--accel", default="kvm",
                        help="kvm or tcg (default: kvm, falls back to tcg without /dev/kvm)")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 16,
                        help="parallel make jobs (default: number of CPUs)")
    parser.add_argument("--boot-timeout", type=int, default=300,
                        help="seconds to wait for the guest to answer SSH (default: 300)")
    parser.add_argument("--config", default="",
                        help=".vars.config to use (default: ./.vars.config, then the tool directory)")
    parser.add_argument("--skip-build", action="store_true",
                        help="boot the existing build without reconfiguring or rebuilding")
    parser.add_argument("--keep-vm", action="store_true",
                        help="leave the VM running after the checks")
    args = parser.parse_args()

    kernel_dir = os.path.abspath(os.path.expanduser(args.kernel_dir))
    if not os.path.exists(os.path.join(kernel_dir, "Makefile")):
        print("%s does not look like a kernel source tree" % kernel_dir)
        return 1

    config = find_config(args.config)
    if not config:
        print("No .vars.config found; copy run_vars.example to .vars.config and edit it")
        return 1
    parse_config(config)
    print("Using config %s" % config)

    if tools.is_bare_metal():
        print("ssh_port is 22 (bare metal); this workflow only drives a QEMU guest")
        return 1
    topo = cxl.find_topology(args.topo)
    if not topo:
        print("Unknown topology %s" % args.topo)
        return 1
    qemu = tools.system_path("QEMU_ROOT") + "/build/qemu-system-x86_64"
    if not os.path.exists(qemu):
        print("%s not found; run ./cxl-tool.py --setup-qemu or --build-qemu" % qemu)
        return 1
    if not os.path.exists(tools.system_path("QEMU_IMG")):
        print("QEMU_IMG %s not found; run ./cxl-tool.py --create-image" % tools.system_path("QEMU_IMG"))
        return 1
    if tools.vm_is_running():
        print("A QEMU VM is already running; shut it down first (./cxl-tool.py --poweroff)")
        return 1

    if not args.skip_build:
        if not check("configure kernel", prepare_config(kernel_dir)):
            return 1
        if not check("build kernel and install modules to /opt/lib/modules",
                     build_kernel(kernel_dir, args.jobs)):
            return 1
    bzimage = os.path.join(kernel_dir, "arch/x86/boot/bzImage")
    if not os.path.exists(bzimage):
        print("%s not found" % bzimage)
        return 1
    release = kernel_release(kernel_dir)
    cxl_modular = kconfig_value(kernel_dir, "CONFIG_CXL_BUS") == "m"

    log_dir = tools.system_path("cxl_test_log_dir") or "/tmp/"
    qemu_log = os.path.join(log_dir, "qemu0.log")
    gdb_port = tools.system_env("gdb_port") or "1234"
    guest = Guest(tools.system_env("vm_usr"), tools.system_env("ssh_port"))

    boot_vm(qemu, topo, bzimage, args.accel)
    try:
        if not check("guest boots and answers SSH",
                     wait_for_ssh(guest, gdb_port, args.boot_timeout),
                     "last lines of %s:\n%s" % (qemu_log, tail(qemu_log))):
            return 1
        run_cxl_checks(guest, release, cxl_modular, log_dir)
    finally:
        if args.keep_vm:
            print("Leaving VM running: ssh %s@localhost -p %s" % (guest.user, guest.port))
        else:
            shutdown_vm(guest, gdb_port)

    failed = [name for name, ok in results if not ok]
    print("\n%d checks, %d failed" % (len(results), len(failed)))
    for name in failed:
        print("  FAIL: " + name)
    print("QEMU console log: %s" % qemu_log)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
