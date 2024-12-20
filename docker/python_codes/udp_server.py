import sys
import socket

# from .inter_server_comm import ServerCommunicator


# current_server = sys.argv[1]
# server_ips = ServerCommunicator.server_ips

# for server_name, server_ip in server_ips.items():
#     if server_name != current_server:
#         other_server = server_name
#         other_server_ip = server_ip
#         break

# server_comm = ServerCommunicator(other_server)

HOST = ""  # or "0.0.0.0"
PORT = 5005

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind((HOST, PORT))
    print("UDP server listening on all interfaces...")
    while True:
        data, addr = s.recvfrom(1024)
        print(f"Received from {addr}: {data.decode()}")
        s.sendto(b"Message received", addr)
