#! /bin/bash
extra_opts=""

default_vars_file=./.vars.config
opt_vars_file=""
image_name=""
qmp_file=""

top_file=/tmp/topo.txt
cmd_file=/tmp/cmd

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

print_key_value() {
    key=$1
    value=$2
    echo -e "$key \t\t\t $value"
}

create_topology() {
    s=`python cxl-topology-xml-parser.py`
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
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,nonvolatile-dc-memdev=cxl-dcd0,volatile-memdev=cxl-mem2,id=cxl-dcd0,num-dc-regions=2\
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

    echo "${QEMU} -s $extra_opts \
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
        -monitor telnet:127.0.0.1:12345,server,nowait \
        -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped \
        -virtfs local,path=/home/fan,mount_tag=homeshare,security_model=mapped \
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
        -monitor telnet:127.0.0.1:12345,server,nowait \
        -drive file=${QEMU_IMG},index=0,media=disk,format=$format \
        -machine q35,cxl=on -m 8G,maxmem=32G,slots=8 \
        -virtfs local,path=/lib/modules,mount_tag=modshare,security_model=mapped \
        -virtfs local,path=/home/fan,mount_tag=homeshare,security_model=mapped \
        $topo 1>&/tmp/qemu.log &

    if [ "$accel_mode" == "kvm" ];then
        sleep 2
    else
        sleep 5
    fi
    running=`ps -ef | grep qemu-system-x86_64 | grep -c raw`
    if [ $running -gt 0 ];then
        echo "QEMU:running" > /tmp/qemu-status
        echo "QEMU instance is up, access it: ssh root@localhost -p $ssh_port"
        sleep 2
    else
        echo "Qemu: start Fail!"
		echo "Check /tmp/qemu.log for more information"
		exit 1
    fi
}

shutdown_qemu() {
    if [ ! -f /tmp/qemu-status ];then
        echo "Warning: qemu is not running, skip shutdown!"
    fi
    running=`cat /tmp/qemu-status | grep -c "QEMU:running"`
    if [ $running -eq 0 ];then
        echo "Warning: qemu is not running, skip shutdown!"
    else
        ssh root@localhost -p $ssh_port "poweroff"
        echo "" > /tmp/qemu-status
        echo "Qemu: shutdown"
    fi
}

load_cxl_driver() {
    echo_task "install cxl modules"

    echo "Loading cxl drivers: modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem cxl_pmem"
    ssh root@localhost -p $ssh_port "modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem"
    echo "Loading nd_pmem for creating region for cxl pmem"
    ssh root@localhost -p $ssh_port "modprobe -a nd_pmem"
    echo "Loading dax related drivers"
    ssh root@localhost -p $ssh_port "modprobe -a dax device_dax"

    echo
    ssh root@localhost -p $ssh_port "lsmod"
}

unload_cxl_driver() {
    echo_task "uninstall cxl modules"

    echo "remove cxl drivers" 
    ssh root@localhost -p $ssh_port "rmmod -f cxl_pmem cxl_mem cxl_port cxl_pci cxl_acpi cxl_pmu cxl_core"
    echo "remove nd_pmem" 
    ssh root@localhost -p $ssh_port "rmmod -f nd_pmem"
    echo "remove dax related drivers"
    ssh root@localhost -p $ssh_port "rmmod -f device_dax dax nd_btt libnvdimm"

    echo
    ssh root@localhost -p $ssh_port "lsmod"
}


create_cxl_dc_region() {
    echo_task "Create DC region"
    cmd_str="rid=0; \
          region=\$(cat /sys/bus/cxl/devices/decoder0.0/create_dc_region); \
          echo \$region > /sys/bus/cxl/devices/decoder0.0/create_dc_region; \
          echo 256 > /sys/bus/cxl/devices/\$region/interleave_granularity; \
          echo 1 > /sys/bus/cxl/devices/\$region/interleave_ways; \
          echo dc\$rid >/sys/bus/cxl/devices/decoder2.0/mode; \
          echo 0x40000000 >/sys/bus/cxl/devices/decoder2.0/dpa_size; \
          echo 0x40000000 > /sys/bus/cxl/devices/\$region/size; \
          echo  decoder2.0 > /sys/bus/cxl/devices/\$region/target0; \
          echo 1 > /sys/bus/cxl/devices/\$region/commit; \
          echo \$region > /sys/bus/cxl/drivers/cxl_region/bind"
    ssh root@localhost -p $ssh_port "$cmd_str"

    echo_task "Show dc region"
    ssh root@localhost -p $ssh_port "cxl list -i"
}

issue_qmp_cmd() {
    port=`cat $cmd_file | sed "s/.*qmp/qmp/g" | awk -F'[^0-9]+' '{ print $2 }'`
    if [ "port" == "" ];then
        error "qmp port not found, check whether qemu is launched with qmp support"
        exit 1
    else
        echo "qmp port: $port"
    fi
    echo_task "Install ncat tool on host"
    sudo apt-get install ncat

    echo_task "execute qmp commands"
    cat $qmp_file | ncat localhost $port

    echo_task "execute qmp command completed"
}

reset_qemu() {
    shutdown_qemu
    sleep 2
    if [ -f $run_opts_file ]; then
        source $run_opts_file
    fi
    run_qemu "$topo"
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
    --create-topo \t\t flag to generate topology
    -N,--CPUS \t\t\t number of CPUs created for the VM
    -E,--extra-opts \t\t extra options to pass to qemu when launching
    -A,--accel \t\t\t acceleration mode: tcg (default)/kvm/...
    -Q,--qemu-root \t\t Qemu directory
    -K,--kernel \t\t Linux kernel directory
    -BK,--deploy-kernel \t\t flag to build kernel, install kernel modeles
    -BQ,--build-qemu \t\t flag to build qemu
    -I,--create \t\t create qemu image
    --install-ndctl \t\t flag to install ndctl
    --ndctl-url \t\t url to git clone ndctl
    --qemu-url \t\t\t url to git clone ndctl
    --kernel-url \t\t url to git clone ndctl
    --ndctl-branch \t\t ndctl branch
    --qemu-branch \t\t qemu branch
    --load-drv \t\t\t load cxl driver
    --unload-drv \t\t\t unload cxl driver
    --setup-qemu \t\t git clone, configure, make and install qemu
    --setup-kernel \t\t git clone, configure, make and install kernel
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
    --create-dcR \t\t Create DC region before DC extents can be added
    --create-region \t\t Create a regular region for mem0
    --create-ram-region \t Create a regular ram region for volatile memory mem0
    --disable-region \t\t disable a region (region0 by default)
    --destroy-region \t\t destroy a region (region0 by default)
    --issue-qmp \t\t issue qmp command to VM for poison injection, dc extent add/release 
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

create_cxl_region() {
    if [ "$1" == "" ];then
        mode="pmem"
    else
        mode=$1
    fi
    load_cxl_driver

    echo_task "Show cxl device: cxl list -iu"
    ssh root@localhost -p $ssh_port "cxl list -iu"

    echo 
    echo "create region"
    ssh root@localhost -p $ssh_port "cxl create-region -m -d decoder0.0 -w 1 mem0 -s 512M -t $mode"

    echo_task "Show cxl device: cxl list -iu"
    ssh root@localhost -p $ssh_port "cxl list -iu"
    if [ "$mode" == "ram" ];then
        ssh root@localhost -p $ssh_port "lsmem"
    fi
}

destroy_cxl_region() {
    region="region0"
    if [ "$1" != "" ];then
        region=$1
    fi
    ssh root@localhost -p $ssh_port "cxl destroy-region $region -f"
    echo_task "Show cxl device: cxl list -iu"
    ssh root@localhost -p $ssh_port "cxl list -iu"
}

disable_cxl_region() {
    region="region0"
    if [ "$1" != "" ];then
        region=$1
    fi
    ssh root@localhost -p $ssh_port "cxl disable-region $region -f"
    echo_task "Show cxl device: cxl list -iu"
    ssh root@localhost -p $ssh_port "cxl list -iu"
}

setup_cxl_memory() {
    load_cxl_driver

    echo "Show cxl device: cxl list -iu"
    ssh root@localhost -p $ssh_port "cxl list -iu"

    echo 
    echo "create region"
    ssh root@localhost -p $ssh_port "cxl create-region -m -d decoder0.0 -w 1 mem0 -s 512M --debug"

    echo 
    echo "create namespace"
    ssh root@localhost -p $ssh_port "ndctl create-namespace -m dax -r region0"

    echo 
    echo "daxctl reconfigure-device --mode=system-ram --no-online dax0.0"
    ssh root@localhost -p $ssh_port "daxctl reconfigure-device --mode=system-ram --no-online dax0.0"

    echo 
    echo "online memory"
    ssh root@localhost -p $ssh_port "daxctl online-memory dax0.0"

    echo 
    echo "show memory"
    ssh root@localhost -p $ssh_port "lsmem"
}

kernel_deploy() {
    echo_task "build kernel and install modules"
    build_source_code $KERNEL_ROOT
    sudo make modules_install
    echo_task "build kernel and install modules--done"
}

display_dmesg() {
    ssh root@localhost -p $ssh_port "dmesg | grep cxl | grep -v Doorbell | grep -v 0x4102"
}

create_qemu_image() {
    echo -e 'network:
    version: 2
    renderer: networkd
    ethernets:
        enp0s2:
            dhcp4: true
    ' > /tmp/netplan-config.yaml

    echo_task "Create qemu image: $image_name"
    IMG=$image_name
    DIR=/tmp/img_dir

	if [ ! -d `dirname $IMG` ];then
		mkdir -p `dirname $IMG`
		if [ "$?" != "0" ];then
			echo "Create image directory failed, exit..."
			exit 1
		fi
	fi
	qemu-img create $IMG 16g
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

    echo_task "cp $/tmp/netplan-config.yaml $DIR/etc/netplan"
    sudo mkdir -p $DIR/etc/netplan/
    sudo cp /tmp/netplan-config.yaml $DIR/etc/netplan/config.yaml

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
    sudo chroot $DIR apt-get install -y ssh netplan.io
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
        libcap-ng-dev libattr1-dev libslirp-dev libslirp0
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
    gdb ./vmlinux
}

gdb_qemu() {
    pid=`ps -ef | grep qemu-system | awk '{print $2}'`
    echo pid: $pid
    gdb -p $pid
}

gdb_ndctl() {
    opt=$1
    echo ssh root@localhost -p $ssh_port "cd ndctl; gdb --args build/$opt"
    ssh root@localhost -p $ssh_port "cd ndctl; gdb --args build/$opt"
}

setup_ndctl() {
    echo_task "setup ndctl to install cxl tools"
    url=$1

    if [ "$url" == "" -o `echo $url | grep -c "github"` -eq 0 ]; then
        url=https://github.com/pmem/ndctl.git
    fi

    ssh root@localhost -p $ssh_port "apt-get install -y git meson bison pkg-config cmake libkmod-dev libudev-dev uuid-dev libjson-c-dev libtraceevent-dev libtracefs-dev asciidoctor keyutils libudev-dev libkeyutils-dev libiniparser-dev"
    ssh root@localhost -p $ssh_port "git clone $url "
    ssh root@localhost -p $ssh_port "\
        cd ndctl;\
        meson setup build;\
        meson compile -C build;\
        meson install -C build
    "
    echo "**********************"
    echo "cxl list:"
    ssh root@localhost -p $ssh_port "cxl list"
    echo "**********************"
    if [ "$?" != "0" ];then
        echo_task "Install ndctl failed!"
    else
        echo_task "Install ndctl completed!"
    fi
}

cxl_test() {
    setup_ndctl $ndctl_url
    setup_cxl_memory
}

exec_cmd() {
    if [ ! -f /tmp/qemu-status ];then
        echo "Warning: qemu is not running, skip executing command!"
    fi

    running=`cat /tmp/qemu-status | grep -c "QEMU:running"`
    if [ $running -eq 0 ];then
        echo "Warning: qemu is not running, skip executing command!"
    else
        if [ -n "$cmd_str" ]; then
            echo "Qemu: execute \"$cmd_str\" on VM"
            ssh root@localhost -p $ssh_port "$cmd_str"
        fi
    fi
}

set_default_options
# processing arguments

parse_args() {
    while [[ "$#" -gt 0 ]]; do
        case "$1" in
            -C|--cmd) cmd_str="$2"; shift ;;
            -T|--topology) TOPO="$2"; shift ;;
            -N|--CPUS) num_cpus="$2"; shift ;;
            -E|--extra-opts) extra_opts="$2"; shift ;;
            -A|--accel) accel_mode="$2"; shift ;;
            -Q|--qemu_root) QEMU_ROOT="$2"; shift ;;
            -K|--kernel_root) KERNEL_ROOT="$2"; shift ;;
            -BK|--deploy-kernel) deploy_kernel=true ;;
            -BQ|--build-qemu) build_qemu=true ;;
            --create-image) create_image=true ;;
            --cxl) test_cxl=true ;;
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
            --poweroff|--shutdown) shutdown=true ;;
            --load-drv) load_drv=true ;;
            --unload-drv) unload_drv=true ;;
            --create-dcR) create_dc_region=true;;
            --kdb) kdb=true ;;
            --qdb) qdb=true ;;
            --ndb) ndb=true ; opt_nbd="$2"; shift;;
            -F/--vars-file) opt_vars_file="$2"; shift;;
            --kconfig) kconfig=true;;
            --cxl-mem-setup) cxl_mem_setup=true;;
            --create-region) region_create=true;;
            --create-ram-region) ram_region_create=true;;
            --destroy-region) region_destroy=true;;
            --disable-region) region_disable=true;;
            --issue-qmp) issue_qmp=true; qmp_file="$2"; shift;;
            -H|--help) help; exit;;
            *) echo "Unknown parameter passed: $1"; exit 1 ;;
        esac
        shift
    done
}

if [ ! -f $default_vars_file ];then
    warning "default vars file not found!"
else
    source "$default_vars_file"
fi

parse_args "$@"

if [ ! -f $default_vars_file ] && [ "$opt_vars_file" == "" -o ! -f "$opt_vars_file" ] ;then
    error "both default and optional vars file not found, try 
    1) create $default_vars_file from run_vars.example, or 
    2) pass optional vars file with -F/vars-file option"
    exit 1
fi

if [ "$opt_vars_file" != "" -o -f "$opt_vars_file" ] ;then
    warning "Default vars are overwritten by optional vars file"
    source $opt_vars_file
fi

if [ ! -n "$image_name" ];then
	echo "image_name is not given with --image option, use QEMU_IMG ($QEMU_IMG)"
	image_name=$QEMU_IMG
fi

if [ ! -s "$ssh_port" ];then
    ssh_port="2024"
fi
net_config="-netdev user,id=network0,hostfwd=tcp::$ssh_port-:22 -device e1000,netdev=network0" 

display_options

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
    ssh root@localhost -p $ssh_port
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

if [ -n "$cmd_str" ]; then
    exec_cmd
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

