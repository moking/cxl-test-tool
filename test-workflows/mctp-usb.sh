
mctp_link=`mctp link|grep mctpusb | awk '{print $2}'`
echo $mctp_link
if [ "$mctp_link" == "" ];then
    echo "MCTP link not found"
    exit 1
fi

addr=50
net=11
mctp_links=$mctp_link
for mctp_link in $mctp_links; do
    echo mctp_link
    # Bring up the link
    mctp link set $mctp_link up
    # Assign an address to the aspeed-i2c controller
    mctp addr add $addr dev $mctp_link
    # Assign a neetwork ID to the link (11)
    mctp link set $mctp_link net $net
    addr=$((addr+1))
    net=$((net+1))
done
# Start the daemon that uses dbus for configuration.

systemctl stop mctpd.service
systemctl start mctpd.service
# Assign an EID to the EP (hard coded I2C address is 0x4d)
busctl call au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/interfaces/mctpusb0 au.com.codeconstruct.MCTP.BusOwner1 SetupEndpoint ay 0

# Check it worked by dumping some state.
# busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/8 xyz.openbmc_project.MCTP.Endpoint
# busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/9 xyz.openbmc_project.MCTP.Endpoint
# busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/10 xyz.openbmc_project.MCTP.Endpoint

busctl introspect au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/networks/11/endpoints/50
busctl introspect au.com.codeconstruct.MCTP1 /au/com/codeconstruct/mctp1/networks/12/endpoints/51
