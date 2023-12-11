loops=$1


if [ "$loops" = "" ];then
    loops=5
fi

loop=0

while [ $loop -lt $loops ]; do
    cxl-tool --create-ram-region
    cxl-tool --destroy-region
    loop=$(($loop+1))
done
