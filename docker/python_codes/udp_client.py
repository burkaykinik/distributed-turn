import socket
import sys
import time

def main():
    if len(sys.argv) != 3:
        print("Usage: python udp_client.py <IP> <PORT>")
        sys.exit(1)

    server_ip = sys.argv[1]
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print("Error: Port must be an integer.")
        sys.exit(1)

    # Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2.0) 

    while True:
        try:
            # Send "hello" message
            message = "hello".encode('utf-8')
            client_socket.sendto(message, (server_ip, server_port))
            print(f"Sent message: 'hello' to {server_ip}:{server_port}")

            # Set a timeout for the socket

            try:
                # Wait for a reply
                data, addr = client_socket.recvfrom(1024)  # Buffer size is 1024 bytes
                print(f"Received reply from {addr}: {data.decode('utf-8')}")
            except socket.timeout:
                print("No reply received within the timeout period.")

        except Exception as e:
            print(f"An error occurred: {e}")
            client_socket.close()
            break
        time.sleep(1)
if __name__ == "__main__":
    main()
