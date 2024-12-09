#!/bin/bash

# Number of networks to create
NUM_NETWORKS=$1

# Base name for the networks
BASE_NAME="NAT_NET"

# Starting subnet base (192.168.1.0/24)
SUBNET_BASE=1

# Remove existing networks with names matching the pattern NAT_NET*
EXISTING_NETWORKS=$(docker network ls --filter name="^${BASE_NAME}" --format "{{.Name}}")

if [ ! -z "$EXISTING_NETWORKS" ]; then
    echo "Removing existing networks:"
    for NETWORK in $EXISTING_NETWORKS
    do
        echo "Removing network $NETWORK"
        docker network rm $NETWORK
    done
else
    echo "No existing networks to remove."
fi



# Create the networks with incremental names and subnets
for (( i=1; i<=NUM_NETWORKS; i++ ))
do
    NETWORK_NAME="${BASE_NAME}${i}"
    SUBNET="172.168.${SUBNET_BASE}.0/24"
    echo "Creating network $NETWORK_NAME with subnet $SUBNET"
    docker network create --subnet=$SUBNET $NETWORK_NAME
    ((SUBNET_BASE++))
done


PUBLIC_NET_NAME="PUBLIC_NET"
EXISTING_PUBLIC_NETWORKS=$(docker network ls --filter name="^${PUBLIC_NET_NAME}" --format "{{.Name}}")

if [ ! -z "$EXISTING_PUBLIC_NETWORKS" ]; then
    echo "Removing existing networks:"
    for NETWORK in $EXISTING_PUBLIC_NETWORKS
    do
        echo "Removing network $NETWORK"
        docker network rm $NETWORK
    done
else
    echo "No existing networks to remove."
fi


SUBNET="15.0.0.0/8"
echo "Creating network $PUBLIC_NET_NAME with subnet $SUBNET"
docker network create --subnet=$SUBNET $PUBLIC_NET_NAME

echo "Network creation complete."
