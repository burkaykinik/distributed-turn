#!/bin/bash

cd "$(dirname "$0")/.."  # Move to project root directory

echo "Creating Docker networks..."
docker network create --subnet=15.0.0.0/8 PUBLIC_NET 2>/dev/null || echo "PUBLIC_NET already exists"
docker network create --subnet=172.168.1.0/24 NAT_NET1 2>/dev/null || echo "NAT_NET1 already exists"
docker network create --subnet=172.168.2.0/24 NAT_NET2 2>/dev/null || echo "NAT_NET2 already exists"

echo "Building Docker image..."
docker build -t distributed-turn -f deployment/docker/Dockerfile .

echo "Starting containers..."
docker-compose -f deployment/docker/docker-compose.yml up -d

echo "Opening tmux session with peers..."
tmux new-session -d -s p2p_test

# Split into three panes
tmux split-window -v
tmux select-pane -t 0
tmux split-window -h
tmux select-pane -t 2
tmux split-window -h

# Enable mouse control
tmux set -g mouse on

# Connect to containers with correct names
tmux send-keys -t 3 "docker exec -it docker-central_server-1 python3 -m src.server.server_main" C-m
sleep 2  # Wait for server to start
tmux send-keys -t 2 "docker exec -it docker-relay_peer-1 python3 -m src.peer.peer --relay" C-m
sleep 1
tmux send-keys -t 0 "docker exec -it docker-peer_a-1 python3 -m src.peer.peer" C-m
tmux send-keys -t 1 "docker exec -it docker-peer_b-1 python3 -m src.peer.peer" C-m

# Attach to tmux session
tmux attach-session -t p2p_test