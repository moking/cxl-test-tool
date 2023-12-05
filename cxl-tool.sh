#! /bin/bash
extra_opts=""

default_vars_file=./.vars.config
opt_vars_file=""
image_name=""

top_file=/tmp/topo.txt
echo "" > $top_file

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
    echo "** Task: $@ **"
    echo
}

get_val() {
    key=$1
    val=`cat /tmp/cxl-val | grep -w "$key" | awk -F= '{print $2}'`
    echo $val
}

inc() {
    key=$1
    line=`cat /tmp/cxl-val | grep -w "$key"`
    val=`cat /tmp/cxl-val | grep -w "$key" | awk -F= '{print $2}'`
    val=$(($val+1))
    newline=$key"="$val
    sed -i "s/$line/$newline/g" /tmp/cxl-val
}

create_object() {
    name=$1
    size=$2
    path=$3
    if [ "$path" == "" -o ! -d $path ];then
        path=/tmp/
    fi

        if [ "$size" == "" ];then
            size="512M"
    fi
    echo "-object memory-backend-file,id=$name,share=on,mem-path=$path/$name.raw,size=$size " >> $top_file
    echo $name
}

create_cxl_bus() {
    bus=`get_val "bus"`
    bus_nr=`get_val "bus_nr"`
    echo "-device pxb-cxl,bus_nr=$bus_nr,bus=pcie.0,id=cxl.$bus " >> $top_file
    echo "cxl.$bus"
    inc "bus"
    inc "bus_nr"
 }

create_cxl_rp() {
    rp=`get_val "rp"`
    slot=`get_val "slot"`
    chassis=`get_val "chassis"`
    echo "-device cxl-rp,port=$rp,bus=cxl.1,id=root_port$rp,chassis=$chassis,slot=$slot " >> $top_file
    echo "root_port$rp"
    inc "rp"
    inc "slot"
}

create_cxl_mem() {
     port_name=$1
     mem_id=`get_val "mem_id"`
     mem=$(create_object "mem$mem_id")
     lsa=$(create_object "lsa$mem_id")
     echo "-device cxl-type3,bus=$port_name,memdev=$mem,lsa=$lsa,id=cxl-memdev$mem_id ">>$top_file
     echo "cxl-memdev$mem_id"
     inc "mem_id"
}

create_cxl_fmw() {
    size=$1
    bus=$2
    fmw=`get_val "fmw"`
    if [ "$size" == "" ];then
        size="4G"
    fi
    if [ "$bus" == "" ];then
        bus="cxl.1"
    fi
    ig="8k"
    echo "-M cxl-fmw.0.targets.0=$bus,cxl-fmw.$fmw.size=$size,cxl-fmw.$fmw.interleave-granularity=$ig " >> $top_file 
    echo "cx-fmw.$fmw"
    inc "fmw"
}

gen_topology_str() {
    topo_str=`cat $top_file`
    topo_str=`echo $topo_str |sed "s/\n/ /g"`
    echo $topo_str
}


create_topology() {
    bus1=`create_cxl_bus`
    rp1=`create_cxl_rp`
    rp2=`create_cxl_rp`
    mem=$(create_cxl_mem $rp1)
    mem2=$(create_cxl_mem $rp2)
    fmw=$(create_cxl_fmw)

    topo=`gen_topology_str`
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

    echo "QEMU=$QEMU" > $run_opts_file
    echo "KERNEL_PATH=$KERNEL_PATH" >> $run_opts_file
    echo "SHARED_CFG=\"$SHARED_CFG\"" >> $run_opts_file
    echo "net_config=\"$net_config\"" >> $run_opts_file
    echo "topo=\"$topo\"" >> $run_opts_file
    echo "QEMU_IMG=$QEMU_IMG" >> $run_opts_file
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
        $topo 1>&/dev/null" > /tmp/cmd

    ${QEMU} -s\
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
        $topo 1>&/dev/null &

    sleep 2
    running=`ps -ef | grep qemu-system-x86_64 | grep -c raw`
    if [ $running -gt 0 ];then
        echo "QEMU:running" > /tmp/qemu-status
        echo "QEMU instance is up, access it: ssh root@localhost -p $ssh_port"
        sleep 2
    else
        echo "Qemu: start Fail!"
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
    -C,--cmd  \t\t shell command series to execute on the VM
    -T,--topology  \t CXL topology to use for qemu emulation:
        sw: \t with a switch
        rp1: \t with only one root port
        hb2: \t with two home bridges
        m2: \t with two memdev and 1 HB
    -N,--CPUS \t\t number of CPUs created for the VM
    -E,--extra-opts \t extra options to pass to qemu when launching
    -A,--accel \t\t acceleration mode: tcg (default)/kvm/...
    -Q,--qemu-root \t Qemu directory
    -K,--kernel \t Linux kernel directory
    -BK,--build-kernel \t flag to build kernel
    -BQ,--build-qemu \t flag to build qemu
    -I,--create \t create qemu image
    --install-ndctl \t flag to install ndctl
    --gen-topo \t\t flag to generate topology
    --ndctl-url \t url to git clone ndctl
    --qemu-url \t\t url to git clone ndctl
    --kernel-url \t url to git clone ndctl
    --ndctl-branch \t ndctl branch
    --qemu-branch \t qemu branch
    --load-drv \t\t load cxl driver
    --setup-qemu \t git clone, configure, make and install qemu
    --setup-kernel \t git clone, configure, make and install kernel
    --kernel-branch \t kernel branch
    -P,--port \t\t port to ssh to VM
    -L,--login \t\t login the VM
    -R,--run \t\t start qemu
    --reset \t\t reset the VM instance
    --poweroff \t\t shutdown the VM instance
    --shutdown \t\t shutdown the VM instance
    --kdb \t\t debug kernel with gdb
    --ndb \t\t debug ndctl inside VM with gdb, followed with cxl operations
    --qdb \t\t debug qemu with gdb, may need to launch gdb with -S option
    --kconfig \t\t configure kernel with make menuconfig
    --cxl-mem-setup \t\t set up cxl memory as regular memory and online
    -H,--help \t\t display help information
    '
}

cleanup() {
    rm -f /tmp/lsa*
    rm -f /tmp/cxltest*
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
    kdb=false
    ndb=false
    qdb=false
    opt_nbd="cxl"
    kconfig=false
    cxl_mem_setup=false
    test_cxl=false
}

display_options() {
    echo "***************************"
    echo Run $0 with options:
    echo " mode $accel_mode"
    echo " num_cpus $num_cpus"
    echo " topology $TOPO"
    echo " build_qemu $build_qemu "
    echo " deploy_kernel $deploy_kernel"
    echo " KERNEL_ROOT $KERNEL_ROOT"
    echo " QEMU_ROOT $QEMU_ROOT"
    echo " QEMU_IMG $QEMU_IMG "
    echo " create_image $create_image "
    echo " run $run "
    echo " shutdown $shutdown "
    echo " reset $reset "
    echo " install_ndctl $install_ndctl "
    echo " generate topology $gen_topo "

    echo "***************************"
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
    echo $topo > /tmp/cxl-top.txt
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

    ssh-keygen -f "/home/fan/.ssh/known_hosts" -R "[localhost]:2024"
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
        libcap-ng-dev libattr1-dev
    echo
    echo git clone -b $qemu_branch --single-branch $url $QEMU_ROOT
    git clone -b $qemu_branch --single-branch $url $QEMU_ROOT
    echo
    cd $QEMU_ROOT
    echo ./configure --target-list=x86_64-softmmu --enable-debug
    ./configure --target-list=x86_64-softmmu --enable-debug
    echo
    echo "make -j8"
    make -j8
}

kernel_setup() {
    echo_task "setup kernel: git clone, compile and install modules -- started"

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

    echo_task "Configure the kernel..."
    echo -n "Configure mannually (1) or copy the example config (2): "
    read choice

    if [ "$choice" == "1" ]; then
        make menuconfig
    else
        echo "Copy the example config as .config"
        cp kconfig.example $KERNEL_ROOT/.config
    fi

    echo_task "Compile the kernel in $KERNEL_ROOT"
    cd $KERNEL_ROOT
    make -j 16

    echo_task "Install kernel modules"
    sudo make modules_install
    
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
    echo ssh root@localhost -p $ssh_port "cd ndctl; gdb --args build/cxl/$opt"
    ssh root@localhost -p $ssh_port "cd ndctl; gdb --args build/cxl/$opt"
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
        case $1 in
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
            --gen-topo) gen_topo=true ;;
            --ndctl-url) ndctl_url=$2; shift ;;
            --qemu-url) qemu_url=$2; shift ;;
            --kernel-url) kernel_url=$2; shift ;;
            --ndctl-branch) ndctl_branch=$2; shift ;;
            --qemu-branch) qemu_branch=$2; shift ;;
            --kernel-branch) kernel_branch=$2; shift ;;
            -P|--port) ssh_port="$2"; shift ;;
            -L|--login) login=true ;;
            -R|--run) run=true ;;
            --reset) reset=true ;;
            --setup-qemu) setup_qemu=true ;;
            --setup-kernel) setup_kernel=true ;;
            --poweroff|--shutdown) shutdown=true ;;
            --load-drv) load_drv=true ;;
            --kdb) kdb=true ;;
            --qdb) qdb=true ;;
            --ndb) ndb=true ; opt_nbd="$2"; shift;;
            -F/--vars-file) opt_vars_file="$2"; shift;;
            --kconfig) kconfig=true;;
            --cxl-mem-setup) cxl_mem_setup=true;;
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

parse_args $@

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

if [ -n "$image_name" ];then
    QEMU_IMG=$image_name
fi

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

if $create_image && [ -n "$image_name" ];then
    create_qemu_image
fi


QEMU=$QEMU_ROOT/build/qemu-system-x86_64
KERNEL_PATH=$KERNEL_ROOT/arch/x86/boot/bzImage

if $gen_topo; then
    echo "Create cxl topology..."
    create_topology
else
    echo "Use cxl topology defined..."
    topo=$(get_cxl_topology $TOPO)
fi

if [ ! -s "$port" ];then
    ssh_port="2024"
fi
net_config="-netdev user,id=network0,hostfwd=tcp::$ssh_port-:22 -device e1000,netdev=network0" 


if $run; then
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


    run_qemu "$topo"
fi
if $login; then
    ssh root@localhost -p $ssh_port
fi

if $shutdown; then
    shutdown_qemu
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

if $kconfig; then
    configure_kernel
fi

if $cxl_mem_setup; then
    setup_cxl_memory
fi

cleanup
