import os;
import utils.tools as tools
import psutil;

RP1="-object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest.raw,size=512M \
     -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa.raw,size=1M \
     -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
     -device cxl-rp,port=0,bus=cxl.1,id=root_port13,chassis=0,slot=2 \
     -device cxl-type3,bus=root_port13,memdev=cxl-mem1,lsa=cxl-lsa1,id=cxl-pmem0,sn=0xabcd \
     -M cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=8k"

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

FM_DCD="-object memory-backend-file,id=cxl-mem1,mem-path=/tmp/t3_cxl1.raw,size=256M \
 -object memory-backend-file,id=cxl-lsa1,mem-path=/tmp/t3_lsa1.raw,size=1M \
 -object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=512M \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -object memory-backend-file,id=cxl-mem3,mem-path=/tmp/t3_cxl3.raw,size=512M \
 -object memory-backend-file,id=cxl-lsa3,mem-path=/tmp/t3_lsa3.raw,size=2M \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-downstream,port=4,bus=us0,id=swport3,chassis=0,slot=7 \
 -device cxl-type3,bus=swport0,memdev=cxl-mem1,id=cxl-pmem1,lsa=cxl-lsa1,sn=3 \
 -device cxl-type3,bus=swport2,memdev=cxl-mem2,id=cxl-pmem2,lsa=cxl-lsa2,sn=4 \
 -device cxl-type3,bus=swport3,volatile-dc-memdev=cxl-mem3,id=cxl-dcd0,num-dc-regions=2,sn=99\
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=4,target=us0 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=5,target=cxl-pmem1 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=6,target=cxl-pmem2 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=7,target=cxl-dcd0 \
 -device virtio-rng-pci,bus=swport1"

FM_DCD="-object memory-backend-file,id=cxl-mem1,mem-path=/tmp/t3_cxl1.raw,size=256M \
 -object memory-backend-file,id=cxl-lsa1,mem-path=/tmp/t3_lsa1.raw,size=1M \
 -object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=4G \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-type3,bus=swport0,memdev=cxl-mem1,id=cxl-pmem1,lsa=cxl-lsa1,sn=3 \
 -device cxl-type3,bus=swport2,volatile-dc-memdev=cxl-mem2,id=cxl-dcd0,lsa=cxl-lsa2,num-dc-regions=2,sn=99 \
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=4,target=us0 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=5,target=cxl-pmem1 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=6,target=cxl-dcd0 \
 -device virtio-rng-pci,bus=swport1"

FM_TARGET="-object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=4G \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-type3,bus=swport2,volatile-dc-memdev=cxl-mem2,id=cxl-dcd0,lsa=cxl-lsa2,num-dc-regions=1,sn=99,allow-fm-attach=on,mctp-buf-init=on \
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=4,target=us0 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=6,target=cxl-dcd0 \
 -device virtio-rng-pci,bus=swport1"

FM_CLIENT="-object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=4G \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-type3,bus=swport2,volatile-dc-memdev=cxl-mem2,id=cxl-dcd0,lsa=cxl-lsa2,num-dc-regions=1,sn=99,allow-fm-attach=on \
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=4,target=us0 \
 -device i2c_mctp_cxl,bus=aspeed.i2c.bus.0,address=6,target=cxl-dcd0,qmp=127.0.0.1:4445,mctp-msg-forward=on \
 -device virtio-rng-pci,bus=swport1"



SW="-object memory-backend-file,id=cxl-mem0,share=on,mem-path=/tmp/cxltest.raw,size=512M \
    -object memory-backend-file,id=cxl-mem1,share=on,mem-path=/tmp/cxltest1.raw,size=512M \
    -object memory-backend-file,id=cxl-mem2,share=on,mem-path=/tmp/cxltest2.raw,size=512M \
    -object memory-backend-file,id=cxl-mem3,share=on,mem-path=/tmp/cxltest3.raw,size=512M \
    -object memory-backend-file,id=cxl-lsa0,share=on,mem-path=/tmp/lsa0.raw,size=2M \
    -object memory-backend-file,id=cxl-lsa1,share=on,mem-path=/tmp/lsa1.raw,size=2M \
    -object memory-backend-file,id=cxl-lsa2,share=on,mem-path=/tmp/lsa2.raw,size=2M \
    -object memory-backend-file,id=cxl-lsa3,share=on,mem-path=/tmp/lsa3.raw,size=2M \
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

FM_USB="-object memory-backend-file,id=cxl-mem1,mem-path=/tmp/t3_cxl1.raw,size=256M \
 -object memory-backend-file,id=cxl-lsa1,mem-path=/tmp/t3_lsa1.raw,size=1M \
 -object memory-backend-file,id=cxl-mem2,mem-path=/tmp/t3_cxl2.raw,size=4G \
 -object memory-backend-file,id=cxl-lsa2,mem-path=/tmp/t3_lsa2.raw,size=1M \
 -device usb-ehci,id=ehci \
 -device pxb-cxl,bus_nr=12,bus=pcie.0,id=cxl.1,hdm_for_passthrough=true \
 -device cxl-rp,port=0,bus=cxl.1,id=cxl_rp_port0,chassis=0,slot=2 \
 -device cxl-upstream,port=2,sn=1234,bus=cxl_rp_port0,id=us0,addr=0.0,multifunction=on, \
 -device cxl-switch-mailbox-cci,bus=cxl_rp_port0,addr=0.1,target=us0 \
 -device cxl-downstream,port=0,bus=us0,id=swport0,chassis=0,slot=4 \
 -device cxl-downstream,port=1,bus=us0,id=swport1,chassis=0,slot=5 \
 -device cxl-downstream,port=3,bus=us0,id=swport2,chassis=0,slot=6 \
 -device cxl-type3,bus=swport0,memdev=cxl-mem1,id=cxl-pmem1,lsa=cxl-lsa1,sn=3 \
 -device cxl-type3,bus=swport2,volatile-dc-memdev=cxl-mem2,id=cxl-dcd0,lsa=cxl-lsa2,num-dc-regions=2,sn=99 \
 -machine cxl-fmw.0.targets.0=cxl.1,cxl-fmw.0.size=4G,cxl-fmw.0.interleave-granularity=1k \
 -device virtio-rng-pci,bus=swport1 \
 -device usb-cxl-mctp,bus=ehci.0,id=usb1,target=us0 \
 -device usb-cxl-mctp,bus=ehci.0,id=usb2,target=cxl-pmem1"


topos = {
    "RP1": RP1,
    "FM": FM,
    "FM_CLIENT": FM_CLIENT,
    "FM_TARGET": FM_TARGET,
    "SW": SW,
    "FM_USB": FM_USB
}

def find_topology(top):
    topo = topos.get(top.upper(), "")
    return topo

def load_driver(host="localhost"):
    user = tools.system_env("vm_usr")
    if user == "root":
        tools.execute_on_vm("modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem", echo=True)
        tools.execute_on_vm("modprobe -a nd_pmem")
        tools.execute_on_vm("modprobe -a dax device_dax dax_pmem")
    else:
        tools.execute_on_vm("sudo modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem")
        tools.execute_on_vm("sudo modprobe -a nd_pmem")
        tools.execute_on_vm("sudo modprobe -a dax device_dax dax_pmem")

    rs=tools.execute_on_vm("lsmod")
    print(rs)

def unload_driver(host="localhost"):
    user = tools.system_env("vm_usr")
    if user == "root":
        tools.execute_on_vm("modprobe -r cxl_pmem cxl_mem cxl_port cxl_pci cxl_acpi cxl_pmu cxl_core")
        tools.execute_on_vm("modprobe -r nd_pmem")
        tools.execute_on_vm("modprobe -r dax_pmem device_dax dax nd_btt libnvdimm dax_pmem")
    else:
        tools.execute_on_vm("sudo modprobe -r cxl_pmem cxl_mem cxl_port cxl_pci cxl_acpi cxl_pmu cxl_core")
        tools.execute_on_vm("sudo modprobe -r nd_pmem")
        tools.execute_on_vm("sudo modprobe -r device_dax dax nd_btt libnvdimm dax_pmem")

    rs=tools.execute_on_vm("lsmod")
    print(rs)

def cxl_driver_loaded():
    cmd="cxl list -i"
    rs=tools.execute_on_vm(cmd)
    data = tools.output_to_json_data(rs)
    if not data:
        return False
    return True

def device_is_active(memdev):
    cmd="cxl list -i -m %s"%memdev
    rs=tools.execute_on_vm(cmd)
    data = tools.output_to_json_data(rs)
    if not data:
        return False;
    for key in data[0].keys():
        if key == "state":
            if data[0][key] == "disabled":
                return False;
            else:
                return True;
    return False

def enable_memdev(memdev):
    cmd="cxl enable-memdev %s"%memdev
    rs=tools.execute_on_vm(cmd, echo=True)

def find_serial(memdev):
    cmd = "cxl list -m %s -i"%memdev
    rs=tools.execute_on_vm(cmd)
    if not rs:
        return ""
    data = tools.output_to_json_data(rs)
    return data[0]["serial"]

def find_cmdline_device_id(memdev):
    name="qemu-system"
    serial=find_serial(memdev)
    key="sn=%s"%serial
    print(key)
    for process in psutil.process_iter(['name', 'cmdline']):
        try:
            # Check if the process name matches
            if name in process.info['name']:
                cmd=process.info['cmdline']
                for c in cmd:
                    if "dc-region" in c and key in c:
                        args=c.split(",")
                        for arg in args:
                            if arg.strip().startswith("id"):
                                return arg.split("=")[1]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue;

def find_mode(memdev):
    # file=tools.system_path("cxl_test_log_dir")+"/tmp.json"
    rs=tools.execute_on_vm("cxl list -i -m %s"%memdev)
    data=tools.output_to_json_data(rs)
    if not data:
        return None
    for key in data[0].keys():
        if "_size" in key:
            return key.split("_")[0]
    return "dc0"

def memdev_size(memdev):
    # file=tools.system_path("cxl_test_log_dir")+"/tmp.json"
    rs=tools.execute_on_vm("cxl list -i -m %s"%memdev)
    data=tools.output_to_json_data(rs)
    if not data:
        return 0
    for key in data[0].keys():
        if "_size" in key:
            return int(data[0][key])
    print("Warning: No size field found, check whether it is DCD")
    return 0

def find_key_in_json_data(data, key):
    res=[]
    if not data or not key:
        return []
    for d in data:
        for k in d.keys():
            if k == key:
                res.append(d[k])
            elif isinstance(d[k], list):
                rs = find_key_in_json_data(d[k], key)
                if rs:
                    for i in rs:
                        res.append(i)
    return res

def region_exists_for_device(memdev):
    cmd="cxl list -Ri"
    rs=tools.execute_on_vm(cmd)
    json=tools.output_to_json_data(rs)
    #print(rs)
    regions=find_key_in_json_data(json, "region")
    if not regions:
        return ""

    for region in regions:
        cmd="cxl list -v -r %s"%region
        rs=tools.execute_on_vm(cmd)
        json=tools.output_to_json_data(rs)

        rs=find_key_in_json_data(json, "memdev")
        if memdev in rs:
            return region
    return ""


def create_region(memdev):
    file=tools.system_path("cxl_test_log_dir")+"/tmp.json"

    if not cxl_driver_loaded():
        print("Load cxl drivers")
        load_driver();

    region=region_exists_for_device(memdev)
    if region:
        print("%s already created for %s, exit"%(region, memdev))
        return ""

    if not device_is_active(memdev):
        enable_memdev(memdev)

    mode=find_mode(memdev)
    size=memdev_size(memdev)
    if size == 0:
        print("no device size found, exit")
        return
    sz_str = "%sM"%(size//1024//1024)
    cmd="cxl create-region -m -d decoder0.0 -w 1 %s -s %s -t %s"%(memdev, sz_str, mode)
    print("# "+cmd)
    output=tools.execute_on_vm(cmd)
    print(output)
    region_info = tools.output_to_json_data(output)
    region = region_info.get("region", "")
    return region

def destroy_region(region):
    if not region:
        print("Cannot delete region due to wrong region input")
        return "ERROR"
    cmd="cxl destroy-region %s -f"%(region)
    print("# "+cmd)
    rs=tools.execute_on_vm(cmd)
    print(rs)

def create_namespace(region):
    if not region:
        print("Cannot create namespace due to wrong region input")
        return "",""
    cmd="ndctl create-namespace -m dax -r %s"%region
    print(cmd)
    output=tools.execute_on_vm(cmd)
    print(output)

    file=tools.system_path("cxl_test_log_dir")+"/tmp.json"
    tools.write_to_file(file, output)
    ns=""
    dax=""
    with open(file, "r") as f:
        for line in f:
            if "\"chardev\"" in line:
                dax = line.split(":")[1].replace(",", "").strip()
                break
            if "\"dev\":" in line:
                ns = line.split(":")[1].replace(",", "").strip()

        return ns,dax

def destroy_namespace(ns):
    if not ns:
        print("Cannot delete namespace due to wrong namespace input")
        return "ERROR"
    cmd="cxl destroy-namespace %s -f"%(ns)
    print("# "+cmd)
    rs=tools.execute_on_vm(cmd)
    print(rs)

def find_endpoint_num(memdev):
    cmd="cxl list -E -m %s"%memdev
    out=tools.execute_on_vm(cmd)
    data = tools.output_to_json_data(out)
    if not data:
        print("Cannot found decoder for %s"%memdev)
        return ""
    return data[0]["endpoint"].replace("endpoint", "")

def create_dax_device(region, echo=False):
    if not region:
        return ""

    cmd="daxctl create-device -r %s"%region
    if echo:
        print(cmd)
    rs=tools.execute_on_vm(cmd)
    if echo:
        print(rs)
    cmd="daxctl list -r %s -D"%region
    if echo:
        print(cmd)
    rs=tools.execute_on_vm(cmd)
    if echo:
        print(rs)
    data=tools.output_to_json_data(rs)
    if not data:
        return ""

    return data[-1]["chardev"]


def create_dc_region(memdev):
    if not memdev:
        return ""

    if not cxl_driver_loaded():
        print("Load cxl drivers")
        load_driver();

    region=region_exists_for_device(memdev)
    if region:
        print("%s already created for %s, exit"%(region, memdev))
        return region

    if not device_is_active(memdev):
        enable_memdev(memdev)

    mode=find_mode(memdev)
    if not mode.startswith("dc") and not mode.startswith("dynamic"):
        print("%s is not DCD device, skip"%memdev)
        return ""

    region=region_exists_for_device(memdev)
    if region:
        print("%s already created for %s, return directly"%(region, memdev))
        return region

    # This is from the last kernel code, for creating region, we use
    #  cxl create-region -m mem0 -d decoder0.0 -s 4G -t dynamic_ram_a
    if mode.startswith("dynamic"):
        size=memdev_size(memdev)
        cmd = "cxl create-region -m mem0 -d decoder0.0 -s %s -t %s"%(size,
                                                                     os.getenv("dc_mode"))
        rs = tools.execute_on_vm(cmd)
        print(rs)
        region_info = tools.output_to_json_data(rs)
        if region_info:
            region = region_info.get("region", "")
        else:
            region = ""
        return region

    num=find_endpoint_num(memdev)
    if not num:
        print("Cannot find endpoint, exit")
        return ""
    rid="dc0"
    cmd="cat /sys/bus/cxl/devices/decoder0.0/create_dc_region"
    region=tools.execute_on_vm(cmd)
    if not region:
        print("read create_dc_region failed, abort")
        return ""
    cmd_str='''\
      echo %s > /sys/bus/cxl/devices/decoder0.0/create_dc_region; \
      echo 256 > /sys/bus/cxl/devices/%s/interleave_granularity; \
      echo 1 > /sys/bus/cxl/devices/%s/interleave_ways; \
      echo %s >/sys/bus/cxl/devices/decoder%s.0/mode; \
      echo 0x40000000 >/sys/bus/cxl/devices/decoder%s.0/dpa_size; \
      echo 0x40000000 > /sys/bus/cxl/devices/%s/size; \
      echo  decoder%s.0 > /sys/bus/cxl/devices/%s/target0; \
      echo 1 > /sys/bus/cxl/devices/%s/commit;  \
      echo %s > /sys/bus/cxl/drivers/cxl_region/bind\
      '''%(region, region, region, rid, num, num, region, num, region, region, region)

    cmds=cmd_str.split(";")
    for cmd in cmds:
        cmd=cmd.strip()
        tools.execute_on_vm(cmd, echo=True)

    cmd="cxl list -r %s"%region
    output=tools.execute_on_vm(cmd, echo=True)
    if tools.output_to_json_data(output):
        print("DC region %s created for %s"%(region, memdev))
    return region
