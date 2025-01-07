#!/bin/bash

cd "$(dirname "$0")/.."  # Move to project root directory

echo "Stopping containers..."
docker-compose -f deployment/docker/docker-compose.yml down

echo "Stopping all containers manually..."
docker stop $(docker ps -a -q)
docker rm $(docker ps -a -q)

echo "Removing networks..."
docker network rm PUBLIC_NET NAT_NET1 NAT_NET2 || true

echo "Killing tmux session..."
tmux kill-session -t p2p_test || true

echo "Cleanup complete!"