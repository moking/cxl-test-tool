echo "Start VM"
cxl-tool.py --run -T FM_TARGET 
cxl-tool.py --create-dcR mem0
echo "Start FM"
cxl-tool.py --attach-fm -T FM_CLIENT
sleep 2
echo "Install libcxlmi on FM"
cxl-tool.py --install-libcxlmi-fm
echo "Setup MCTP on FM"
cxl-tool.py --setup-mctp-fm

echo 
echo "Now, login FM VM"
echo "cxl-tool.py --login-fm"
echo "cd /tmp/libcxlmi; ./build/examples/cxl-dcd"
