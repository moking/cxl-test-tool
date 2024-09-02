import utils.tools as tools
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

    region=region_exists_for_device(memdev)
    if region:
        print("%s already created for %s, exit"%(region, memdev))
        return ""

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
