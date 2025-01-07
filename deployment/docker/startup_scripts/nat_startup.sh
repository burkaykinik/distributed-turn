#!/bin/bash

NAT_TYPE=$1
WAN_IF=eth0
LAN_IF=eth1

echo "1" > /proc/sys/net/ipv4/ip_forward

case "$NAT_TYPE" in
    "symmetric")
        # Configure symmetric NAT
        iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE --random-fully
        iptables -A FORWARD -i $WAN_IF -o $LAN_IF -m state --state ESTABLISHED -j ACCEPT
        iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
        ;;
        
    "full_cone")
        # Configure full cone NAT
        iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE
        iptables -A FORWARD -i $WAN_IF -o $LAN_IF -j ACCEPT
        iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
        ;;
        
    *)
        echo "Invalid NAT type: $NAT_TYPE"
        exit 1
        ;;
esac

echo "NAT configured as $NAT_TYPE"