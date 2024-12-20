

NAT_NETWORK_COUNT=$1

cp docker/peer_compose.yml.example docker/peer_compose.yml
for (( i=1; i<=NAT_NETWORK_COUNT; i++ ))
do
    echo "\
  NAT_NET$i:
    external: true" >> docker/peer_compose.yml
done

for (( i=1; i<=NAT_NETWORK_COUNT; i++ ))
do
    NETWORK_NAME="NAT_NET${i}"
    echo "Creating container with network $NETWORK_NAME"
    NETWORK_ID=$i docker-compose --project-name "nat_container${i}" -f docker/peer_compose.yml up -d 
    
    docker network connect $NETWORK_NAME nat_container${i}-nat-1 --ip "172.168.${i}.10"
    # docker network connect PUBLIC_NET nat_container${i}-nat-1
    # docker network connect $NETWORK_NAME nat_container${i}-peer-1
    

    docker exec nat_container${i}-peer-1 bash -c "ip route del default"
    docker exec nat_container${i}-peer-1 bash -c "ip route add default via 172.168.${i}.10"

    docker exec nat_container${i}-nat-1 bash -c "./startup_scripts/nat_startup.sh symmetric"

done

for (( i=1; i<=2; i++))
do
    docker-compose --project-name "public_container${i}" -f docker/public_compose.yml up -d
    # docker network connect PUBLIC_NET public_container${i}-server-1 --ip "15.0.0.$((i+5))"
done