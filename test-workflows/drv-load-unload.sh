loops=$1


if [ "$loops" = "" ];then
    loops=5
fi

loop=0

while [ $loop -lt $loops ]; do
    cxl-tool --load-drv
    cxl-tool --unload-drv
    loop=$(($loop+1))
done
