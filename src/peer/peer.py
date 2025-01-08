import socket
import json
import threading
import time
import uuid

import sys

class Peer:
    def __init__(self, server_host="15.0.0.3", server_port=50000, is_relay_capable=False):
        self.server_addr = (server_host, server_port)
        self.peer_id = str(uuid.uuid4())[:8]
        self.is_relay_capable = is_relay_capable

        
        self.relay_ports:dict[str, (int,int)] = {}
        """
            self.relays is in the for of {peer_id-peer_id: (port_to, port_from)}
            it shows which ports are relayed to which other ports
        """
        self.relay_sockets:dict[str, (socket.socket, socket.socket)] = {}
        self.relay_mutexes:dict[str, threading.Lock] = {}
        self.relay_addr_for_port:dict[int, (str, int)] = {}




        self.main_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.temp_sock_addr = None
        self.temp_sock = None
        # self.sock.bind(("0.0.0.0", 0))


    def run(self):
        self._register_with_server()
        peer_b_id = input()
        if peer_b_id != "wait":
            self.connect_to_peer(peer_b_id)
        while True:
            data, addr = self.main_sock.recvfrom(1024)
            message = json.loads(data.decode())
            print(f"\n[PEER {self.peer_id}] Received: {message}")
            
            if message["type"] == "starting_connection_process":
                self._handle_connection_request(message, addr)

            if message["type"] == "relay_request":
                self._handle_relay_request(message, addr)


    def _register_with_server(self):
        """
        Register with the central server
        
        Returns:
            bool: True if registration was successful, False otherwise
        """
        self._send_to_server({
            "type": "register",
            "peer_id": self.peer_id,
            "is_relay_capable": self.is_relay_capable
        })

        data, _ = self.main_sock.recvfrom(1024)
        message = json.loads(data.decode())

        if message["type"] == "register_response" and message["status"] == "success":
            print(f"[PEER {self.peer_id}] Registration successful")
            return True
        else:
            print(f"[PEER {self.peer_id}] Registration failed")
            return False
        
    def connect_to_peer(self, target_peer_id):
        """
        Connect to a peer
        
        Args:
            target_peer_id (str): The id of the target peer
        """
        self._send_to_server({
            "type": "connect_request",
            "from_peer": self.peer_id,
            "to_peer": target_peer_id
        })


        data, addr = self.main_sock.recvfrom(1024)
        message = json.loads(data.decode())

        if message["type"] == "connect_response":
            if message["status"] == "failed":
                print(f"[PEER {self.peer_id}] Connection failed: {message['message']}")
                return
        
        # data, addr = self.main_sock.recvfrom(1024)
        # message = json.loads(data.decode())

        if message["type"] == "starting_connection_process":
            self.temp_sock_addr = (addr[0], message["port"])
            self._set_temp_sock(message, self.temp_sock_addr)

            # Send an unimportant message to the temp socket
            self._send_to_temp_sock(message, self.temp_sock_addr)

        
        data, _ = self._recv_from_temp_sock()
        message = json.loads(data.decode())

        if message["type"] == "connect_response":
            if message["status"] == "failed":
                print(f"[PEER {self.peer_id}] Connection failed: {message['message']}")
                return
        
        if message["type"] == "connection_established":

            self.ip_for_relay = message["ip"]
            self.port_for_relay = message["port"]
            
            self.temp_sock.close()

            print("Connection successful")
            print("Connected to peer: ", self.ip_for_relay, self.port_for_relay)

        else:
            print(f"[PEER {self.peer_id}] Connection failed")
            return


    def _handle_connection_request(self, message, addr):
        """
        Handle a connection request
        
        Args:
            message (dict): The message from the server
            addr (tuple): The address of the server
        """
        from_peer_id = message["from_peer"]
        new_port = message["new_port"]

        self._set_temp_sock(message, addr)
        new_server_addr = (addr[0], new_port)

        self._send_to_temp_sock({
            "type": "accept_connection_request",
        }, new_server_addr)

        if message["type"] == "starting_connection_process":

            self._send_to_temp_sock({
                "type": "accept_connection_request",
            }, new_server_addr)

        
        data, _ = self._recv_from_temp_sock()
        message = json.loads(data.decode())

        if message["type"] == "connect_response":
            if message["status"] == "failed":
                print(f"[PEER {self.peer_id}] Connection failed: {message['message']}")
                return
        
        if message["type"] == "connection_established":
            self.ip_for_relay = message["ip"]
            self.port_for_relay = message["port"]

            self.addr_to_relay = (self.ip_for_relay, self.port_for_relay)

            self.socket_to_relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket_to_relay.sendto(json.dumps({
                "type": "establish_connection",
            }).encode(), self.addr_to_relay)


            self.temp_sock.close()
            print("Connection successful")
            print("Connected to peer: ", self.ip_for_relay, self.port_for_relay)
            return
        else:
            print(f"[PEER {self.peer_id}] Connection failed")
            return
        
    def set_relay_socket_for_connection(self, message, addr):
        self.socket_to_relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr_for_relay = (addr[0], message["port"])
        self.socket_to_relay.sendto(json.dumps({
            "type": "establish_connection",
        }).encode(), addr)




    def _handle_relay_request(self, message, addr):
        """
        Handle a relay request
        
        Args:
            message (dict): The message from the server
            addr (tuple): The address of the server
        """

        if self.is_relay_capable == False:
            self._send_to_server({
                "type": "relay_response",
                "status": "failed",
                "message": "Peer is not relay capable"
            })
            return

        from_peer_id = message["from_peer"]
        to_peer_id = message["to_peer"]
        
        temp_port_for_server = message["port"]
        temp_server_addr = (addr[0], temp_port_for_server)

        self._set_temp_sock(message, temp_server_addr)

        socket_for_from_relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_for_from_relay.bind(("0.0.0.0", 0))
        port_for_from_relay = socket_for_from_relay.getsockname()[1]

        socket_for_to_relay = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_for_to_relay.bind(("0.0.0.0", 0))
        port_for_to_relay = socket_for_to_relay.getsockname()[1]

        self.relay_ports[f"{from_peer_id}-{to_peer_id}"] = (port_for_from_relay, port_for_to_relay)
        self.relay_sockets[f"{from_peer_id}-{to_peer_id}"] = (socket_for_from_relay, socket_for_to_relay)
        self.relay_mutexes[f"{from_peer_id}-{to_peer_id}"] = threading.Lock()
        

        # Receive one message from each peer to learn addr
        _, addr = socket_for_from_relay.recvfrom(1024)
        self.relay_addr_for_port[port_for_from_relay] = addr

        _, addr = socket_for_to_relay.recvfrom(1024)
        self.relay_addr_for_port[port_for_to_relay] = addr 
    

        self._send_to_temp_sock({
            "type": "relay_response",
            "status": "success",
            "port_to_peer": port_for_to_relay,
            "port_from_peer": port_for_from_relay
        }, temp_server_addr)



        self.start_relaying(from_peer_id, to_peer_id)


    def _set_temp_sock(self, message, addr):
        
        new_port = message["port"]
        self.temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        

    def _send_to_temp_sock(self, message, addr):
        self.temp_sock.sendto(json.dumps(message).encode(), addr)

    def _recv_from_temp_sock(self):
        data, addr = self.temp_sock.recvfrom(1024)
        message = json.loads(data.decode())
        return message, addr


    def _send_to_server(self, message):
        self.main_sock.sendto(json.dumps(message).encode(), self.server_addr)


    def start_relaying(self, from_peer_id, to_peer_id):
        """
        Start relaying messages between two peers
        
        Args:
            from_peer_id (str): The id of the peer sending the message
            to_peer_id (str): The id of the peer receiving the message
        """
        
        from_socket, to_socket = self.relay_sockets[f"{from_peer_id}-{to_peer_id}"]
        from_port, to_port = self.relay_ports[f"{from_peer_id}-{to_peer_id}"]

        threading.Thread(target=self.relay_thread, args=(from_socket, to_socket, from_port, to_port)).start()
        threading.Thread(target=self.relay_thread, args=(to_socket, from_socket, to_port, from_port)).start()

    def relay_thread(self, from_socket, to_socket, from_port, to_port):
        """
        Handle a relay request
        
        Args:
            message (dict): The message from the server
            addr (tuple): The address of the server
        """
        
        while True:
            data, addr = from_socket.recvfrom(1024)
            to_socket.sendto(data, self.relay_addr_for_port[to_port])
        
        from_socket.close()
        to_socket.close()
        print(f"[PEER {self.peer_id}] Relay closed")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        is_relay_capable = sys.argv[1] == "--relay"
    else:
        is_relay_capable = False
    peer = Peer(is_relay_capable=is_relay_capable)
    peer.run()