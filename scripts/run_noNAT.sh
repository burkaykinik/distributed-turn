#!/bin/bash

# 1. Move to project root directory (adjust if needed)
cd "$(dirname "$0")/.."

# 2. Kill old containers
echo "[run_noNAT] Stopping any running containers..."
docker-compose down -v || true

echo "[run_noNAT] Removing old networks..."
docker network rm PUBLIC_NET NAT_NET1 NAT_NET2 2>/dev/null || true

# 3. Create a simple network named PUBLIC_NET with a chosen subnet
echo "[run_noNAT] Creating PUBLIC_NET network..."
docker network create --subnet=15.0.0.0/16 PUBLIC_NET 2>/dev/null || \
   echo "PUBLIC_NET already exists or creation failed. Proceeding..."

# 4. Build Docker image (if needed)
echo "[run_noNAT] Building Docker image..."
docker build -t distributed-turn -f deployment/docker/Dockerfile .

# 5. Start containers in the background
echo "[run_noNAT] Starting containers with no NAT..."
docker-compose -f deployment/docker/docker-compose.yml up -d

# 6. Optional: Use tmux to attach to each container’s logs/exec
#    If you don't want tmux, remove or comment out this section.
echo "[run_noNAT] Opening tmux session..."
tmux new-session -d -s noNAT_test

# Split into three panes: one for server, one for relay, one for peers
tmux split-window -v
tmux select-pane -t 0
tmux split-window -h
tmux select-pane -t 2
tmux split-window -h

# Pane mapping:
#   0: top-left
#   1: bottom-left
#   2: top-right
#   3: bottom-right

# Attach to containers
tmux send-keys -t 3 "docker exec -it docker-central_server-1 python3 -m src.server.server_main" C-m
sleep 2  # wait for server to start
tmux send-keys -t 2 "docker exec -it docker-relay_peer-1 python3 -m src.peer.peer --relay" C-m
sleep 1
tmux send-keys -t 0 "docker exec -it docker-peer_a-1 python3 -m src.peer.peer" C-m
tmux send-keys -t 1 "docker exec -it docker-peer_b-1 python3 -m src.peer.peer" C-m

# Attach to tmux
tmux attach-session -t noNAT_test
