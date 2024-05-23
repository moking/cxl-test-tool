#! /bin/bash


create_cmd_line(){
    op=$1
    extent=$2
    body="
    { \"execute\": \"qmp_capabilities\" }

    { \"execute\": \"$op\",
        \"arguments\": {
        \"path\": \"/machine/peripheral/cxl-memdev0\",
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
        \"path\": \"/machine/peripheral/cxl-memdev0\",
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
		  "path": "/machine/peripheral/cxl-memdev0",
          "output": "/tmp/dc-extent.txt"
      }
    }
	{ "execute": "cxl-display-pending-to-add-dc-extents",
	  "arguments": {
		  "path": "/machine/peripheral/cxl-memdev0",
          "output": "/tmp/dc-extent.txt"
      }
    }
    '
extent_file=/tmp/dc-extent.txt
show_extent(){
    rm -f $extent_file
    echo $print > /tmp/qmp-print.conf
    cxl-tool --issue-qmp /tmp/qmp-print.conf
    cat $extent_file
    echo
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
