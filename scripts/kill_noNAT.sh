#!/bin/bash

# Move to the project root directory
cd "$(dirname "$0")/.." 

echo "Stopping containers..."
docker-compose -f deployment/docker/docker-compose.noNAT.yml down

echo "Stopping all containers manually..."
docker stop $(docker ps -a -q) 2>/dev/null
docker rm $(docker ps -a -q) 2>/dev/null

echo "Removing networks..."
docker network rm PUBLIC_NET || true

echo "Cleanup complete!"
