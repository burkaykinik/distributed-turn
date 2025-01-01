#!/bin/bash

# Start a new tmux session
tmux new-session -d -s my_session

tmux split-window -v
tmux select-pane -t 0
# Split the window vertically (side by side)
tmux split-window -h

tmux set -g mouse
# Send the command to the left pane
tmux send-keys -t 0 "docker exec -it nat_container1-peer-1 bash" C-m

# Send the command to the right pane
tmux send-keys -t 1 "docker exec -it public_container1-server-1 bash" C-m

tmux send-keys -t 2 "docker exec -it nat_container1-nat-1 bash" C-m


tmux send-keys -t 1 "python3 python_codes/udp_server.py" C-m
tmux send-keys -t 0 "python3 python_codes/udp_client.py 15.0.0.2 5005" C-m


# Attach to the tmux session
tmux attach-session -t my_session
