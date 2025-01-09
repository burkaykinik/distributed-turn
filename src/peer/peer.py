import socket
import json
import threading
import time
import uuid
from typing import Dict, Tuple, Optional

class Peer:
    def __init__(self, server_host="15.0.0.3", server_port=50000, is_relay_capable=False):
        self.server_addr = (server_host, server_port)
        self.peer_id = str(uuid.uuid4())[:8]
        self.is_relay_capable = is_relay_capable
        
        # Main socket for communication with the server (and possibly for sending data to the relay)
        self.main_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.main_sock.bind(("0.0.0.0", 0))  # OS selects an ephemeral local port
        
        # Status flags
        self.running = False
        
        # Connection info (for normal peers)
        self.current_session = None
        self.relay_addr = None    # The IP of the relay
        self.relay_port = None    # The UDP port assigned to this peer
        self.target_peer = None   # The peer we’re connecting to

        # Relay-specific data (only used if is_relay_capable=True)
        self.relay_sessions: Dict[str, Dict] = {}
        self.relay_threads: Dict[str, list] = {}

        local_ip, local_port = self.main_sock.getsockname()
        print(f"\n[PEER {self.peer_id}] Started on ({local_ip}:{local_port})")
        if is_relay_capable:
            print(f"[PEER {self.peer_id}] Running as relay node")

    def start(self):
        """Start peer operation."""
        self.running = True
        
        # Register with server
        self._register_with_server()
        
        # Start message handling thread
        msg_thread = threading.Thread(target=self._handle_messages)
        msg_thread.daemon = True
        msg_thread.start()

        # (Optional) Keep sending keepalives periodically, only if not a relay
        if not self.is_relay_capable:
            keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
            keepalive_thread.start()
        
        # Start command interface (interactive console)
        self._handle_commands()

    def _register_with_server(self):
        """Register with the central server."""
        message = {
            "type": "register",
            "peer_id": self.peer_id,
            "is_relay_capable": self.is_relay_capable
        }
        self._send_to_server(message)
        print(f"[PEER {self.peer_id}] Registering with server...")

    def _keepalive_loop(self):
        """Periodically send keepalive to keep NAT mapping open (for normal peers)."""
        while self.running:
            time.sleep(10)  # every 10 seconds
            self._send_keepalive()

    def _send_keepalive(self):
        """Send an outbound packet to the server from the same local port, refreshing NAT mapping."""
        if self.is_relay_capable:
            return  # Relay peers typically don't need this
        local_ip, local_port = self.main_sock.getsockname()
        keepalive_msg = {
            "type": "keepalive",
            "peer_id": self.peer_id
        }
        self.main_sock.sendto(json.dumps(keepalive_msg).encode(), self.server_addr)
        print(f"[PEER {self.peer_id}] Sent keepalive to server from ({local_ip}:{local_port})")

    def _handle_messages(self):
        """Background thread: handle incoming UDP messages."""
        while self.running:
            try:
                data, addr = self.main_sock.recvfrom(1024)
                message = json.loads(data.decode())
                self._process_message(message, addr)
            except Exception as e:
                print(f"[PEER {self.peer_id}] Error handling message: {e}")

    def _process_message(self, message: Dict, addr: Tuple[str, int]):
        """Dispatch messages based on 'type'."""
        msg_type = message.get("type", "")
        
        if msg_type == "register_response":
            print(f"[PEER {self.peer_id}] Registration {'successful' if message['status'] == 'success' else 'failed'}")
            # Immediately send a keepalive now (in addition to the periodic loop)
            if message["status"] == "success" and not self.is_relay_capable:
                self._send_keepalive()

        elif msg_type == "incoming_connection":
            self._handle_incoming_connection(message)
            
        elif msg_type == "relay_setup" and self.is_relay_capable:
            self._handle_relay_setup(message)
            
        elif msg_type == "relay_info":
            self._handle_relay_info(message)
            
        elif msg_type == "relay_data":
            self._handle_relay_data(message)
        
        elif msg_type == "error":
            print(f"[PEER {self.peer_id}] Server error: {message.get('message', '')}")
        
        else:
            print(f"[PEER {self.peer_id}] Unknown message type: {msg_type}")

    def _handle_incoming_connection(self, message: Dict):
        """Peer B receives a connection request from Peer A."""
        from_peer = message["from_peer"]
        print(f"[PEER {self.peer_id}] Incoming connection from {from_peer}")
        
        # Auto-accept connection
        accept_msg = {
            "type": "accept_connection",
            "from_peer": from_peer
        }
        print(f"[PEER {self.peer_id}] Accepting connection")
        self._send_to_server(accept_msg)

    # ============== RELAY MODE (If is_relay_capable=True) ==============
    def _handle_relay_setup(self, message: Dict):
        """
        The server is telling this peer to act as a relay for peer_a and peer_b.
        We'll create two sockets, one for each peer, and then send back 'relay_ready'.
        """
        session_id = message["session_id"]
        peer_a = message["peer_a"]
        peer_b = message["peer_b"]
        
        # Create sockets for both peers
        sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_a.bind(("0.0.0.0", 0))  # OS picks free port
        sock_b.bind(("0.0.0.0", 0))  # OS picks free port
        
        # Store session info
        self.relay_sessions[session_id] = {
            "peer_a": {"id": peer_a, "socket": sock_a, "addr": None},
            "peer_b": {"id": peer_b, "socket": sock_b, "addr": None}
        }
        
        # Start relay threads
        self._start_relay_threads(session_id)
        
        # Send ports to server
        response = {
            "type": "relay_ready",
            "session_id": session_id,
            "ports": {
                # We map each peer_id to the port that belongs to it
                peer_a: sock_a.getsockname()[1],
                peer_b: sock_b.getsockname()[1]
            }
        }
        self._send_to_server(response)
        print(f"[PEER {self.peer_id}] Relay setup complete. Session {session_id}")

    def _start_relay_threads(self, session_id: str):
        """Start threads to relay data in both directions."""
        session = self.relay_sessions[session_id]
        
        thread_ab = threading.Thread(
            target=self._relay_thread,
            args=(session["peer_a"]["socket"], session["peer_b"]["socket"], 
                  "peer_a", "peer_b", session_id)
        )
        thread_ba = threading.Thread(
            target=self._relay_thread,
            args=(session["peer_b"]["socket"], session["peer_a"]["socket"], 
                  "peer_b", "peer_a", session_id)
        )
        
        thread_ab.daemon = True
        thread_ba.daemon = True
        
        self.relay_threads[session_id] = [thread_ab, thread_ba]
        thread_ab.start()
        thread_ba.start()

    def _relay_thread(self, from_sock: socket.socket, to_sock: socket.socket, 
                     from_peer_key: str, to_peer_key: str, session_id: str):
        """
        Repeatedly recv from one socket and forward to the other peer's known address.
        If we don't know the address yet, we learn it from the first inbound packet.
        """
        session = self.relay_sessions[session_id]
        while self.running and session_id in self.relay_sessions:
            try:
                data, addr = from_sock.recvfrom(1024)
                
                # If we haven't learned the "from" peer's NAT address yet, store it
                if not session[from_peer_key]["addr"]:
                    session[from_peer_key]["addr"] = addr
                    print(f"[RELAY {self.peer_id}] Learned {from_peer_key} address: {addr}")
                
                # Forward the packet if we know where to send it
                if session[to_peer_key]["addr"]:
                    to_sock.sendto(data, session[to_peer_key]["addr"])
                    print(f"[RELAY {self.peer_id}] Relayed {from_peer_key} -> {to_peer_key}")
            except Exception as e:
                print(f"[RELAY {self.peer_id}] Error in relay: {e}")

    # ============== NORMAL PEER MODE ==============
    def _handle_relay_info(self, message: Dict):
        """
        The server tells me which port the relay allocated for me. 
        I'll store that and send an initial packet to open my NAT pinhole.
        """
        self.current_session = message["session_id"]
        relay_ip = message["relay_addr"][0]  
        relay_port_for_me = message["port"]

        self.relay_addr = relay_ip
        self.relay_port = relay_port_for_me
        
        print(f"[PEER {self.peer_id}] Relay info: connect to {relay_ip}:{relay_port_for_me}")

        # Send an 'init' message to the relay to create a NAT mapping
        init_msg = {
            "type": "relay_data",
            "session_id": self.current_session,
            "action": "init"
        }
        self.main_sock.sendto(json.dumps(init_msg).encode(), (relay_ip, relay_port_for_me))
        print(f"[PEER {self.peer_id}] Sent INIT to relay at {relay_ip}:{relay_port_for_me}")

    def _handle_relay_data(self, message: Dict):
        """We received relay_data from the relay."""
        if message.get("action") == "init":
            print(f"[PEER {self.peer_id}] NAT pinhole established.")
        else:
            print(f"[PEER {self.peer_id}] Received from relay: {message.get('data', '')}")

    def connect_to_peer(self, target_peer_id: str):
        """Request connection to another peer via the server."""
        message = {
            "type": "connect_request",
            "from_peer": self.peer_id,
            "to_peer": target_peer_id
        }
        self._send_to_server(message)
        print(f"[PEER {self.peer_id}] Requesting connection to {target_peer_id}")

    def send_message(self, data: str):
        """Send a message through the relay."""
        if not self.relay_addr or not self.relay_port:
            print(f"[PEER {self.peer_id}] Error: Not connected to relay")
            return
            
        message = {
            "type": "relay_data",
            "session_id": self.current_session,
            "data": data
        }
        self.main_sock.sendto(json.dumps(message).encode(), (self.relay_addr, self.relay_port))
        print(f"[PEER {self.peer_id}] Sent message to relay: {data}")

    def _send_to_server(self, message: Dict):
        """Helper: send JSON-encoded message to the central server."""
        self.main_sock.sendto(json.dumps(message).encode(), self.server_addr)

    def _handle_commands(self):
        """Interactive console loop."""
        while self.running:
            try:
                cmd = input("\nEnter command (connect <peer_id> or send <message>): ")
                parts = cmd.split(maxsplit=1)
                if not parts:
                    continue
                    
                if parts[0] == "connect" and len(parts) == 2:
                    self.connect_to_peer(parts[1])
                elif parts[0] == "send" and len(parts) == 2:
                    self.send_message(parts[1])
                else:
                    print("Invalid command. Use 'connect <peer_id>' or 'send <message>'")
            except Exception as e:
                print(f"[PEER {self.peer_id}] Command error: {e}")

if __name__ == "__main__":
    import sys
    is_relay = (len(sys.argv) > 1 and sys.argv[1] == "--relay")
    peer = Peer(is_relay_capable=is_relay)
    peer.start()
