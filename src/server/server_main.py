from registry import Registry

import socket
import json
import threading

class ConnectionHandler:
    def __init__(self, port=0):
        pass
        # self.port = port
        # self.main_socket:socket.socket = None

        # Sockets for other connections, keys are ports
        # TODO: decide if peerid works better

        # self.second_socks:dict[str,socket.socket] = {}
        # self.sock_to_peer_addr = {}
        

    def get_new_sock(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 0))
        # port = sock.getsockname()[1]

        # self.second_socks[port] = sock
        return sock

    # def wait_for_connection_on_port(self, port):
    #     data, addr = self.second_socks[port].recvfrom(1024)
    #     self.sock_to_peer_addr[port] = addr
    #     # message:dict[str,str] = json.loads(data.decode())
    #     # return message, addr
        
    # def send_get_message(self, peer_id:str, message:dict):
    #     """
    #     Send a message to a peer and waits for a response
        
    #     Args:
    #         peer_id (str): The id of the peer to send the message to
    #         message (dict): The message to send
    #     """
    #     if not self.sock_to_peer_addr.get(peer_id):
    #         print(f"[SERVER] Error: Connection to peer not found")
    #         return
        
    #     addr = self.sock_to_peer_addr[peer_id]
    #     self.main_socket.sendto(json.dumps(message).encode(), addr)
        
    #     try:
    #         data, addr = self.main_socket.recvfrom(1024)
    #     except Exception as e:
    #         print(f"[SERVER] Error: {e}")
    #         return
    #     self.sock_to_peer_addr[peer_id] = addr
    #     return data.decode()

    # def send_message(self, peer_id:str, message:dict):
    #     """Send a message to a peer
        
    #     Args:
    #         peer_id (str): The id of the peer to send the message to
    #         message (dict): The message to send
    #     """

    #     if not self.sock_to_peer_addr.get(peer_id):
    #         print(f"[SERVER] Error: Connection to peer not found")
    #         return
        
    #     addr = self.sock_to_peer_addr[peer_id]
    #     self.main_socket.sendto(json.dumps(message).encode(), addr)

    # def send_messsage_to_addr(self, addr, message):
    #     self.main_socket.sendto(json.dumps(message).encode(), addr)


class Server:
    def __init__(self, port):
        self.registry = Registry()
        self.connection_handler = ConnectionHandler()
        # self.connection_handler.start()

        self.threads:list[threading.Thread] = []


        self.main_sock = None
        self.main_sock_lock = threading.Lock()
        self.port = port



    def start(self):

        self.main_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.main_sock.bind(("0.0.0.0", self.port))

        while True:
            try:
                data, addr = self.main_sock.recvfrom(1024)
                message = json.loads(data.decode())
                
                print("[SERVER] Received:", message , "from", addr)

                message_type = message.get("type", "")
                if message_type == "register":
                    self._handle_register(message, addr)
                elif message_type == "connect_request":
                    self._handle_connect_request(message, addr)
            except Exception as e:
                print(f"[SERVER] Error from main: {e}")

    def _handle_register(self, message, addr):
        """
        Handle a register message from a peer. It will start a peer to handle the registration
        
        Args:
            message (dict): The message from the peer
            addr (tuple): The address of the peer
        """

        register_thread = threading.Thread(target=self._handle_register_thread, args=(message, addr))
        register_thread.start()
        self.threads.append(register_thread)


    def _handle_register_thread(self, message, addr):
        """
        Handle a register message from a peer in a thread
        
        Args:
            message (dict): The message from the peer
            addr (tuple): The address of the peer
        """

        peer_id = message["peer_id"]
        ip = addr[0]
        port = addr[1]

        self.registry.add_peer(peer_id, ip, port)



        
        if message.get("is_relay_capable", False):
            self.registry.add_relay_peer(peer_id, ip, port)

        print(f"[SERVER] Registered peer: {peer_id}")

        response = {
            "type": "register_response",
            "status": "success"
        }

        self._send_to_peer(response, peer_id)

    def _handle_connect_request(self, message, addr):
        """
        Handle a connect request from a peer
        
        Args:
            message (dict): The message from the peer
            addr (tuple): The address of the peer
        """

        connect_thread = threading.Thread(target=self._handle_connect_request_thread, args=(message, addr))
        connect_thread.start()
        self.threads.append(connect_thread)

        

        
    def _handle_connect_request_thread(self, message, addr):
        
        from_peer = message["from_peer"]
        to_peer = message["to_peer"]
        
        print(f"[SERVER] Connection request: {from_peer} -> {to_peer}")

        from_peer_data = self.registry.get_peer(from_peer)
        to_peer_data = self.registry.get_peer(to_peer)

        if not to_peer_data:
            print(f"[SERVER] Error: Peer not found")
            self._send_to_peer({
                "type": "connect_response",
                "status": "failed",
                "message": "Peer not found"
            }, from_peer)
            return
        
        
        from_peer_sock = self.connection_handler.get_new_sock()
        to_peer_sock = self.connection_handler.get_new_sock()

        from_peer_port = from_peer_sock.getsockname()[1]
        to_peer_port = to_peer_sock.getsockname()[1]

        self._send_to_peer({
            "type": "starting_connection_process",
            "port": from_peer_port
        }, from_peer)

        self._send_to_peer({
            "type": "starting_connection_process",
            "from_peer": from_peer,
            "port": to_peer_port
        }, to_peer)


        _, new_from_peer_addr = from_peer_sock.recvfrom(1024)

        data, new_to_peer_addr = to_peer_sock.recvfrom(1024)
        message = json.loads(data.decode())
        
        if message["type"] != "accept_connection_request":
            self._send_to_sock({
                "type": "connect_response",
                "status": "failed",
                "message": "Peer did not accept connection request"
            }, from_peer_sock, new_from_peer_addr)
            self._send_to_peer({
                "type": "connect_response",
                "status": "failed",
                "message": "Peer did not accept connection request"
            }, to_peer, new_to_peer_addr)

            from_peer_sock.close()
            to_peer_sock.close()
            return
        

        # Until this point, we registered the new ports and got the new addresses
        # Now, establish a connection to the relay peer

        
        selected_relay_peer = self._select_relay_peer(from_peer, to_peer)
        if not selected_relay_peer:
            self._send_to_sock({
                "type": "connect_response",
                "status": "failed",
                "message": "No relay peer available"
            }, from_peer_sock, new_from_peer_addr)
            self._send_to_peer({
                "type": "connect_response",
                "status": "failed",
                "message": "No relay peer available"
            }, to_peer, new_to_peer_addr)

            from_peer_sock.close()
            to_peer_sock.close()
            return
        
        relay_peer_sock = self.connection_handler.get_new_sock()
        relay_peer_port = relay_peer_sock.getsockname()[1]

        self._send_to_peer({
            "type": "relay_request",
            "from_peer": from_peer,
            "to_peer": to_peer,
            "port": relay_peer_port
        }, selected_relay_peer)

        _, new_relay_peer_addr = relay_peer_sock.recvfrom(1024)

        # self._send_to_sock({
        #     "type": "relay_request",
        #     "from_peer": from_peer,
        #     "to_peer": to_peer,
        # }, relay_peer_sock, new_relay_peer_addr)

        data, _ = relay_peer_sock.recvfrom(1024)
        message = json.loads(data.decode())

        # TODO: Select a new relay peer if the current one is not available
        if message["type"] != "relay_response" or message["status"] == "failed":
            self._send_to_sock({
                "type": "connect_response",
                "status": "failed",
                "message": "Relay peer did not accept connection request"
            }, from_peer_sock, new_from_peer_addr)
            self._send_to_peer({
                "type": "connect_response",
                "status": "failed",
                "message": "Relay peer did not accept connection request"
            }, to_peer, new_to_peer_addr)

            from_peer_sock.close()
            to_peer_sock.close()
            relay_peer_sock.close()
            return
        
        if message["type"] == "relay_response" and message["status"] == "success":
            relay_peer_ip = new_from_peer_addr[0]
            port_to_peer = message["port_to_peer"]
            port_from_peer = message["port_from_peer"]

            self._send_to_sock({
                "type": "connection_established",
                "ip": relay_peer_ip,
                "port": port_to_peer
            }, from_peer_sock, new_from_peer_addr)

            self._send_to_sock({
                "type": "connection_established",
                "ip": relay_peer_ip,
                "port": port_from_peer
            }, to_peer_sock, new_to_peer_addr)

        
        from_peer_sock.close()
        to_peer_sock.close()
        relay_peer_sock.close()


    def _select_relay_peer(self, from_peer:str, to_peer:str):
        """
        Select a relay peer for a connection
        """

        relay_peers = self.registry.get_relay_peers()
        if not relay_peers:
            print(f"[SERVER] Error: No relay peers available")
            return None

        # For now, always return the first relay peer
        return relay_peers[0]


    def _send_to_peer(self, message:dict, peer_id:str):
        """
        Send a message to a peer
        
        Args:
            message (dict): The message to send
            peer_id (str): The id of the peer to send the message to
        """

        peer_data = self.registry.get_peer(peer_id)
        if not peer_data:
            print(f"[SERVER] Error: Peer not found")
            return
        
        ip = peer_data["ip"]
        port = peer_data["port"]
        addr = (ip, port)
        with self.main_sock_lock:
            self.sock.sendto(json.dumps(message).encode(), addr)

    def _send_to_sock(self, message:dict, sock, addr):
        sock.sendto(json.dumps(message).encode(), addr)




        