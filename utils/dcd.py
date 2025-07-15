import utils.tools as tools
import utils.cxl as cxl
import json;
import os;

extent_file="/tmp/dc-extent.txt"

#extent_list: 0-128,128-256...
def format_extent_list(extent_list):
    ext_list=[]
    extents=extent_list.split(',')
    for ext in extents:
        start=int(ext.split('-')[0])
        end=int(ext.split('-')[1])
        size=end-start

        start *= 1024*1024
        size *= 1024*1024
        item={"offset":start, "len":size}
        ext_list.append(item)
    return ext_list

def dc_region_idx():
    mode = os.getenv("dc_mode", "")
    if not mode:
        return 0;
    m = mode.split("_")
    if not m:
        return 0
    return int(m[2])

def create_add_extent_qmp_input(dev, extents):
    op="cxl-add-dynamic-capacity"

    idx = dc_region_idx()
    ext_list=format_extent_list(extents)
    body=[
    { "execute": "qmp_capabilities" }
    ,
    { "execute": "%s"%op,
    "arguments": {
        "path": "/machine/peripheral/%s"%dev,
        "host-id": 0,
        "selection-policy": "prescriptive",
        "region": idx,
        "extents": ext_list
    }
    }]
    
    file="/tmp/qmp-add.json"
    with open(file, "w") as json_file:
        json.dump(body[0], json_file, indent=4)
        json.dump(body[1], json_file, indent=4)
    return file

def create_release_extent_qmp_input(dev, extents):
    op="cxl-release-dynamic-capacity"
    
    idx = dc_region_idx()
    ext_list=format_extent_list(extents)
    body=[
    { "execute": "qmp_capabilities" }
    ,
    { "execute": "%s"%op,
        "arguments": {
        "path": "/machine/peripheral/%s"%dev,
        "host-id": 0,
        "removal-policy":"prescriptive",
        "forced-removal": False,
        "region": idx,
        "extents":ext_list
    }
    }]
    file="/tmp/qmp-rm.json"
    with open(file, "w") as json_file:
        json.dump(body[0], json_file, indent=4)
        json.dump(body[1], json_file, indent=4)
    return file

def create_display_extents_qmp_input(dev):
    op="cxl-display-accepted-dc-extents"
    op2="cxl-display-pending-to-add-dc-extents"

    body=[
    { "execute": "qmp_capabilities" }
    ,
    { "execute": "%s"%op,
     "arguments": {
         "path": "/machine/peripheral/%s"%dev,
         "output": "%s"%extent_file
         }
     },
    { "execute": "%s"%op2,
     "arguments": {
         "path": "/machine/peripheral/%s"%dev,
          "output": "/tmp/dc-extent.txt"
      }
    }
    ]

    file="/tmp/qmp-show.json"
    with open(file, "w") as json_file:
        json.dump(body[0], json_file, indent=4)
        json.dump(body[1], json_file, indent=4)
        json.dump(body[2], json_file, indent=4)
    
    return file

def show_dc_extents():
    cmd="cat %s"%extent_file
    rs=tools.sh_cmd(cmd)
    print(rs)

def handle_dc_extents_op(memdev):
    if not memdev:
        print("Need a memdev for dc extent operations")
        return;

    dev=cxl.find_cmdline_device_id(memdev)
    if not dev:
        print("Cannot find a device from command line")
        return
    
    while True:
        choice=""
        try:
            choice=input("Choose OP: 0: add, 1: release, 2: print extent, 9: exit\nChoice: ")
        except EOFError:
            pass
        if choice == "0":
            extents=input("Input extent to add, for example (unit: MB): 0-128[,128-256]\nExtents: ")
            f=create_add_extent_qmp_input(dev,extents=extents)
            tools.issue_qmp_cmd(f)
        elif choice == "1":
            extents=input("Input extent to release, for example (unit: MB): 0-128[,128-256]\nExtents: ")
            f=create_release_extent_qmp_input(dev,extents=extents)
            tools.issue_qmp_cmd(f)
        elif choice == "2":
            f=create_display_extents_qmp_input(dev)
            if os.path.exists(extent_file):
                os.remove(extent_file)
            tools.issue_qmp_cmd(f)
            show_dc_extents()

        elif choice == "9":
            return
        else:
            print("Choice not accepted")
