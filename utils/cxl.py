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
    for key in data[0].keys():
        if "_size" in key:
            return key.split("_")[0]
    return "dc"

def create_region(memdev):
    file="/tmp/tmp.json"

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
