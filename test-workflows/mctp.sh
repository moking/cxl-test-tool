
mctp_link=`mctp link|grep mctpi2c | awk '{print $2}'`
if [ "$mctp_link" == "" ];then
    echo "MCTP link not found"
    exit 1
fi

# Bring up the link
mctp link set $mctp_link up
# Assign an address to the aspeed-i2c controller
mctp addr add 50 dev $mctp_link
# Assign a neetwork ID to the link (11)
mctp link set $mctp_link net 11
# Start the daemon that uses dbus for configuration.
systemctl start mctpd.service
# Assign an EID to the EP (hard coded I2C address is 0x4d)
busctl call xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp au.com.CodeConstruct.MCTP AssignEndpoint say $mctp_link 1 0x4
busctl call xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp au.com.CodeConstruct.MCTP AssignEndpoint say $mctp_link 1 0x5
busctl call xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp au.com.CodeConstruct.MCTP AssignEndpoint say $mctp_link 1 0x6
# Check it worked by dumping some state.
busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/8 xyz.openbmc_project.MCTP.Endpoint
busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/9 xyz.openbmc_project.MCTP.Endpoint
busctl introspect xyz.openbmc_project.MCTP /xyz/openbmc_project/mctp/11/10 xyz.openbmc_project.MCTP.Endpoint

