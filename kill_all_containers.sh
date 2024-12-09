#!/bin/bash

# Get the IDs of all running containers
CONTAINER_IDS=$(docker ps -q)

# Check if there are any running containers
if [ -z "$CONTAINER_IDS" ]; then
    echo "No running containers to stop."
else
    # Stop all running containers
    echo "Stopping all running containers..."
    docker stop $CONTAINER_IDS
fi
docker container prune -f
echo "All containers have been stopped."
