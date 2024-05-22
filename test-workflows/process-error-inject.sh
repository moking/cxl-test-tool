#! /bin/bash


inject_cor_err='
 { "execute": "qmp_capabilities" }

 { "execute": "cxl-inject-correctable-error",
	  "arguments": {
		  "path": "/machine/peripheral/cxl-pmem0",
          "type": "physical"
      }
    }
'

inject_uncor_err='
{ "execute": "cxl-inject-uncorrectable-errors",
  "arguments": {
    "path": "/machine/peripheral/cxl-pmem0",
    "errors": [
        {
            "type": "cache-address-parity",
            "header": [ 3, 4]
        },
        {
            "type": "cache-data-parity",
            "header": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]
        },
        {
            "type": "internal",
            "header": [ 1, 2, 4]
        }
        ]
  }}
'

qmp_file=/tmp/qmp-run.txt
execute(){
    cmd=$1
    echo $cmd > $qmp_file
    echo cxl-tool --issue-qmp $qmp_file
    cxl-tool --issue-qmp $qmp_file
    echo
}

help() {
 echo
 echo $0 [args]
 echo "args:"
 echo -e "  1: inject correctable error"
 echo -e "  2: inject uncorrectable error"
 echo
}


arg=$1

if [ "$arg" == "1" ];then
    cmd="$inject_cor_err"
elif [ "$arg" == "2" ];then
    cmd="$inject_uncor_err"
else
    echo "args: $1 not supported"
    help
    exit 1
fi
execute "$cmd"


