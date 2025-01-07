import socket
import json
import threading
import time
import uuid

class Peer:
    def __init__(self, server_host="15.0.0.3", server_port=5000, is_relay_capable=False):
        self.server_addr = (server_host, server_port)
        self.peer_id = str(uuid.uuid4())[:8]
        self.is_relay_capable = is_relay_capable
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.local_addr = self.sock.getsockname()
        
        # For relay functionality
        self.relay_sessions = {}  # {session_id: {peer_id: addr}}
        
        # For peer functionality
        self.relay_addr = None
        self.target_peer = None
        
        print(f"\n[PEER {self.peer_id}] Started on {self.local_addr}")
        if is_relay_capable:
            print(f"[PEER {self.peer_id}] Running as relay node")
        
    def register_with_server(self):
        message = {
            "type": "register",
            "peer_id": self.peer_id,
            "is_relay_capable": self.is_relay_capable
        }
        print(f"\n[PEER {self.peer_id}] Registering with server...")
        self._send_to_server(message)
        
    def connect_to_peer(self, target_peer_id):
        message = {
            "type": "connect_request",
            "from_peer": self.peer_id,
            "to_peer": target_peer_id
        }
        print(f"\n[PEER {self.peer_id}] Requesting connection to peer {target_peer_id}")
        self._send_to_server(message)
        
    def start(self):
        self.register_with_server()
        
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                message = json.loads(data.decode())
                print(f"\n[PEER {self.peer_id}] Received: {message}")
                
                if message["type"] == "register_response":
                    print(f"[PEER {self.peer_id}] Registration successful")
                    
                elif message["type"] == "connect_response":
                    self.relay_addr = tuple(message["relay_addr"])
                    self.target_peer = message["peer_b_id"]
                    print(f"[PEER {self.peer_id}] Connected via relay: {self.relay_addr}")
                    
                elif message["type"] == "incoming_connection":
                    self.relay_addr = tuple(message["relay_addr"])
                    self.target_peer = message["from_peer"]
                    print(f"[PEER {self.peer_id}] Incoming connection from {self.target_peer} via relay {self.relay_addr}")
                    
                elif message["type"] == "relay":
                    if self.is_relay_capable:
                        self._handle_relay(message, addr)
                    else:
                        if message["target"] == self.peer_id:
                            print(f"[PEER {self.peer_id}] Message from peer: {message['data']}")
            
            except Exception as e:
                print(f"[PEER {self.peer_id}] Error: {e}")
    
    def send_message(self, data):
        if not self.relay_addr or not self.target_peer:
            print(f"[PEER {self.peer_id}] Error: Not connected to a peer")
            return
            
        message = {
            "type": "relay",
            "source": self.peer_id,
            "target": self.target_peer,
            "data": data
        }
        print(f"\n[PEER {self.peer_id}] Sending through relay: {data}")
        self.sock.sendto(json.dumps(message).encode(), self.relay_addr)
    
    def _handle_relay(self, message, addr):
        source = message["source"]
        target = message["target"]
        
        session_id = f"{min(source, target)}-{max(source, target)}"
        print(f"[RELAY {self.peer_id}] Handling session: {session_id}")
        
        if session_id not in self.relay_sessions:
            self.relay_sessions[session_id] = {source: addr}
            print(f"[RELAY {self.peer_id}] New session created")
        else:
            if source not in self.relay_sessions[session_id]:
                self.relay_sessions[session_id][source] = addr
                print(f"[RELAY {self.peer_id}] Added peer to session")
            
            other_peer_addr = self.relay_sessions[session_id].get(target)
            if other_peer_addr:
                print(f"[RELAY {self.peer_id}] Forwarding message to {target}")
                self.sock.sendto(json.dumps(message).encode(), other_peer_addr)
    
    def _send_to_server(self, message):
        self.sock.sendto(json.dumps(message).encode(), self.server_addr)

def start_peer(is_relay=False):
    peer = Peer(is_relay_capable=is_relay)
    
    # Start the receiving thread
    receive_thread = threading.Thread(target=peer.start)
    receive_thread.daemon = True
    receive_thread.start()
    
    # Interactive command loop
    while True:
        try:
            cmd = input("\nEnter command (connect <peer_id> or send <message>): ")
            parts = cmd.split(maxsplit=1)
            if not parts:
                continue
                
            if parts[0] == "connect" and len(parts) == 2:
                peer.connect_to_peer(parts[1])
            elif parts[0] == "send" and len(parts) == 2:
                peer.send_message(parts[1])
            else:
                print("Invalid command. Use 'connect <peer_id>' or 'send <message>'")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import sys
    is_relay = len(sys.argv) > 1 and sys.argv[1] == "--relay"
    start_peer(is_relay)