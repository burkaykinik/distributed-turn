#!/bin/bash

# NAT configuration script
# Usage: ./nat_config.sh [full_cone|restricted_cone|port_restricted|symmetric]

NAT_TYPE=$1
WAN_IF=eth0
LAN_IF=eth1

# Function to validate interfaces
validate_interfaces() {
    if ! ip link show $WAN_IF >/dev/null 2>&1 || ! ip link show $LAN_IF >/dev/null 2>&1; then
        echo "Error: Interfaces $WAN_IF or $LAN_IF do not exist"
        exit 1
    fi
}

# Function to reset iptables
reset_iptables() {
    echo "Resetting iptables rules..."
    # Flush existing rules
    iptables -t filter --flush
    iptables -t nat --flush
    iptables -t mangle --flush
    
    # Delete custom chains
    iptables -X
    
    # Set default policies
    iptables -P INPUT ACCEPT
    iptables -P FORWARD ACCEPT
    iptables -P OUTPUT ACCEPT
    
    # Enable IP forwarding
    echo "1" > /proc/sys/net/ipv4/ip_forward
}

# Function to configure symmetric NAT
configure_symmetric_nat() {
    echo "Configuring Symmetric NAT..."
    reset_iptables
    
    # Enable strict reverse path filtering
    echo "1" > /proc/sys/net/ipv4/conf/$WAN_IF/rp_filter
    echo "1" > /proc/sys/net/ipv4/conf/$LAN_IF/rp_filter
    
    # Create new chain for symmetric NAT
    iptables -N SYMNAT
    
    # Set up NAT with per-destination mapping
    iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE --random-fully
    
    # Add connection tracking with per-destination restrictions
    iptables -A FORWARD -j SYMNAT
    iptables -A SYMNAT -m state --state ESTABLISHED,RELATED -j ACCEPT
    iptables -A SYMNAT -i $LAN_IF -o $WAN_IF -m state --state NEW -j ACCEPT
    
    # Enable strict connection tracking
    iptables -A SYMNAT -m conntrack --ctstate INVALID -j DROP
    
    # Force new connection for each destination
    iptables -t raw -A PREROUTING -i $LAN_IF -j CT --notrack
    
    # Log NAT translations (optional, comment out in production)
    iptables -t nat -A POSTROUTING -o $WAN_IF -j LOG --log-prefix "SYMNAT: "
    
    echo "Symmetric NAT configuration complete."
    echo "Note: NAT translations can be monitored in syslog"
}

# Function to configure full cone NAT
configure_full_cone_nat() {
    echo "Configuring Full Cone NAT..."
    reset_iptables
    
    # Set up NAT without port restrictions
    iptables -t nat -A POSTROUTING -o $WAN_IF -j SNAT --to-source $(ip addr show $WAN_IF | grep 'inet ' | awk '{print $2}' | cut -d/ -f1)
    
    # Allow all incoming traffic to translated addresses
    iptables -A FORWARD -i $WAN_IF -o $LAN_IF -j ACCEPT
    iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
    
    echo "Full Cone NAT configuration complete."
}

# Function to configure restricted cone NAT
configure_restricted_cone_nat() {
    echo "Configuring Restricted Cone NAT..."
    reset_iptables
    
    # Set up NAT with source address restriction
    iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE
    
    # Allow only responses from previously contacted addresses
    iptables -A FORWARD -i $WAN_IF -o $LAN_IF -m state --state ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
    
    echo "Restricted Cone NAT configuration complete."
}

# Function to configure port restricted cone NAT
configure_port_restricted_nat() {
    echo "Configuring Port Restricted Cone NAT..."
    reset_iptables
    
    # Set up NAT with port and address restriction
    iptables -t nat -A POSTROUTING -o $WAN_IF -j MASQUERADE
    
    # Allow only responses from previously contacted addresses and ports
    iptables -A FORWARD -i $WAN_IF -o $LAN_IF -m state --state ESTABLISHED -j ACCEPT
    iptables -A FORWARD -i $LAN_IF -o $WAN_IF -j ACCEPT
    
    # Add additional port tracking
    iptables -t mangle -A PREROUTING -i $WAN_IF -m state --state NEW -j DROP
    
    echo "Port Restricted Cone NAT configuration complete."
}

# Validate input
if [ -z "$NAT_TYPE" ]; then
    echo "Usage: $0 [full_cone|restricted_cone|port_restricted|symmetric]"
    exit 1
fi

# Validate interfaces
validate_interfaces

# Configure NAT based on type
case "$NAT_TYPE" in
    symmetric)
        configure_symmetric_nat
        ;;
    full_cone)
        configure_full_cone_nat
        ;;
    restricted_cone)
        configure_restricted_cone_nat
        ;;
    port_restricted)
        configure_port_restricted_nat
        ;;
    *)
        echo "Invalid NAT type"
        exit 1
        ;;
esac

# Display current NAT configuration
echo -e "\nCurrent iptables rules:"
iptables -L -v -n
echo -e "\nCurrent NAT rules:"
iptables -t nat -L -v -n