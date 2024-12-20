#!/bin/bash

NAT_TYPE=$1

WAN_IF=eth0
LAN_IF=eth1

if [ -z "$NAT_TYPE" ]; then
    echo "Usage: $0 [full_cone|restricted_cone|port_restricted|symmetric]"
    exit 1
fi


case "$NAT_TYPE" in

    full_cone)
    echo "Full cone NAT not implemented yet"
    ;;
    restricted_cone)
    echo "Restricted cone NAT not implemented yet"
    ;;
    port_restricted)
    echo "Port restricted NAT not implemented yet"
    ;;
    symmetric)
    echo "1" > /proc/sys/net/ipv4/ip_forward
    iptables --flush
    iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE --random
    iptables -A FORWARD -i $WAN_IF -o $LAN_IF -m state --state RELATED,ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
    ;;
    *)
    echo "Invalid NAT type"
    exit 1
    ;;
esac

echo "NAT configuration for $NAT_TYPE is complete"