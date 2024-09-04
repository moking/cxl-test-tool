import utils.tools as tools
import psutil;
def load_driver(user="root", host="localhost", port="2024"):
    tools.execute_on_vm("modprobe -a cxl_acpi cxl_core cxl_pci cxl_port cxl_mem")
    tools.execute_on_vm("modprobe -a nd_pmem")
    tools.execute_on_vm("modprobe -a dax device_dax")

    rs=tools.execute_on_vm("lsmod")
    print(rs)

def unload_driver(user="root", host="localhost", port="2024"):
    tools.execute_on_vm("rmmod -f cxl_pmem cxl_mem cxl_port cxl_pci cxl_acpi cxl_pmu cxl_core")
    tools.execute_on_vm("rmmod -f nd_pmem")
    tools.execute_on_vm("rmmod -f device_dax dax nd_btt libnvdimm")

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
    file="/tmp/tmp.json"
    rs=tools.execute_on_vm("cxl list -i -m %s"%memdev)
    data=tools.output_to_json_data(rs)
    if not data:
        return None
    for key in data[0].keys():
        if "_size" in key:
            return key.split("_")[0]
    return "dc"

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
    file="/tmp/tmp.json"

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
    cmd="cxl create-region -m -d decoder0.0 -w 1 %s -s 512M -t %s"%(memdev, mode)
    print("# "+cmd)
    output=tools.execute_on_vm(cmd)
    print(output)

    tools.write_to_file(file, output)
    with open(file, "r") as f:
        for line in f:
            if "\"region\"" in line:
                rs = line.split(":")[1].replace(",", "").strip()
                return rs
        return ""

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

    file="/tmp/tmp.json"
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

    return data[0]["chardev"]


def create_dc_region(memdev):
    if not memdev:
        return ""

    if not device_is_active(memdev):
        enable_memdev(memdev)

    mode=find_mode(memdev)
    if mode != "dc":
        print("%s is not DCD device, skip"%memdev)
        return ""

    region=region_exists_for_device(memdev)
    if region:
        print("%s already created for %s, return directly"%(region, memdev))
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
