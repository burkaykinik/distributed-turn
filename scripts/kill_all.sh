#!/bin/bash

echo "Stopping containers..."
docker-compose down

echo "Removing networks..."
docker network rm PUBLIC_NET NAT_NET1 NAT_NET2

echo "Killing tmux session..."
tmux kill-session -t p2p_test

echo "Cleanup complete!"