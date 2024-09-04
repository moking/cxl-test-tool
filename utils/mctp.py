import utils.tools as tools

def install_mctp_pkg():
    print("install mctp program")
    url="https://github.com/CodeConstruct/mctp.git"
    mctp_dir="/tmp/mctp"
    
    if tools.path_exist_on_vm("/etc/systemd/system/mctpd.service"):
        print("mctpd service already configured, skip")
        return

    tools.install_packages_on_vm("libsystemd-dev python3-pytest")
    if not tools.path_exist_on_vm(mctp_dir):
        tools.execute_on_vm("git clone %s %s"%(url, mctp_dir), echo=True)
        tools.execute_on_vm("cd %s; git reset --hard 69ed224ff9b5206ca7f3a5e047a9da61377d2ca7"%mctp_dir, echo=True)

    tools.execute_on_vm("cd %s; meson setup obj; ninja -C obj; meson install -C obj"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cp conf/mctpd-dbus.conf /etc/dbus-1/system.d/"%mctp_dir, echo=True)
    tools.execute_on_vm("cd %s; cat conf/mctpd.service | sed 's/sbin/local\\/sbin/' > /etc/systemd/system/mctpd.service"%mctp_dir, echo=True)


def mctp_setup(mctp_sh):
    install_mctp_pkg()
    remote_file="/tmp/mctp-setup.sh"
    tools.copy_to_remote(mctp_sh, dst=remote_file)
    tools.execute_on_vm("bash %s"%remote_file)

def try_fmapi_test():
    url="https://github.com/moking/cxl-fmapi-tests-clone.git"
    test_dir="/tmp/fmapi-test"
    if not tools.path_exist_on_vm(test_dir):
        tools.execute_on_vm("git clone %s %s"%(url, test_dir))
    cmd="cd %s; gcc cxl-mctp-test.c -o cxl-mctp-test"%test_dir
    tools.execute_on_vm(cmd, echo=True)
    cmd="cd %s; ./cxl-mctp-test 8; ./cxl-mctp-test 9; ./cxl-mctp-test 10"%test_dir
    tools.execute_on_vm(cmd, echo=True)



