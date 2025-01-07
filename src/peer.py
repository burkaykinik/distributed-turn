import socket
import json
import threading
import time
import uuid

class Peer:
    def __init__(self, server_host="15.0.0.3", server_port=5000, is_relay_capable=False):
        self.server_addr = (server_host, server_port)
        self.peer_id = str(uuid.uuid4())[:8]  # Short unique ID
        self.is_relay_capable = is_relay_capable
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))  # Random port
        self.local_addr = self.sock.getsockname()
        
        # For relay functionality
        self.relay_sessions = {}  # {session_id: (peer_a_addr, peer_b_addr)}
        
        # For peer functionality
        self.relay_addr = None
        self.target_peer = None
        
        print(f"Peer {self.peer_id} started on {self.local_addr}")
        
    def register_with_server(self):
        """Register with the central server"""
        message = {
            "type": "register",
            "peer_id": self.peer_id,
            "is_relay_capable": self.is_relay_capable
        }
        self._send_to_server(message)
        
    def connect_to_peer(self, target_peer_id):
        """Request connection to another peer"""
        message = {
            "type": "connect_request",
            "from_peer": self.peer_id,
            "to_peer": target_peer_id
        }
        self._send_to_server(message)
        
    def start(self):
        """Start listening for messages"""
        self.register_with_server()
        
        while True:
            data, addr = self.sock.recvfrom(1024)
            message = json.loads(data.decode())
            print(f"Received: {message} from {addr}")
            
            if message["type"] == "register_response":
                print("Successfully registered with server")
                
            elif message["type"] == "connect_response":
                # Got relay information from server
                self.relay_addr = tuple(message["relay_addr"])  # Convert list to tuple
                print(f"Using relay: {self.relay_addr}")
                self.target_peer = message["peer_b_id"]
                
            elif message["type"] == "incoming_connection":
                # Someone wants to connect to us
                self.relay_addr = tuple(message["relay_addr"])
                print(f"Incoming connection from {message['from_peer']} via relay {self.relay_addr}")
                
            elif message["type"] == "relay":
                if self.is_relay_capable:
                    self._handle_relay(message, addr)
                else:
                    # Forward to intended recipient through relay
                    if message["target"] == self.peer_id:
                        print(f"Message from peer: {message['data']}")
    
    def send_message(self, data):
        """Send a message to the connected peer through relay"""
        if self.relay_addr:
            message = {
                "type": "relay",
                "source": self.peer_id,
                "target": self.target_peer,
                "data": data
            }
            self.sock.sendto(json.dumps(message).encode(), self.relay_addr)
    
    def _handle_relay(self, message, addr):
        """Handle relay functionality if this peer is a relay"""
        source = message["source"]
        target = message["target"]
        
        # Create or get session ID
        session_id = f"{min(source, target)}-{max(source, target)}"
        
        if session_id not in self.relay_sessions:
            # Store the first peer's address
            self.relay_sessions[session_id] = {source: addr}
        else:
            # If we don't have this sender's address, store it
            if source not in self.relay_sessions[session_id]:
                self.relay_sessions[session_id][source] = addr
            
            # Forward the message to the other peer
            other_peer_addr = self.relay_sessions[session_id].get(target)
            if other_peer_addr:
                self.sock.sendto(json.dumps(message).encode(), other_peer_addr)
    
    def _send_to_server(self, message):
        """Helper to send message to central server"""
        self.sock.sendto(json.dumps(message).encode(), self.server_addr)

def start_peer(is_relay=False):
    peer = Peer(is_relay_capable=is_relay)
    peer.start()

if __name__ == "__main__":
    import sys
    is_relay = len(sys.argv) > 1 and sys.argv[1] == "--relay"
    start_peer(is_relay)