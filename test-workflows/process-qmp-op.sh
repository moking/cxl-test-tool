#! /bin/bash

find_dcd_name_from_qemu_cmd_line() {
    line=`ps -ef | grep qemu-system | sed 's/.*dc-regions/dc-regions/'`
    echo $line | awk '{print $1}' | awk -F, '{print $2}' | awk -F= '{print $2}'
}
devname=`find_dcd_name_from_qemu_cmd_line`

create_cmd_line(){
    op=$1
    extent=$2
    body="
    { \"execute\": \"qmp_capabilities\" }

    { \"execute\": \"$op\",
        \"arguments\": {
        \"path\": \"/machine/peripheral/$devname\",
        \"host-id\": 0,
        \"selection-policy\": \"prescriptive\",
        \"region\": 0,
        \"extents\": [
        $extent
        ]
    }
    }"
    echo $body
}

release_cmd_line(){
    op=$1
    extent=$2
    body="
    { \"execute\": \"qmp_capabilities\" }

    { \"execute\": \"$op\",
        \"arguments\": {
        \"path\": \"/machine/peripheral/$devname\",
        \"host-id\": 0,
        \"removal-policy\":\"prescriptive\",
        \"forced-removal\": false,
        \"region\": 0,
        \"extents\": [
        $extent
        ]
    }
    }"
    echo $body
}
    

extent() {
    dpa=$1
    len=$2
    first_time=$3

    dpa=$((dpa*1024*1024))
    len=$((len*1024*1024))
    
    if [ -z "$first_time" ];then
    echo ",
        {
        \"offset\": $dpa,
        \"len\": $len
        }
    "
else
    echo "
        {
        \"offset\": $dpa,
        \"len\": $len
        }
    "
fi
}

print='
 { "execute": "qmp_capabilities" }

	{ "execute": "cxl-display-accepted-dc-extents",
	  "arguments": {
		  "path": "/machine/peripheral/'$devname'",
          "output": "/tmp/dc-extent.txt"
      }
    }
	{ "execute": "cxl-display-pending-to-add-dc-extents",
	  "arguments": {
		  "path": "/machine/peripheral/'$devname'",
          "output": "/tmp/dc-extent.txt"
      }
    }
    '

show_extent_in_vm() {
    path="/sys/bus/cxl/devices/dax_region0/"
    cxl-tool --cmd "find $path -name extent*" > /tmp/vm-extent

    echo "extent info on the VM"
    cat /tmp/vm-extent
    echo
    items=""
    while read line; do
        first=`echo $line | grep -c "@"`
        if [ "$first" != "0" ];then
            continue
        fi
        offset=$line/offset
        length=$line/length
        items="$items $offset $length"
    done < /tmp/vm-extent

    for item in $items; do
        cxl-tool --cmd "cat $item"
    done
    echo
}

extent_file=/tmp/dc-extent.txt
show_extent(){
    rm -f $extent_file
    echo $print > /tmp/qmp-print.conf
    cxl-tool --issue-qmp /tmp/qmp-print.conf
    cat $extent_file
    echo
    show_extent_in_vm
}

p=`extent 0 128 abc`
p=$p`extent 128 128`
p=$p`extent 256 128`

parse_ext_str() {
    str=$1
    echo $str | sed 's/,/\n/g' > /tmp/ext-str

    rs=""

    while read line; do
        start=`echo $line | awk -F- '{print $1}'`
        end=`echo $line | awk -F- '{print $2}'`
        len=$((end-start))

        if [ -z "$rs" ]; then
            rs=$rs`extent $start $len abc`
        else
            rs=$rs`extent $start $len`
        fi
    done < /tmp/ext-str
    echo $rs

}

echo $print >  /tmp/qmp-print.conf

rand=false
loops=10
if [ "$1" == "-r" ];then
    rand=true
    if [ "$2" != "" ];then
        loops=$2
        loops=$((loops))
    fi
elif [ "$1" == "" ];then
    rand=false
else
    echo "unknown input argument: $1"
    exit
fi

loop=0
if $rand; then
    while true; do
        if [ $loop -eq $loops ];then
            break;
        fi
        loop=$((loop+1))
        echo "Choose OP: 0: add, 1: release, 2: print extent, 9: exit"
        choice=$(( ( RANDOM % 10 )))
        if [ "$choice" == "2" ];then
            show_extent
        elif [ "$choice" == "9" ];then
            break;
        elif [ $choice -le 5 ];then
            choice=0
        else
            choice=1
        fi

        if [ "$choice" == "0" ];then
            op="cxl-add-dynamic-capacity"
            echo "Input extent to add, for example (unit: MB): 0-128[,128-256]"
            end=$(( ( RANDOM % 16 + 1)*16))
            start=$((end-16))
            #read ext_str
            ext_str="$start-$end"
            exts=`parse_ext_str $ext_str`
            echo Add $ext_str
            create_cmd_line $op "$exts" |tee /tmp/qmp.conf
            cxl-tool --issue-qmp /tmp/qmp.conf
            show_extent
        else
            op="cxl-release-dynamic-capacity"
            echo "Input extent to add, for example (unit: MB): 0-128[,128-256]"
            #read ext_str
            end=$(( ( RANDOM % 16 + 1)*16))
            start=$((end-16))
            #read ext_str
            ext_str="$start-$end"
            exts=`parse_ext_str $ext_str`
            echo release $ext_str
            release_cmd_line $op "$exts" |tee /tmp/qmp.conf
            cxl-tool --issue-qmp /tmp/qmp.conf
            show_extent
        fi
    done
else
    while true; do
        echo "Choose OP: 0: add, 1: release, 2: print extent, 9: exit"
        read choice
        if [ "$choice" == "0" ];then
            op="cxl-add-dynamic-capacity"
            echo "Input extent to add, for example (unit: MB): 0-128[,128-256]"
            read ext_str
            exts=`parse_ext_str $ext_str`
            create_cmd_line $op "$exts" |tee /tmp/qmp.conf
            cxl-tool --issue-qmp /tmp/qmp.conf
        elif [ "$choice" == "1" ];then
            op="cxl-release-dynamic-capacity"
            echo "Input extent to add, for example (unit: MB): 0-128[,128-256]"
            read ext_str
            exts=`parse_ext_str $ext_str`
            release_cmd_line $op "$exts" |tee /tmp/qmp.conf
            cxl-tool --issue-qmp /tmp/qmp.conf
        elif [ "$choice" == "2" ];then
            show_extent
        elif [ "$choice" == "9" ];then
            break;
        else
            echo "choice not accepted"
        fi
    done
fi
