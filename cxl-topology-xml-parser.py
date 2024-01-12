import xml.etree.ElementTree as ET
import os
import argparse

rp=13
mem_id=0
slot=2
chassis=0
bus=1
bus_nr=12
fmw=0
us_port=0
ds_port=0
num_hb_found=0

def create_object(name, size="512M", path="/tmp"):
    return name, "-object memory-backend-file,id=%s,share=on,mem-path=%s/%s.raw,size=%s "%(name,path,name,size)

def create_cxl_bus():
    global bus, bus_nr
    name = "cxl.%s"%bus
    rs = "-device pxb-cxl,bus_nr=%s,bus=pcie.0,id=%s "%(bus_nr, name)
    bus = bus + 1
    bus_nr += 100
    return name, rs

def create_cxl_rp(bus="cxl.1"):
    global rp, slot, chassis
    name="root_port%s"%rp
    rs= "-device cxl-rp,port=%s,bus=%s,id=root_port%s,chassis=%s,slot=%s "\
    %(rp, bus, rp, chassis, slot)
    rp += 1
    slot += 1
    return name, rs

def create_cxl_pmem(parent_dport, size="512M"):
    global mem_id
    hmem, hmem_str=create_object("hmem%s"%mem_id, size=size)
    lsa, lsa_str=create_object("lsa%s"%mem_id)
    name = "cxl-memdev%s"%mem_id
    mem_str= "-device cxl-type3,bus=%s,memdev=%s,lsa=%s,id=cxl-memdev%s "%(parent_dport, hmem, lsa, mem_id)
    mem_id += 1

    return name, hmem_str+lsa_str+mem_str

def create_cxl_vmem(parent_dport, size="512M"):
    global mem_id
    hmem, hmem_str=create_object("hmem%s"%mem_id, size=size)
    name = "cxl-memdev%s"%mem_id
    mem_str= "-device cxl-type3,bus=%s,volatile-memdev=%s,id=cxl-vmemdev%s "%(parent_dport, hmem, mem_id)
    mem_id += 1

    return name, hmem_str+mem_str

def create_cxl_mem(parent_dport, pmem=True, vmem=False, dcd=False):
    global mem_id
    prefix= "-device cxl-type3,bus=%s,"%parent_dport
    lsa, lsa_str=create_object("lsa%s"%mem_id)
    name = "cxl-memdev%s "%mem_id
    suffix="id=%s"%name
    hmem_str=""
    vhmem_str=""
    dhmem_str=""
    pmem_str=""
    vmem_str=""
    dcd_str=""
    if pmem:
        hmem, hmem_str=create_object("hmem%s"%mem_id)
        pmem_str= "memdev=%s,lsa=%s,"%(hmem, lsa)
    if vmem:
        vhmem, vhmem_str=create_object("vhmem%s"%mem_id)
        vmem_str= "volatile-memdev=%s,"%(vhmem)
    if dcd:
        dhmem, dhmem_str=create_object("dhmem%s"%mem_id, size="4G")
        dcd_str="nonvolatile-dc-memdev=%s,num-dc-regions=2,"%dhmem

    mem_id += 1
    return name, hmem_str+vhmem_str+dhmem_str+lsa_str+prefix+pmem_str+vmem_str+dcd_str+suffix


def create_cxl_switch(parent_dport, num_dsp=2):
    global us_port
    up_name="us%s"%us_port
    upstream= "-device cxl-upstream,bus=%s,id=%s "%(parent_dport, up_name)
    downstreams=""
    # for did in range(num_dsp):
        # ds_name = "swport%s"%did
        # downstreams += "-device cxl-downstream,port=%s,bus=%s,id=%s,chassis=0,slot=4 " \
                # %(did, up_name, ds_name)
    us_port += 1
    return up_name, upstream+downstreams

def create_cxl_dsp(parent_dport, dsid):
    global ds_port, slot
    ds_name = "swport%s"%ds_port
    # print(parent_dport, ds_name)
    rs = "-device cxl-downstream,port=%s,bus=%s,id=%s,chassis=0,slot=%s " \
            %(dsid, parent_dport, ds_name, slot)
    ds_port += 1
    slot += 1
    return ds_name, rs

def create_fmw(size="4G", ig="8k"):
    global fmw
    name="cxl-fmw.%s"%fmw
    bus_str=""
    for i in range(num_hb_found):
        bus = "cxl.%s"%(i+1)
        bus_str+="%s.targets.%s=%s,"%(name, i, bus)

    rs = "-M %s%s.size=%s,%s.interleave-granularity=%s " \
            %(bus_str, name, size, name, ig)
    fmw += 1
    return name,rs

# s: include the all string for qemu arguemnts
def parse_topo(root, p="", s=""):
    global num_hb_found
    name=""
    if root.tag == "host_bridge":
        name,rs=create_cxl_bus()
        num_hb_found += 1
        s += rs
    else:
        if root.tag == "rp":
            size="512M"
            if root.attrib.get("size"):
                size = root.attrib["size"]
            name, rs = create_cxl_rp(p)
            s += rs
            if root.text =="pmem":
                name, rs = create_cxl_pmem(name, size)
                s += rs
            if root.text =="vmem":
                name, rs = create_cxl_vmem(name, size)
                s += rs
            if root.text == "mixed":
                name, rs = create_cxl_mem(name, pmem=True, vmem=True)
                s += rs
            if root.text == "mixed-dcd":
                name, rs = create_cxl_mem(name, pmem=True, vmem=True, dcd=True)
                s += rs
            if root.text == "dcd":
                name, rs = create_cxl_mem(name, pmem=False, vmem=False, dcd=True)
                s += rs
        elif root.tag == "switch":
            name, rs = create_cxl_switch(p)
            s += rs
        elif root.tag == "dsp":
            dsid=root.attrib["id"]
            size="512M"
            if root.attrib.get("size"):
                size = root.attrib["size"]
            name, rs = create_cxl_dsp(p, dsid)
            s += rs
            if root.text == "pmem":
                name, rs = create_cxl_pmem(name, size)
                s += rs
            if root.text == "vmem":
                name, rs = create_cxl_vmem(name, size)
                s += rs
            if root.text == "mixed":
                name, rs = create_cxl_mem(name, pmem=True, vmem=True)
                s += rs
            if root.text == "mixed-dcd":
                name, rs = create_cxl_mem(name, pmem=True, vmem=True, dcd=True)
                s += rs
            if root.text == "dcd":
                name, rs = create_cxl_mem(name, pmem=False, vmem=False, dcd=True)
                s += rs
        elif root.tag == "fmw":
            size = root.attrib.get("size", "4G")
            ig = root.attrib.get("ig", "8K")
            name, rs = create_fmw(size=size, ig=ig)
            s += rs
            return s
            
    for child in root:
        s = parse_topo(child, name, s)
    return s

parser = argparse.ArgumentParser(description='A tool to generate qemu command line arguments for cxl topology from xml file')
parser.add_argument('-F','--file', help='path to xml file', required=False, default='.cxl-topology.xml')
args = vars(parser.parse_args())

top_xml=args["file"]
if not os.path.exists(top_xml):
    print("Error: topology xml: %s not found, create one by copy cxl-topology.xml.example"%top_xml)
    exit(1)
tree = ET.parse(top_xml)
root = tree.getroot()
qemu_str = parse_topo(root, "")
print(qemu_str)
