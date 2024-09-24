#! /bin/bash
extra_opts=""

default_vars_file=./.vars.config
opt_vars_file=""
image_name=""
qmp_file=""

top_file=/tmp/topo.txt
cmd_file=/tmp/cmd
einj_file=""
ssh_port="2024"
dcd_last_used=""
vmem_last_used=""
pmem_last_used=""

echo '
rp=13
mem_id=0
slot=2
chassis=0
bus=1
bus_nr=12
fmw=0
' > /tmp/cxl-val


warning() {
    echo "Warning: $@"
}

error() {
    echo "Error: $@"
}

echo_task() {
    echo
    echo "** Task: $@ **"
    echo
}

same_file() {
    f1=$1
    f2=$2
    if [ "$f1" == "" -o "$f2" == "" ];then
        echo "0"
    elif [ ! -f "$f1" -o ! -f "$f2" ];then
        echo "0"

        rs=`diff -q -i -E -Z -w -B $f1 $f2`
        if [ "$rs" == "" ]; then
            echo "1"
        else
            echo "0"
        fi
    fi
}

sh_on_remote() {
    cmd="$1"
    echo root@VM\#: ssh root@localhost -p $ssh_port "$cmd"
    ssh root@localhost -p $ssh_port "$cmd"
}

raw_sh_on_remote() {
    cmd="$1"
    ssh root@localhost -p $ssh_port "$cmd"
}

ps_qemu_status() {
    ps -ef | grep qemu-system
    exit
}

copy_to_remote() {
    dst="/tmp/"
    if [ "$1" == "" ];then
        error "no source for scp command"
        exit
    fi
    if [ "$2" != "" ];then
        dst=$2
    fi
    echo "scp -r -P 2024 $1 root@localhost:$dst 2>&1 1>/dev/null"
    scp -r -P 2024 $1 root@localhost:$dst 2>&1 1>/dev/null
}

print_key_value() {
    key=$1
    value=$2
    echo -e "$key \t\t\t $value"
}

create_topology() {
    python_exists=`which python`
    if [ "$python_exists" == "" ];then
        sudo apt-get install python3 python-is-python3
    fi
    s=`python $cxl_test_tool_dir/cxl-topology-xml-parser.py -F $cxl_test_tool_dir/.cxl-topology.xml`
    echo "$s"
}

RP1="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=512M \
     -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
     -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0 \
     -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

RP1_DCD="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
	 -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=2048M \
	 -object memory-backend-file,id=cxl-dcd0,share=on,mem-path=/tmp/cxltest-dcd.raw,size=4096M \
     -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa3,share=on,mem-path=/tmp/lsa2.raw,size=512M \
     -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
     -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
     -device cxl-rp,port=1,bus=cxl.1,id=root_port14,chassis=0,slot=3 \
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,volatile-dc-memdev=cxl-dcd0,volatile-memdev=cxl-mem2,id=cxl-dcd0,num-dc-regions=2\
     -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

M2="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=512M \
    -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa2,share=on,mem-path=/tmp/lsa2.raw,size=512M \
    -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
    -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
    -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0 \
    -device cxl-rp,port=1,bus=cxl.1,id=root_port14,chassis=0,slot=3 \
    -device cxl-type3,bus=root_port14,memdev=cxl-mem2,lsa=cxl-lsa2,id=cxl-pmem1 \
    -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

HB2="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
     -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=512M \
     -object memory-backend-file,id=cxl-mem3,share=on,mem-path=/tmp/cxltest3.raw,size=512M \
     -object memory-backend-file,id=cxl-mem4,share=on,mem-path=/tmp/cxltest4.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa2,share=on,mem-path=/tmp/lsa2.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa3,share=on,mem-path=/tmp/lsa3.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa4,share=on,mem-path=/tmp/lsa4.raw,size=512M \
     -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
     -device pxb-cxl,bus_nr=222,bus=pcie.0,id=cxl.2 \
     -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0 \
     -device cxl-rp,port=1,bus=cxl.1,id=root_port14,chassis=0,slot=3 \
     -device cxl-type3,bus=root_port14,memdev=cxl-mem2,lsa=cxl-lsa2,id=cxl-pmem1 \
     -device cxl-rp,port=0,bus=cxl.2,id=root_port15,chassis=0,slot=5 \
     -device cxl-type3,bus=root_port15,memdev=cxl-mem3,lsa=cxl-lsa3,id=cxl-pmem2 \
     -device cxl-rp,port=1,bus=cxl.2,id=root_port16,chassis=0,slot=6 \
     -device cxl-type3,bus=root_port16,memdev=cxl-mem4,lsa=cxl-lsa4,id=cxl-pmem3 \
     -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.targets.1=cxl.2,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

SW="-object memory-backend-file,id=cxl-mem0,share=on,mem-path=/tmp/cxltest.raw,size=512M \
    -object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest1.raw,size=512M \
    -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=512M \
    -object memory-backend-file,id=cxl-mem3,share=on,mem-path=/tmp/cxltest3.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa0,share=on,mem-path=/tmp/lsa0.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa1.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa2,share=on,mem-path=/tmp/lsa2.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa3,share=on,mem-path=/tmp/lsa3.raw,size=512M \
    -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1 \
    -device cxl-rp,port=0,bus=cxl.1,id=root_port0,chassis=0,slot=0 \
    -device cxl-rp,port=1,bus=cxl.1,id=root_port1,chassis=0,slot=1 \
    -device cxl-upstream,bus=root_port0,id=us0 \
    -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
    -device cxl-type3,bus=swport0,memdev=cxl-mem0,lsa=cxl-lsa0,id=cxl-pmem0 \
    -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
    -device cxl-type3,bus=swport1,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem1 \
    -device cxl-downstream,port=2,bus=us0,id=swport2,chassis=0,slot=6 \
    -device cxl-type3,bus=swport2,memdev=cxl-mem2,lsa=cxl-lsa2,id=cxl-pmem2 \
    -device cxl-downstream,port=3,bus=us0,id=swport3,chassis=0,slot=7 \
    -device cxl-type3,bus=swport3,memdev=cxl-mem3,lsa=cxl-lsa3,id=cxl-pmem3 \
    -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=4k"

FM="-object memory-backend-file,id=cxl-mem1,mem-path=/tmp/t3_cxl1.raw,size=256M \
 -object memory-backend-file,id=cxl-lsa1,mem-path=/tmp/t3_lsa1.raw,size=1M \
 -object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=512M \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-type3,bus=swport0,memdev=cxl-mem1,id=cxl-pmem1,lsa=cxl-lsa1,sn=3 \
 -device cxl-type3,bus=swport2,memdev=cxl-mem2,id=cxl-pmem2,lsa=cxl-lsa2,sn=4 \
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=4,target=us0 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=5,target=cxl-pmem1 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=6,target=cxl-pmem2 \
 -device virtio-rng-pci,bus=swport1"

qemu_vm_is_running() {
    running=`ps -ef | grep qemu-system-x86_64 | grep -c raw`
    if [ $running -gt 0 ];then
        return 0
    else
        return 1
    fi
}
run_qemu() {
    if [ "$1" != "" ];then
        topo="$1"
    fi
    cleanup

    echo "QEMU=$QEMU" > $run_opts_file
    echo "KERNEL_PATH=$KERNEL_PATH" >> $run_opts_file
    echo "SHARED_CFG=\"$SHARED_CFG\"" >> $run_opts_file
    echo "net_config=\"$net_config\"" >> $run_opts_file
    echo "topo=\"$topo\"" >> $run_opts_file
    echo "QEMU_IMG=$QEMU_IMG" >> $run_opts_file
    echo "accel_mode=$accel_mode" >> $run_opts_file
    echo "***: Start running Qemu..."

    format=raw
    if [ `echo $QEMU_IMG | grep -c qcow2` -ne 0 ];then
        format="qcow2"
    fi

    if $monitor_wait; then
        wait_flag="wait"
    else
        wait_flag="nowait"
    fi

    if $(qemu_vm_is_running); then
        echo -n "A Qemu VM is running, do you want to poweroff it first (Y/N)?"
        read ans
        if [ "$ans" == "Y" ]; then
            cxl-tool --poweroff
            sleep 2
        else
            exit
        fi
    fi

    echo "${QEMU} -s \
        -kernel ${KERNEL_PATH} \
        -append \"${KERNEL_CMD}\" \
        -smp $num_cpus \
        -accel $accel_mode \
        -serial mon:stdio \
        -nographic \
        ${SHARED_CFG} \
        ${net_config} \
        -drive file=${QEMU_IMG},index=0,media=disk,format=$format \
        -machine q35,cxl=on -m 8G,maxmem=32G,slots=8 \
        -monitor telnet:127.0.0.1:12345,server,$wait_flag \
        $extra_opts \
        -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped \
        -virtfs local,path=/home/`whoami`,mount_tag=homeshare,security_model=mapped \
        $topo" > $cmd_file

    ${QEMU} -s $extra_opts \
        -kernel ${KERNEL_PATH} \
        -append "${KERNEL_CMD}" \
        -smp $num_cpus \
        -accel $accel_mode \
        -serial mon:stdio \
        -nographic \
        ${SHARED_CFG} \
        ${net_config} \
        -monitor telnet:127.0.0.1:12345,server,$wait_flag \
        -drive file=${QEMU_IMG},index=0,media=disk,format=$format \
        -machine q35,cxl=on -m 8G,maxmem=32G,slots=8 \
        -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped \
        -virtfs local,path=/home/`whoami`,mount_tag=homeshare,security_model=mapped \
        $topo 1>&/tmp/qemu.log &

    if [ "$accel_mode" == "kvm" ];then
        sleep 2
    else
        sleep 5
    fi
    if $(qemu_vm_is_running);then
        echo "QEMU:running" > /tmp/qemu-status
        echo "QEMU instance is up, access it: ssh root@localhost -p $ssh_port"
        rs=`same_file  $cxl_test_tool_dir/$default_vars_file /tmp/$default_vars_file`
        if [ "$rs" == "0" ];then
            echo_task "copy default vars file to /tmp/"
            cp $cxl_test_tool_dir/$default_vars_file /tmp/
        fi
        sleep 2
    else
        echo "Qemu: start Fail!"
		echo "Check /tmp/qemu.log for more information"
		exit 1
    fi
}

shutdown_qemu() {
    if [ ! -f /tmp/qemu-status ]  || ! $(qemu_vm_is_running);then
        echo "Warning: qemu is not running, skip shutdown!"
        exit
    fi
    running=`cat /tmp/qemu-status | grep -c "QEMU:running"`
    if [ $running -eq 0 ];then
        echo "Warning: qemu is not running as shown in qemu-status, skip shutdown!"
    else
        raw_sh_on_remote "poweroff"
        sleep 1
        if $(qemu_vm_is_running); then
            echo "execute poweroff on guest failed"
            exit
        fi
        echo "" > /tmp/qemu-status
        echo "Qemu: shutdown"
    fi
}

load_cxl_driver() {
    echo_task "install cxl modules"

    sh_on_remote "modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem"
    sh_on_remote "modprobe -a nd_pmem"
    sh_on_remote "modprobe -a dax device_dax"

    echo
    sh_on_remote "lsmod"
}

unload_cxl_driver() {
    echo_task "uninstall cxl modules"

    sh_on_remote "rmmod -f cxl_pmem cxl_mem cxl_port cxl_pci cxl_acpi cxl_pmu cxl_core"
    sh_on_remote "rmmod -f nd_pmem"
    sh_on_remote "rmmod -f device_dax dax nd_btt libnvdimm"

    echo
    sh_on_remote "lsmod"
}

find_dcd() {
    cmd="cxl list | grep serial -B 1 | grep -m1 memdev | sed 's/,//'"
    rs=`raw_sh_on_remote "$cmd"`
    dev=`echo $rs | awk -F: '{print $2}'`
    dcd_last_used=$dev
    echo $dev
}

find_decoder() {
    dev=`find_dcd`
    if [ -z "$dev" ];then
        echo ""
    else
        cmd="cxl list -E -m $dev"
        raw_sh_on_remote "$cmd" > /tmp/cxl-list
        num=`cat /tmp/cxl-list | grep endpoint | awk -F: '{print $2}'| sed 's/,//' | sed 's/endpoint//'`
        echo $num
    fi
}

create_cxl_dc_region() {
    mod_loaded=`raw_sh_on_remote "lsmod | grep -c cxl_mem"`
    if [ "$mod_loaded" == "0" ];then
        load_cxl_driver
    fi

    num=`find_decoder`
    if [ -z "$num" ];then
        echo "cannot find decoder, exit"
        exit 1
    fi
    echo_task "Create DC region"
    cmd_str="rid=0; \
          region=\$(cat /sys/bus/cxl/devices/decoder0.0/create_dc_region); \
          echo \$region > /sys/bus/cxl/devices/decoder0.0/create_dc_region; \
          echo 256 > /sys/bus/cxl/devices/\$region/interleave_granularity; \
          echo 1 > /sys/bus/cxl/devices/\$region/interleave_ways; \
          echo dc\$rid >/sys/bus/cxl/devices/decoder$num.0/mode; \
          echo 0x40000000 >/sys/bus/cxl/devices/decoder$num.0/dpa_size; \
          echo 0x40000000 > /sys/bus/cxl/devices/\$region/size; \
          echo  decoder$num.0 > /sys/bus/cxl/devices/\$region/target0; \
          echo 1 > /sys/bus/cxl/devices/\$region/commit; \
          echo \$region > /sys/bus/cxl/drivers/cxl_region/bind"
    sh_on_remote "$cmd_str"

    echo_task "Show dc region"
    sh_on_remote "cxl list -iu"
}

issue_qmp_cmd() {
    port=`cat $cmd_file | sed "s/.*qmp/qmp/g" | awk -F'[^0-9]+' '{ print $2 }'`
    if [ "port" == "" ];then
        error "qmp port not found, check whether qemu is launched with qmp support"
        exit 1
    fi
    #echo_task "Install ncat tool on host"
    rs=$(which ncat)
    if [ -z "$rs" ];then
        sudo apt-get install ncat >&/dev/null
    fi

    #echo_task "execute qmp commands"
    cat $qmp_file | ncat localhost $port

    #echo_task "execute qmp command completed"
}

reset_qemu() {
    shutdown_qemu
    sleep 2
    if [ -f $run_opts_file ]; then
        source $run_opts_file
    fi
    run_qemu "$topo"
}

mctp_setup() {
    #install_mctp_pkg
    copy_to_remote $cxl_test_tool_dir/test-workflows/mctp.sh /tmp/
    sh_on_remote "bash /tmp/mctp.sh"
}

help() {
    echo "Usage: $0 [OPTION]..."
    echo -e ' OPTION:
    -C,--cmd  \t\t\t shell command series to execute on the VM
    -T,--topology  \t\t predefined CXL topology to use for qemu emulation:
        sw: \t\t with a switch
        rp1: \t\t with only one root port
        hb2: \t\t with two home bridges
        m2: \t\t with two memdev and 1 HB
        fm: \t\t with fmapi
    --create-topo \t\t flag to generate topology
    -N,--CPUS \t\t\t number of CPUs created for the VM
    -E,--extra-opts \t\t extra options to pass to qemu when launching
    -A,--accel \t\t\t acceleration mode: tcg (default)/kvm/...
    -Q,--qemu-root \t\t Qemu directory
    -K,--kernel \t\t Linux kernel directory
    -BK,--deploy-kernel \t flag to build kernel, install kernel modeles
    -BQ,--build-qemu \t\t flag to build qemu
    --dmesg-cxl \t\t print out the dmesg of the VM for cxl
    --create-image \t\t create qemu image
    --install-ndctl \t\t flag to install ndctl
    --ndctl-url \t\t url to git clone ndctl
    --qemu-url \t\t\t url to git clone ndctl
    --kernel-url \t\t url to git clone ndctl
    --ndctl-branch \t\t ndctl branch
    --qemu-branch \t\t qemu branch
    --load-drv \t\t\t load cxl driver
    --unload-drv \t\t unload cxl driver
    --setup-qemu \t\t git clone, configure, make and install qemu
    --setup-kernel \t\t git clone, configure, make and install kernel
    --setup-mctp \t\t setup mctp service
    --kernel-branch \t\t kernel branch
    -P,--port \t\t\t port to ssh to VM
    -L,--login \t\t\t login the VM
    -R,--run \t\t\t start qemu
    --reset \t\t\t reset the VM instance
    --poweroff \t\t\t shutdown the VM instance
    --shutdown \t\t\t shutdown the VM instance
    --kdb \t\t\t debug kernel with gdb
    --ndb \t\t\t debug ndctl inside VM with gdb, followed with cxl operations
    --qdb \t\t\t debug qemu with gdb, may need to launch gdb with -S option
    --kconfig \t\t\t configure kernel with make menuconfig
    --cxl-mem-setup \t\t set up cxl memory as regular memory and online
    --dcd-test \t\t do dcd test (create region & add/release dc extents) without start/poweroff vm
    --create-dcR \t\t Create DC region before DC extents can be added
    --create-region \t\t Create a regular region for mem0
    --create-ram-region \t Create a regular ram region for volatile memory mem0
    --disable-region \t\t disable a region (region0 by default)
    --destroy-region \t\t destroy a region (region0 by default)
    --convert-dc-extents \t\t convert dc extents to system ram (after add extents)
    --issue-qmp \t\t issue qmp command to VM for poison injection, dc extent add/release 
    --try-mctp \t\t Try to test OOB mailbox with MCTP over I2C setup
    --install-ras \t\t Install rasdaemon tool
    --ps \t\t\t Show process status with ps to see if qemu is running
    -H,--help \t\t\t display help information
    '
}

cleanup() {
    rm -f /tmp/hmem*.raw
    rm -f /tmp/*lsa*.raw
    rm -f /tmp/cxltest*.raw
}

set_default_options(){
    num_cpus=1
    TOPO='rp1'
    build_qemu=false
    deploy_kernel=false
    create_image=false
    setup_qemu=false
    setup_kernel=false
    setup_mctp=false
    run=false
    login=false
    reset=false
    shutdown=false
    install_ndctl=false
    gen_topo=false
    cmd_str=""
    load_drv=false
    unload_drv=false
    create_dc_region=false
    kdb=false
    ndb=false
    qdb=false
    opt_nbd="cxl/cxl"
    kconfig=false
    cxl_mem_setup=false
    region_create=false
    ram_region_create=false
    region_destroy=false
    region_disable=false
    issue_qmp=false
    test_cxl=false
    print_dmesg=false
    monitor_wait=false
    try_mctp_test=false
    rasdaemon_install=false
    aer_inject=false
}

display_options() {
    echo_task Run $0 with options:
    echo "***************************"
    print_key_value "KERNEL_ROOT" "$KERNEL_ROOT"
    print_key_value "QEMU_ROOT" "$QEMU_ROOT"
    print_key_value "QEMU_IMG" "$QEMU_IMG "
    print_key_value
    print_key_value "Other variables: "
    print_key_value " mode\t" "$accel_mode"
    print_key_value " num_cpus" "$num_cpus"
    print_key_value " Topology" "$TOPO if no create-topo"
    print_key_value " build_qemu" "$build_qemu "
    print_key_value " deploy_kernel" "$deploy_kernel"
    print_key_value " create_image" "$create_image "
    print_key_value " run\t" "$run "
    print_key_value " shutdown" "$shutdown "
    print_key_value " reset\t" "$reset "
    print_key_value " install_ndctl" "$install_ndctl "
    print_key_value " create-topo" "$gen_topo "
    print_key_value " monitor_wait" "$monitor_wait "

    echo
    echo "run $0 -H for more options available."
    echo "***************************"
    echo
}

get_cxl_topology() {
    topo=""
    if [ "$1" == "sw" ];then
        topo=$SW
    elif [ "$1" == "rp1" ];then
        topo=$RP1
    elif [ "$1" == "hb2" ];then
        topo=$HB2
    elif [ "$1" == "m2" ];then
        topo=$M2
    elif [ "$1" == "fm" ];then
        topo=$FM
    else
        echo topology \"$1\" not supported, exit;
        exit
    fi
    echo $topo;
}

build_source_code() {
    dir=$1
    cmd=$2

    if [ ! -d $dir ]; then
        echo $dir not found, exit building
        exit
    else
        echo cd $dir
        cd $dir
    fi
    if [ ! -s "$cmd" ];then
        cmd="make -j16"
    fi

    echo $cmd
    $cmd
}

configure_kernel() {
    echo_task "Configure kernel"
    cd $KERNEL_ROOT
    make menuconfig
}

find_vmem() {
    cmd="cxl list -M | grep ram -B 1 | grep memdev | sed 's/,//'"
    dev=`raw_sh_on_remote "$cmd"`
    vmem_last_used=`echo $dev | awk -F: '{print $2}'`
    echo $vmem_last_used
}

find_pmem() {
    cmd="cxl list -M | grep pmem -B 1 | grep memdev | sed 's/,//'"
    dev=`raw_sh_on_remote "$cmd"`
    pmem_last_used=`echo $dev | awk -F: '{print $2}'`
    echo $pmem_last_used
}

find_region() {
    type=$1
    path=/sys/bus/cxl/devices/decoder0.0/$type
    raw_sh_on_remote "cat $path"
}

create_cxl_region() {
    memdev="mem0"
    if [ "$1" == "" ];then
        mode="pmem"
        memdev=$(find_pmem)
    else
        mode=$1
        memdev=$(find_vmem)
    fi
    load_cxl_driver

    sh_on_remote "cxl list -iu"
    sh_on_remote "cxl create-region -m -d decoder0.0 -w 1 mem0 -s 512M -t $mode"
    sh_on_remote "cxl list -iu"
    if [ "$mode" == "ram" ];then
        sh_on_remote "lsmem"
    fi
}

destroy_cxl_region() {
    region="region0"
    if [ "$1" != "" ];then
        region=$1
    fi
    sh_on_remote "cxl destroy-region $region -f"
    sh_on_remote "cxl list -iu"
}

disable_cxl_region() {
    region="region0"
    if [ "$1" != "" ];then
        region=$1
    fi
    sh_on_remote "cxl disable-region $region -f"
    sh_on_remote "cxl list -iu"
}

setup_cxl_memory() {
    load_cxl_driver

    memdev="mem0"
    if [ "$1" != "" ];then
        memdev=$1
    else
        memdev=`find_pmem`
    fi

    sh_on_remote "cxl list -iu"
    region=$(find_region "create_pmem_region")

    dax=`echo $region | sed 's/region/dax/'`
    sh_on_remote "cxl create-region -m -d decoder0.0 -w 1 $memdev -s 512M"
    sh_on_remote "ndctl create-namespace -m dax -r $region"
    sh_on_remote "daxctl reconfigure-device --mode=system-ram --no-online $dax.0"
    sh_on_remote "daxctl online-memory $dax.0"
    sh_on_remote "lsmem"
}

convert_dcd_to_system_ram() {
    region=$1
    if [ -z "$region" ];then
        echo "No region of dcd for converting, exit"
        exit
    fi

    dax=`raw_sh_on_remote "daxctl create-device $region" | grep "chardev"`
    if [ -z "$dax" ];then
        echo "Create dax device failed, exit"
        exit
    fi

    dax=`echo $dax | awk -F: '{print $2}'|sed 's/,//'`
    sh_on_remote "daxctl reconfigure-device --mode=system-ram --no-online $dax"
    sh_on_remote "daxctl online-memory $dax"
    sh_on_remote "lsmem"
}

kernel_deploy() {
    echo_task "build kernel and install modules"
    build_source_code $KERNEL_ROOT
    sudo make modules_install
    echo_task "build kernel and install modules--done"
}

display_dmesg() {
    sh_on_remote "dmesg | grep cxl | grep -v Doorbell | grep -v 0x4102"
}

create_qemu_image() {
    echo -e 'network:
    version: 2
    renderer: networkd
    ethernets:
        enp0s2:
            dhcp4: true
    ' > /tmp/netplan-config.yaml
    chmod 600  /tmp/netplan-config.yaml

    echo_task "Create qemu image: $image_name"
    IMG=$image_name
    DIR=/tmp/img_dir
	qemu_img=$QEMU_ROOT/build/qemu-img
    if [ ! -f $qemu_img ];then
        echo "Qemu tool: qemu-img not found"
        exit 1
    fi

	if [ ! -d `dirname $IMG` ];then
		mkdir -p `dirname $IMG`
		if [ "$?" != "0" ];then
			echo "Create image directory failed, exit..."
			exit 1
		fi
	fi
	$qemu_img create $IMG 16g
    sudo mkfs.ext4 $IMG
    mkdir $DIR
    echo_task "mount -o loop $IMG $DIR"
    sudo mount -o loop $IMG $DIR
    if [ $? -ne 0 ];then
        echo "mount $IMG to $DIR failed"
        exit 1
    fi

    echo_task "debootstrap --arch amd64 stable $DIR"
    sudo debootstrap --arch amd64 stable $DIR
    if [ $? -ne 0 ];then
        echo_task "debootstrap failed"
        exit 1
    fi

    echo_task "Copy ssh key to guest"
    sudo mkdir $DIR/root/.ssh
    cat ~/.ssh/*.pub > /tmp/authorized_keys
    sudo cp /tmp/authorized_keys $DIR/root/.ssh/
    echo nameserver 8.8.8.8  | sudo tee -a $DIR/etc/resolv.conf

    echo_task "cp /tmp/netplan-config.yaml $DIR/etc/netplan"
    sudo mkdir -p $DIR/etc/netplan/
    sudo cp /tmp/netplan-config.yaml $DIR/etc/netplan/config.yaml
    openvswitch-switch

    echo "#! /bin/bash
stty rows 80 cols 132
mount -t 9p -o trans=virtio homeshare /home/fan
mount -t 9p -o trans=virtio modshare /lib/modules
" > /tmp/rc.local
    chmod a+x /tmp/rc.local
    sudo cp /tmp/rc.local $DIR/etc/
    sudo mkdir -p $DIR/home/fan
    sudo mkdir -p $DIR/lib/modules/

    sudo chroot $DIR passwd -d root
    sudo chroot $DIR apt-get update
    sudo chroot $DIR apt-get install -y ssh netplan.io openvswitch-switch
    sudo umount $DIR

    echo_task "Convert raw image to qcow2"
    qemu-img convert -O qcow2 $IMG /tmp/qemu-image.qcow2
    rmdir $DIR

    ssh-keygen -f "~/.ssh/known_hosts" -R "[localhost]:2024"
    echo_task "qemu image: $IMG created!"
    exit
}

qemu_setup() {
    url=$qemu_url
    if [ "$url" == "" ]; then
        echo "Error: missing url for qemu git clone"
        exit
    fi

    if [ ! -d "$QEMU_ROOT" ]; then
        mkdir -p $QEMU_ROOT
    fi

    sudo apt install libglib2.0-dev libgcrypt20-dev zlib1g-dev \
        autoconf automake libtool bison flex libpixman-1-dev bc qemu-kvm \
        make ninja-build libncurses-dev libelf-dev libssl-dev debootstrap \
        libcap-ng-dev libattr1-dev libslirp-dev libslirp0 python3-venv
    echo
    echo git clone -b $qemu_branch --single-branch $url $QEMU_ROOT
    git clone -b $qemu_branch --single-branch $url $QEMU_ROOT
    echo
	cur_dir=`pwd`
    cd $QEMU_ROOT
    echo ./configure --target-list=x86_64-softmmu --enable-debug
    ./configure --target-list=x86_64-softmmu --enable-debug
    echo
    echo "make -j8"
    make -j8
	cd $cur_dir
}

kernel_setup() {
    echo_task "setup kernel: git clone, compile and install modules -- started"

    cur_dir=`pwd`

    url=$kernel_url
    if [ "$url" == "" ]; then
        echo "Error: missing url for kernel tree git clone"
        exit
    fi

    if [ ! -d "$KERNEL_ROOT" ]; then
        echo_task "Create the kernel root if not exist already..."
        mkdir -p $KERNEL_ROOT

        cd $KERNEL_ROOT
        echo_task "git clone -b $kernel_branch --single-branch $url $KERNEL_ROOT"
        git clone -b $kernel_branch --single-branch $url $KERNEL_ROOT
    else
        echo_task "$KERNEL_ROOT exists, try checking out branch ($kernel_branch)"
        cd $KERNEL_ROOT
        git checkout $kernel_branch
        if [ "$?" != "0" ]; then
            echo_task "git checkout $kernel_branch failed!"

            echo "Do you want to DELETE $KERNEL_ROOT and git clone the kernel here?"
            echo -n "input \"clone\" to continue, or else exit: "
            read choice
            if [ "$choice" == "clone" ]; then
                mkdir /tmp/old-kernel-dir/
                mv * /tmp/old-kernel-dir/
                echo_task "git clone -b $kernel_branch --single-branch $url $KERNEL_ROOT"
                git clone -b $kernel_branch --single-branch $url $KERNEL_ROOT
            else
                exit 1
            fi
        else
            echo_task "Pull update for branch $kernel_branch"
            git pull
            if [ "$?" != "0" ]; then
                echo "Pull update for branch $kernel_branch failed"
                exit 1
            fi
        fi
    fi

	if [ -f ".config" ];then
		echo -n "Found .config under $KERNEL_ROOT, use it for kernel configuration (Y/N): "
		read choice
		if [ "$choice" == "Y" ]; then
			echo_task "Configure kernel with existing config file"
		elif [ "$choice" == "N" ]; then
			echo_task "Configure the kernel..."
			echo -n "Configure mannually (1) or copy the example config (2): "
			read choice

			if [ "$choice" == "1" ]; then
				make menuconfig
			else
				echo "Copy the example config as .config"
				cp $cur_dir/kconfig.example $KERNEL_ROOT/.config
			fi
		else
			echo "Unknown choice"
			exit 1
		fi
	else
		echo_task "Configure the kernel..."
		echo -n "Configure mannually (1) or copy the example config (2): "
		read choice

		if [ "$choice" == "1" ]; then
			make menuconfig
		else
			echo "Copy the example config as .config"
			cp $cur_dir/kconfig.example $KERNEL_ROOT/.config
		fi
	fi

	echo_task "Compile the kernel in $KERNEL_ROOT"
    cd $KERNEL_ROOT
    make -j 16

    echo_task "Install kernel modules"
    sudo make modules_install

	cd $cur_dir
    
    echo_task "$0 completed."
}

gdb_kernel() {
    cd $KERNEL_ROOT
    gdb -tui ./vmlinux
}

gdb_qemu() {
    pid=`ps -ef | grep qemu-system | awk '{print $2}'`
    echo pid: $pid
    gdb -tui -p $pid
}

gdb_ndctl() {
    opt=$1
    sh_on_remote "cd ndctl; gdb --args build/$opt"
}

ndctl_installed() {
    cmds='ndctl daxctl cxl'
    for cmd in $cmds; do
        rs=`sh_on_remote "which $cmd | grep -c $cmd" 1>/dev/null`
        if [ "$rs" == "0" ];then
            echo "0"
        fi
    done
    echo "1"
}
setup_ndctl() {
    echo_task "setup ndctl to install cxl tools"
    url=$1
    dir=/tmp/ndctl
    rs=`ndctl_installed`
    if [ $rs == "1" ];then
        echo "ndctl tools ready installed, skip installing"
        return
    fi

    if [ "$url" == "" -o `echo $url | grep -c "github"` -eq 0 ]; then
        url=https://github.com/pmem/ndctl.git
    fi

    sh_on_remote "apt-get install -y git meson bison pkg-config cmake libkmod-dev libudev-dev uuid-dev libjson-c-dev libtraceevent-dev libtracefs-dev asciidoctor keyutils libudev-dev libkeyutils-dev libiniparser-dev"
    sh_on_remote "git clone $url $dir"
    sh_on_remote "\
        cd $dir;\
        meson setup build;\
        meson compile -C build;\
        meson install -C build
    "
    echo "**********************"
    echo "cxl list:"
    sh_on_remote "cxl list"
    echo "**********************"
    if [ "$?" != "0" ];then
        echo_task "Install ndctl failed!"
    else
        echo_task "Install ndctl completed!"
    fi
}

install_mctp_pkg(){
    echo_task "install mctp program"
    url="https://github.com/CodeConstruct/mctp.git"
    mctp_dir="/tmp/mctp"

    sh_on_remote "apt-get install -y libsystemd-dev python3-pytest"
    sh_on_remote "git clone $url $mctp_dir"
    sh_on_remote "cd $mctp_dir; git reset --hard 69ed224ff9b5206ca7f3a5e047a9da61377d2ca7"

    sh_on_remote "cd $mctp_dir; meson setup obj; ninja -C obj; meson install -C obj"
    sh_on_remote "cd $mctp_dir; cp conf/mctpd-dbus.conf /etc/dbus-1/system.d/"
    sh_on_remote "cd $mctp_dir; cat conf/mctpd.service | sed 's/sbin/local\/sbin/' > /etc/systemd/system/mctpd.service"
}

try_fmapi_test() {
    url="https://github.com/moking/cxl-fmapi-tests-clone.git"
    test_dir="/tmp/fmapi-test"
    if [ ! -d $test_dir ];then
        sh_on_remote "git clone $url $test_dir"
    fi
    sh_on_remote "cd $test_dir; gcc cxl-mctp-test.c -o cxl-mctp-test"
    sh_on_remote "cd $test_dir; ./cxl-mctp-test 8; ./cxl-mctp-test 9; ./cxl-mctp-test 10"
}


remote_file_exists() {
    file=$1
    cmd="\
    if [ -e $file ];then
        echo 1
    else
        echo 0
    fi"

    sh_on_remote "$cmd"
}

# start: below are rasdaemon related
install_rasdaemon() {
    echo_task "install rasdaemon"
    dir="~/rasdaemon"
    branch="scrub_control"
    url="https://github.com/moking/rasdaemon-clone"

    rt=`remote_file_exists $dir`
    if [ "$rt" == "1" ];then
        echo -n "$dir exists, delete it before git clone (Y/N): "
        read ans
        if [ "$ans" == "Y" ];then
            sh_on_remote "rm -rf $dir"
            sh_on_remote "git clone -b $branch --single-branch $url $dir"
            sh_on_remote "cd $dir; bash ./run-me.sh ; ls rasdaemon -lh"
        fi
    else
        sh_on_remote "git clone -b $branch --single-branch $url $dir"
        sh_on_remote "cd $dir; bash ./run-me.sh ; ls rasdaemon -lh"
    fi

    sh_on_remote "rasdaemon"
}

install_mce_inject() {
    dir="~/mce-inject"
    branch="master"
    url="https://git.kernel.org/pub/scm/utils/cpu/mce/mce-inject.git"

    echo_task "install mce inject"

    rt=`remote_file_exists $dir`
    if [ "$rt" == "1" ];then
        echo -n "$dir exists, delete it before git clone (Y/N): "
        read ans
        if [ "$ans" == "Y" ];then
            sh_on_remote "rm -rf $dir"
            sh_on_remote "git clone -b $branch --single-branch $url $dir"
        fi
    else
        sh_on_remote "git clone -b $branch --single-branch $url $dir"
    fi
    sh_on_remote "apt-get install flex"
    sh_on_remote "cd $dir; make"
}

install_mce_test() {
    dir="~/mce-test"
    branch="master"
    url="https://git.kernel.org/pub/scm/linux/kernel/git/gong.chen/mce-test.git"

    echo_task "install mce test"

    rt=`remote_file_exists $dir`
    if [ "$rt" == "1" ];then
        echo -n "$dir exists, delete it before git clone (Y/N): "
        read ans
        if [ "$ans" == "Y" ];then
            sh_on_remote "rm -rf $dir"
            sh_on_remote "git clone -b $branch --single-branch $url $dir"
        fi
    else
        sh_on_remote "git clone -b $branch --single-branch $url $dir"
    fi
    sh_on_remote "cd $dir; make"
}

install_aer_inject() {
    dir="~/aer-inject"
    branch="master"
    url="https://git.kernel.org/pub/scm/linux/kernel/git/gong.chen/aer-inject.git"

    echo_task "install aer inject"

    rt=`remote_file_exists $dir`
    if [ "$rt" == "1" ];then
        echo -n "$dir exists, delete it before git clone (Y/N): "
        read ans
        if [ "$ans" == "Y" ];then
            sh_on_remote "rm -rf $dir"
            sh_on_remote "git clone -b $branch --single-branch $url $dir"
        fi
    else
        sh_on_remote "git clone -b $branch --single-branch $url $dir"
    fi
    sh_on_remote "cd $dir; make"
}

inject_aer() {
    echo_task "inject aer"
    file=$1
    if [ -z "$file" -o ! -f $file ];then
        echo "EINJ config file missing!"
        echo "=> Example files can be found in $cxl_test_tool_dir/einj-examples"
        exit
    fi

    dir="~/aer-inject"
    copy_to_remote $file /tmp/aer.input
    str="cd $dir; ./aer-inject /tmp/aer.input"
    sh_on_remote "dmesg -C"
    sh_on_remote "$str"
    sh_on_remote "dmesg"
}

# end: below are rasdaemon related

cxl_test() {
    setup_ndctl $ndctl_url
    setup_cxl_memory
}

dcd_test() {
    create_cxl_dc_region
    if [ "$?" != "0" ];then
        exit 1
    fi
    export `cat /tmp/.vars.config | grep "cxl_test_tool_dir"`
    bash $cxl_test_tool_dir/test-workflows/process-qmp-op.sh "$1"
}

exec_cmd() {
    if [ ! -f /tmp/qemu-status ];then
        echo "Warning: qemu is not running, skip executing command!"
    fi
    cmd_str="$1"

    running=`cat /tmp/qemu-status | grep -c "QEMU:running"`
    if [ $running -eq 0 ];then
        echo "Warning: qemu is not running, skip executing command!"
    else
        if [ -n "$cmd_str" ]; then
            sh_on_remote "$cmd_str"
        fi
    fi
    exit
}

set_default_options

# processing arguments
parse_args() {
    if [[ "$#" -eq "0" ]]; then
       echo "run with -H for help"
       exit 0
    fi
    while [[ "$#" -ne "0" ]]; do
        #echo "processing: $1"
        case "$1" in
            -C|--cmd) exec_cmd "$2"; shift ;;
            -T|--topology) TOPO="$2"; shift ;;
            -N|--CPUS) num_cpus="$2"; shift ;;
            -E|--extra-opts) extra_opts="$2"; shift ;;
            -A|--accel) accel_mode="$2"; shift ;;
            -Q|--qemu_root) QEMU_ROOT="$2"; shift ;;
            -K|--kernel_root) KERNEL_ROOT="$2"; shift ;;
            -BK|--deploy-kernel) deploy_kernel=true ;;
            -BQ|--build-qemu) build_qemu=true ;;
            -MW|--monitor-wait) monitor_wait=true;;
            --create-image) create_image=true ;;
            --cxl) test_cxl=true ;;
            --dcd-test) dcd_test "$2"; shift;;
            --convert-dc-extents) convert_dcd_to_system_ram $2;;
            --image) image_name="$2"; shift ;;
            --install-ndctl) install_ndctl=true ;;
            --create-topo) gen_topo=true ;;
            --ndctl-url) ndctl_url=$2; shift ;;
            --qemu-url) qemu_url=$2; shift ;;
            --kernel-url) kernel_url=$2; shift ;;
            --ndctl-branch) ndctl_branch=$2; shift ;;
            --qemu-branch) qemu_branch=$2; shift ;;
            --dmesg-cxl) print_dmesg=true ;;
            --kernel-branch) kernel_branch=$2; shift ;;
            -P|--port) ssh_port="$2"; shift ;;
            -L|--login) login=true ;;
            -R|--run) run=true ;;
            --reset) reset=true ;;
            --setup-qemu) setup_qemu=true ;;
            --setup-kernel) setup_kernel=true ;;
            --setup-mctp) setup_mctp=true ;;
            --poweroff|--shutdown) shutdown=true ;;
            --load-drv) load_drv=true ;;
            --unload-drv) unload_drv=true ;;
            --create-dcR) create_dc_region=true;;
            --kdb) kdb=true ;;
            --qdb) qdb=true ;;
            --ndb) ndb=true ; opt_nbd="$2"; shift;;
            --ps) ps_qemu_status;;
            -F|--vars-file) opt_vars_file="$2"; shift;;
            --kconfig) kconfig=true;;
            --cxl-mem-setup) cxl_mem_setup=true;;
            --create-region) region_create=true;;
            --create-ram-region) ram_region_create=true;;
            --destroy-region) region_destroy=true;;
            --disable-region) region_disable=true;;
            --issue-qmp) issue_qmp=true; qmp_file="$2"; shift;;
            --try-mctp) try_mctp_test=true;;
            --install-ras) rasdaemon_install=true;;
            -EINJ|--aer-inject) aer_inject=true; einj_file=$2;shift;;
            -H|--help) help; exit;;
            *) echo "Unknown parameter passed: $1"; exit 1 ;;
        esac
        shift
    done
}

parse_args "$@"

if [ ! -f $default_vars_file ];then
    warning "default $default_vars_file under `pwd` not found!"
    if [ "$opt_vars_file" == "" -a -f "/tmp/.vars.config" ];then
        opt_vars_file="/tmp/$default_vars_file"
    else
        error "both default and optional vars file not found, try
        1) create $default_vars_file from run_vars.example, or
        2) pass optional vars file with -F/vars-file option"
        exit 1
    fi
    source $opt_vars_file
    rs=`same_file  $cxl_test_tool_dir/$default_vars_file /tmp/$default_vars_file`
    if [ "$rs" == "0" ];then
        echo "NOTE: config change should always on the $cxl_test_tool_dir config file"
        cp $cxl_test_tool_dir/$default_vars_file /tmp/
    fi
    source $opt_vars_file
else
    source "$default_vars_file"
    rs=`same_file  $default_vars_file /tmp/$default_vars_file`
    if [ "$rs" == "0" ];then
        cp $default_vars_file /tmp/
    fi
fi

if [ ! -n "$image_name" ];then
    if $run; then
        echo "warning: image_name is not given with --image option, use QEMU_IMG ($QEMU_IMG)"
    fi
	image_name=$QEMU_IMG
fi

if [ ! -s "$ssh_port" ];then
    ssh_port="2024"
fi
net_config="-netdev user,id=network0,hostfwd=tcp::$ssh_port-:22 -device e1000,netdev=network0" 

#display_options

if $build_qemu; then
    echo "Build the qemu"
    build_source_code $QEMU_ROOT
fi

if $deploy_kernel ; then
    kernel_deploy
fi

if $setup_qemu; then
    qemu_setup
fi

if $setup_kernel; then
    kernel_setup
fi

if $create_image; then
	if [ -n "$image_name" ];then
		create_qemu_image
	fi
fi

if $issue_qmp; then
    if [ "$qmp_file" == "" -o ! -f "$qmp_file" ];then
        error "no qmp input file found, try to create one like qmp-command.example"
        exit
    fi
   issue_qmp_cmd
fi

if $print_dmesg; then 
    display_dmesg
fi

QEMU=$QEMU_ROOT/build/qemu-system-x86_64
KERNEL_PATH=$KERNEL_ROOT/arch/x86/boot/bzImage


if $run; then
    if $gen_topo; then
        echo "Using cxl topology created from xml ..."
        topo=`create_topology`
    else
        echo "Using predefined cxl topology: $TOPO ..."
        topo=$(get_cxl_topology $TOPO)
    fi

    if  [ ! -f "$QEMU" ];then
        error "Qemu binary not found!"
        exit 1
    fi

    if  [ ! -f "$KERNEL_PATH" ];then
        error "kernel image not found!"
        exit 1
    fi

    if  [ ! -f "$QEMU_IMG" ];then
        error "qemu image not found!"
        exit 1
    fi

    echo "***" >> $top_file
    echo $topo | sed "s/ /\n/g" >> $top_file
    echo "***" >> $top_file

    run_qemu "$topo"
fi
if $login; then
    sh_on_remote
fi

if $shutdown; then
    shutdown_qemu
    cleanup
fi

if $reset; then
    reset_qemu
fi

if $test_cxl; then
    cxl_test
fi

if $install_ndctl; then
    setup_ndctl $ndctl_url
fi

if $kdb; then
    gdb_kernel
fi

if $ndb; then
    gdb_ndctl "$opt_nbd"
fi

if $qdb; then
    gdb_qemu
fi

if $load_drv; then
    load_cxl_driver
fi

if $unload_drv; then
    unload_cxl_driver
fi

if $create_dc_region; then
    create_cxl_dc_region
fi

if $kconfig; then
    configure_kernel
fi

if $cxl_mem_setup; then
    setup_cxl_memory
fi

if $region_create; then
    create_cxl_region;
fi

if $ram_region_create; then
    create_cxl_region "ram"
fi

if $region_disable; then
    disable_cxl_region
fi

if $region_destroy; then
    destroy_cxl_region
fi

if $setup_mctp; then
    mctp_setup
fi

if $try_mctp_test; then
    try_fmapi_test
fi

if $rasdaemon_install; then
    install_rasdaemon
    install_mce_inject
    install_mce_test
    install_aer_inject
fi

if $aer_inject; then
    inject_aer $einj_file
fi
